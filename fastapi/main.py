from contextlib import asynccontextmanager
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from typing import Optional, List
import io
import csv
import json
import logging
import os

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy import select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from statsmodels.tsa.holtwinters import ExponentialSmoothing

import redis as redis_lib

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

from database import get_db, AsyncSessionLocal, engine
from models import PurchaseRecord, UserRecord
from auth import (
    Token, User, authenticate_user,
    create_access_token, create_refresh_token, verify_refresh_token,
    get_current_user, get_user, create_user,
)

# --- OpenTelemetry tracing ---
_otlp_endpoint = os.getenv("OTLP_ENDPOINT", "")
if _otlp_endpoint:
    _resource = Resource.create({SERVICE_NAME: "purchases-api"})
    _provider = TracerProvider(resource=_resource)
    _provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=_otlp_endpoint, insecure=True))
    )
    trace.set_tracer_provider(_provider)

# --- Redis ---
_redis: redis_lib.Redis | None = None


def get_redis() -> redis_lib.Redis | None:
    global _redis
    if _redis is None:
        url = os.getenv("REDIS_URL")
        if url:
            try:
                _redis = redis_lib.from_url(url, decode_responses=True)
                _redis.ping()
            except Exception:
                _redis = None
    return _redis


KPI_CACHE_KEY = "kpis"
KPI_TTL = 60


# --- Structured JSON logger ---
class _JSONFormatter(logging.Formatter):
    def format(self, record):
        return json.dumps({
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
        })


_handler = logging.StreamHandler()
_handler.setFormatter(_JSONFormatter())
logger = logging.getLogger("purchases_api")
logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# --- Rate limiter ---
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])


# --- App lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(UserRecord).limit(1))
        if not result.scalar_one_or_none():
            admin_password = os.getenv("ADMIN_PASSWORD", "purchases123")
            await create_user(db, "admin", admin_password, role="admin")
            logger.info("Seeded default admin user")
    yield


app = FastAPI(title="Customer Purchases API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Instrumentator().instrument(app).expose(app)
FastAPIInstrumentor.instrument_app(app)
SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)

SUPPORTED_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "SEK", "NOK", "DKK"}


# --- Pydantic schemas ---
class ErrorDetail(BaseModel):
    detail: str


class BulkUploadResult(BaseModel):
    added: int


class Purchase(BaseModel):
    id: Optional[int] = None
    customer_name: str
    country: str
    purchase_date: date
    amount: float = Field(gt=0, description="Must be greater than zero")
    currency: str = "USD"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class PurchasePage(BaseModel):
    items: List[Purchase]
    total: int
    limit: int
    offset: int


# --- Health / readiness ---
@app.get("/healthz", tags=["ops"])
def health_check():
    return {"status": "healthy"}


@app.get("/readyz", tags=["ops"], responses={503: {"model": ErrorDetail, "description": "Database not ready"}})
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database not ready")


# --- Auth endpoints ---
class RegisterRequest(BaseModel):
    username: str
    password: str


@app.post(
    "/token",
    response_model=Token,
    tags=["auth"],
    responses={401: {"model": ErrorDetail, "description": "Incorrect username or password"}},
)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return Token(
        access_token=create_access_token(user.username),
        refresh_token=create_refresh_token(user.username),
        token_type="bearer",
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post(
    "/token/refresh",
    response_model=Token,
    tags=["auth"],
    responses={401: {"model": ErrorDetail, "description": "Invalid or expired refresh token"}},
)
async def refresh_token(req: RefreshRequest, db: AsyncSession = Depends(get_db)):
    username = verify_refresh_token(req.refresh_token)
    record = await get_user(db, username)
    if not record:
        raise HTTPException(status_code=401, detail="User not found")
    return Token(
        access_token=create_access_token(username),
        refresh_token=create_refresh_token(username),
        token_type="bearer",
    )


@app.post(
    "/register",
    response_model=User,
    tags=["auth"],
    responses={
        400: {"model": ErrorDetail, "description": "Validation error (username/password too short)"},
        409: {"model": ErrorDetail, "description": "Username already taken"},
    },
)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    if len(req.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if await get_user(db, req.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    result = await db.execute(select(func.count()).select_from(UserRecord))
    role = "admin" if result.scalar() == 0 else "user"
    try:
        record = await create_user(db, req.username.strip(), req.password, role=role)
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username already taken")
    logger.info(f"New user registered: {record.username} (role={record.role})")
    return User(username=record.username, role=record.role)


@app.get(
    "/users/me",
    response_model=User,
    tags=["auth"],
    responses={401: {"model": ErrorDetail, "description": "Invalid or expired token"}},
)
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


# --- Purchase endpoints ---
@app.post(
    "/purchase/",
    response_model=Purchase,
    tags=["purchases"],
    responses={
        400: {"model": ErrorDetail, "description": "Unsupported currency"},
        401: {"model": ErrorDetail, "description": "Not authenticated"},
    },
)
async def add_purchase(purchase: Purchase, db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    currency = purchase.currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Unsupported currency: {currency}")
    record = PurchaseRecord(**{**purchase.model_dump(), "currency": currency})
    db.add(record)
    await db.commit()
    await db.refresh(record)
    try:
        cache = get_redis()
        if cache:
            cache.delete(KPI_CACHE_KEY)
    except Exception:
        pass
    logger.info(f"Purchase added: customer={purchase.customer_name} amount={purchase.amount} currency={currency}")
    return record


@app.post(
    "/purchase/bulk/",
    response_model=BulkUploadResult,
    tags=["purchases"],
    responses={
        400: {"model": ErrorDetail, "description": "Invalid file format or malformed CSV row"},
        401: {"model": ErrorDetail, "description": "Not authenticated"},
    },
)
async def add_bulk_purchases(file: UploadFile = File(...), db: AsyncSession = Depends(get_db), _: User = Depends(get_current_user)):
    if file.content_type not in ["text/csv"]:
        raise HTTPException(status_code=400, detail="Invalid file format")

    contents = await file.read()
    reader = csv.DictReader(io.StringIO(contents.decode("utf-8")))

    new_records = []
    for row in reader:
        try:
            raw_currency = (row.get("currency") or "USD").strip().upper()
            if raw_currency not in SUPPORTED_CURRENCIES:
                raw_currency = "USD"
            amount = float(row["amount"].strip())
            if amount <= 0:
                await db.rollback()
                raise HTTPException(status_code=400, detail=f"Amount must be greater than zero, got {amount}")
            record = PurchaseRecord(
                customer_name=row["customer_name"].strip(),
                country=row["country"].strip(),
                purchase_date=datetime.strptime(row["purchase_date"].strip(), "%Y-%m-%d").date(),
                amount=amount,
                currency=raw_currency,
            )
            db.add(record)
            new_records.append(record)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=400, detail=f"Error processing row: {row} — {e}")

    await db.commit()
    try:
        cache = get_redis()
        if cache:
            cache.delete(KPI_CACHE_KEY)
    except Exception:
        pass
    logger.info(f"Bulk upload: {len(new_records)} purchases added")
    return BulkUploadResult(added=len(new_records))


@app.get("/purchases/", response_model=PurchasePage, tags=["purchases"])
@limiter.limit("100/minute")
async def get_purchases(
    request: Request,
    country: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    base = select(PurchaseRecord).where(PurchaseRecord.deleted_at.is_(None))
    if country:
        base = base.where(PurchaseRecord.country.ilike(country))
    if start_date:
        base = base.where(PurchaseRecord.purchase_date >= start_date)
    if end_date:
        base = base.where(PurchaseRecord.purchase_date <= end_date)

    count_result = await db.execute(select(func.count()).select_from(base.subquery()))
    total = count_result.scalar()

    items_result = await db.execute(
        base.order_by(PurchaseRecord.purchase_date.desc()).limit(limit).offset(offset)
    )
    return PurchasePage(items=items_result.scalars().all(), total=total, limit=limit, offset=offset)


@app.get(
    "/purchase/{purchase_id}",
    response_model=Purchase,
    tags=["purchases"],
    responses={404: {"model": ErrorDetail, "description": "Purchase not found"}},
)
async def get_purchase(purchase_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(PurchaseRecord).where(
            PurchaseRecord.id == purchase_id,
            PurchaseRecord.deleted_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return record


@app.delete(
    "/purchase/{purchase_id}",
    tags=["purchases"],
    responses={
        401: {"model": ErrorDetail, "description": "Not authenticated"},
        404: {"model": ErrorDetail, "description": "Purchase not found"},
    },
)
async def delete_purchase(
    purchase_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseRecord).where(
            PurchaseRecord.id == purchase_id,
            PurchaseRecord.deleted_at.is_(None),
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="Purchase not found")
    record.deleted_at = datetime.now(timezone.utc)
    await db.commit()
    try:
        cache = get_redis()
        if cache:
            cache.delete(KPI_CACHE_KEY)
    except Exception:
        pass
    logger.info(f"Purchase {purchase_id} soft-deleted by {current_user.username}")
    return {"message": f"Purchase {purchase_id} deleted"}


@app.get(
    "/purchases/kpis",
    tags=["purchases"],
    responses={
        400: {"model": ErrorDetail, "description": "Not enough data for forecast"},
        404: {"model": ErrorDetail, "description": "No purchase data"},
    },
)
@limiter.limit("30/minute")
async def get_kpis(
    request: Request,
    forecast_days: Optional[int] = Query(default=None, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
):
    cache = get_redis()
    if cache and not forecast_days:
        try:
            cached = cache.get(KPI_CACHE_KEY)
            if cached:
                logger.info("KPI cache hit")
                return json.loads(cached)
        except Exception:
            pass

    result = await db.execute(select(PurchaseRecord).where(PurchaseRecord.deleted_at.is_(None)))
    records = result.scalars().all()
    if not records:
        raise HTTPException(status_code=404, detail="No purchase data")

    client_total: dict = defaultdict(list)
    clients_per_country: dict = defaultdict(set)
    for p in records:
        client_total[p.customer_name].append(p.amount)
        clients_per_country[p.country].add(p.customer_name)

    avg_per_client = {c: mean(amounts) for c, amounts in client_total.items()}
    country_counts = {c: len(clients) for c, clients in clients_per_country.items()}

    sales_forecast = None
    if forecast_days:
        all_dates = sorted({p.purchase_date for p in records})
        if len(all_dates) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 days of purchase data for forecasting")
        min_date, max_date = all_dates[0], all_dates[-1]
        date_range = [min_date + timedelta(days=i) for i in range((max_date - min_date).days + 1)]
        daily_sales = [sum(p.amount for p in records if p.purchase_date == d) for d in date_range]
        if len(daily_sales) < 2:
            raise HTTPException(status_code=400, detail="Need more data for forecasting")
        model = ExponentialSmoothing(daily_sales, trend="add", seasonal=None)
        predicted = model.fit().forecast(forecast_days)
        sales_forecast = {f"Day {i + 1}": round(predicted[i], 2) for i in range(forecast_days)}

    result_data = {
        "mean_purchases_per_client": avg_per_client,
        "clients_per_country": country_counts,
        "sales_forecast": sales_forecast,
    }

    if cache and not forecast_days:
        try:
            cache.setex(KPI_CACHE_KEY, KPI_TTL, json.dumps(result_data))
            logger.info("KPI cache set")
        except Exception:
            pass

    return result_data
