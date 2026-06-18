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
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import text
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from statsmodels.tsa.holtwinters import ExponentialSmoothing

import redis as redis_lib

from database import get_db, SessionLocal
from models import PurchaseRecord, UserRecord
from auth import Token, User, authenticate_user, create_access_token, get_current_user, get_user, create_user

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
KPI_TTL = 60  # seconds


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
    with SessionLocal() as db:
        if not db.query(UserRecord).first():
            admin_password = os.getenv("ADMIN_PASSWORD", "purchases123")
            create_user(db, "admin", admin_password, role="admin")
            logger.info("Seeded default admin user")
    yield


app = FastAPI(title="Customer Purchases API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Instrumentator().instrument(app).expose(app)


SUPPORTED_CURRENCIES = {"USD","EUR","GBP","JPY","CAD","AUD","CHF","SEK","NOK","DKK"}

# --- Pydantic schema ---
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


# --- Health / readiness probes ---
@app.get("/healthz", tags=["ops"])
def health_check():
    return {"status": "healthy"}


@app.get("/readyz", tags=["ops"])
def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception:
        raise HTTPException(status_code=503, detail="Database not ready")


# --- Auth endpoints ---

class RegisterRequest(BaseModel):
    username: str
    password: str


@app.post("/token", response_model=Token, tags=["auth"])
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    return Token(access_token=create_access_token(user.username), token_type="bearer")


@app.post("/register", response_model=User, tags=["auth"])
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if len(req.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if get_user(db, req.username):
        raise HTTPException(status_code=409, detail="Username already taken")
    role = "admin" if db.query(UserRecord).count() == 0 else "user"
    record = create_user(db, req.username.strip(), req.password, role=role)
    logger.info(f"New user registered: {record.username} (role={record.role})")
    return User(username=record.username, role=record.role)


@app.get("/users/me", response_model=User, tags=["auth"])
async def read_current_user(current_user: User = Depends(get_current_user)):
    return current_user


# --- Purchase endpoints ---
@app.post("/purchase/", response_model=Purchase)
def add_purchase(purchase: Purchase, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    currency = purchase.currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Unsupported currency: {currency}")
    record = PurchaseRecord(**{**purchase.model_dump(), "currency": currency})
    db.add(record)
    db.commit()
    db.refresh(record)
    try:
        cache = get_redis()
        if cache:
            cache.delete(KPI_CACHE_KEY)
    except Exception:
        pass
    logger.info(f"Purchase added: customer={purchase.customer_name} amount={purchase.amount} currency={currency}")
    return record


@app.post("/purchase/bulk/")
async def add_bulk_purchases(file: UploadFile = File(...), db: Session = Depends(get_db), _: User = Depends(get_current_user)):
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
            record = PurchaseRecord(
                customer_name=row["customer_name"].strip(),
                country=row["country"].strip(),
                purchase_date=datetime.strptime(row["purchase_date"].strip(), "%Y-%m-%d").date(),
                amount=float(row["amount"].strip()),
                currency=raw_currency,
            )
            db.add(record)
            new_records.append(record)
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"Error processing row: {row} — {e}")

    db.commit()
    try:
        cache = get_redis()
        if cache:
            cache.delete(KPI_CACHE_KEY)
    except Exception:
        pass
    logger.info(f"Bulk upload: {len(new_records)} purchases added")
    return JSONResponse(content={"added": len(new_records)})


@app.get("/purchases/", response_model=List[Purchase])
@limiter.limit("100/minute")
def get_purchases(
    request: Request,
    country: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=500, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseRecord).filter(PurchaseRecord.deleted_at.is_(None))
    if country:
        query = query.filter(PurchaseRecord.country.ilike(country))
    if start_date:
        query = query.filter(PurchaseRecord.purchase_date >= start_date)
    if end_date:
        query = query.filter(PurchaseRecord.purchase_date <= end_date)
    return query.order_by(PurchaseRecord.purchase_date.desc()).limit(limit).offset(offset).all()


@app.delete("/purchase/{purchase_id}", tags=["purchases"])
def delete_purchase(
    purchase_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(PurchaseRecord).filter(
        PurchaseRecord.id == purchase_id,
        PurchaseRecord.deleted_at.is_(None),
    ).first()
    if not record:
        raise HTTPException(status_code=404, detail="Purchase not found")
    record.deleted_at = datetime.now(timezone.utc)
    db.commit()
    try:
        cache = get_redis()
        if cache:
            cache.delete(KPI_CACHE_KEY)
    except Exception:
        pass
    logger.info(f"Purchase {purchase_id} soft-deleted by {current_user.username}")
    return {"message": f"Purchase {purchase_id} deleted"}


@app.get("/purchases/kpis")
@limiter.limit("30/minute")
def get_kpis(request: Request, forecast_days: Optional[int] = Query(default=None, ge=1, le=90), db: Session = Depends(get_db)):
    # Only cache the no-forecast variant — forecasts are parameterised and cheap to recompute
    cache = get_redis()
    if cache and not forecast_days:
        try:
            cached = cache.get(KPI_CACHE_KEY)
            if cached:
                logger.info("KPI cache hit")
                return json.loads(cached)
        except Exception:
            pass

    records = db.query(PurchaseRecord).filter(PurchaseRecord.deleted_at.is_(None)).all()
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

    result = {
        "mean_purchases_per_client": avg_per_client,
        "clients_per_country": country_counts,
        "sales_forecast": sales_forecast if forecast_days else "Not requested",
    }

    if cache and not forecast_days:
        try:
            cache.setex(KPI_CACHE_KEY, KPI_TTL, json.dumps(result))
            logger.info("KPI cache set")
        except Exception:
            pass

    return result
