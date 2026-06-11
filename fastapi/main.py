from contextlib import asynccontextmanager
from collections import defaultdict
from datetime import date, datetime, timedelta
from statistics import mean
from typing import Optional, List
import io
import csv
import json
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from statsmodels.tsa.holtwinters import ExponentialSmoothing

from database import get_db
from models import PurchaseRecord


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
    logger.info("Application startup — schema managed by Alembic")
    yield


app = FastAPI(title="Customer Purchases API", lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

Instrumentator().instrument(app).expose(app)


SUPPORTED_CURRENCIES = {"USD","EUR","GBP","JPY","CAD","AUD","CHF","SEK","NOK","DKK"}

# --- Pydantic schema ---
class Purchase(BaseModel):
    customer_name: str
    country: str
    purchase_date: date
    amount: float
    currency: str = "USD"

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


# --- Purchase endpoints ---
@app.post("/purchase/", response_model=Purchase)
def add_purchase(purchase: Purchase, db: Session = Depends(get_db)):
    currency = purchase.currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"Unsupported currency: {currency}")
    record = PurchaseRecord(**{**purchase.model_dump(), "currency": currency})
    db.add(record)
    db.commit()
    db.refresh(record)
    logger.info(f"Purchase added: customer={purchase.customer_name} amount={purchase.amount} currency={currency}")
    return record


@app.post("/purchase/bulk/")
async def add_bulk_purchases(file: UploadFile = File(...), db: Session = Depends(get_db)):
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
    logger.info(f"Bulk upload: {len(new_records)} purchases added")
    return JSONResponse(content={"added": len(new_records)})


@app.get("/purchases/", response_model=List[Purchase])
@limiter.limit("100/minute")
def get_purchases(
    request: Request,
    country: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = 500,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    query = db.query(PurchaseRecord)
    if country:
        query = query.filter(PurchaseRecord.country.ilike(country))
    if start_date:
        query = query.filter(PurchaseRecord.purchase_date >= start_date)
    if end_date:
        query = query.filter(PurchaseRecord.purchase_date <= end_date)
    return query.order_by(PurchaseRecord.purchase_date.desc()).limit(limit).offset(offset).all()


@app.get("/purchases/kpis")
@limiter.limit("30/minute")
def get_kpis(request: Request, forecast_days: Optional[int] = None, db: Session = Depends(get_db)):
    records = db.query(PurchaseRecord).all()
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
        # Build a daily series from the actual date range of the data
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

    return {
        "mean_purchases_per_client": avg_per_client,
        "clients_per_country": country_counts,
        "sales_forecast": sales_forecast if forecast_days else "Not requested",
    }
