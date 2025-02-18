from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from datetime import date, datetime, timezone
from typing import Optional, List
from statistics import mean
import io
import csv
from collections import defaultdict


app = FastAPI(title="Customer Purchases API")

# In-memory storage
purchases = []

class Purchase(BaseModel):
    customer_name: str
    country: str
    purchase_date: date
    amount: float

@app.post("/purchase/", response_model=Purchase)
async def add_purchase(purchase: Purchase):
    purchases.append(purchase)
    return purchase


@app.post("/purchase/bulk/")
async def add_bulk_purchases(file: UploadFile = File(...)):
    if file.content_type not in ["text/csv"]:
        raise HTTPException(status_code=400, detail="Invalid file format")
    contents = await file.read()
    decoded = contents.decode("utf-8")
    reader = csv.DictReader(io.StringIO(decoded))
    new_purchases = []
    for row in reader:
        try:
            purchase = Purchase(
                customer_name=row["customer_name"],
                country=row["country"],
                purchase_date=date.fromisoformat(row["purchase_date"]),
                amount=float(row["amount"])
            )
            purchases.append(purchase)
            new_purchases.append(purchase)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Error processing row: {row} - {e}")
    return JSONResponse(content={"added": len(new_purchases)})


@app.get("/purchases/", response_model=List[Purchase])
def get_purchases(country: Optional[str] = None, start_date: Optional[date] = None, end_date: Optional[date] = None):
    filtered = purchases
    if country:
        filtered = [p for p in filtered if p.country.lower() == country.lower()]
    if start_date:
        filtered = [p for p in filtered if p.purchase_date >= start_date]
    if end_date:
        filtered = [p for p in filtered if p.purchase_date <= end_date]
    return filtered


@app.get("/purchases/kpis")
def get_kpis(forecast_days: Optional[int] = None):
    if not purchases:
        raise HTTPException(status_code=404, detail="No purchase data")
    
    client_total = defaultdict(list)
    for p in purchases:
        client_total[p.customer_name].append(p.amount)

    avg_purchase_per_client = {
        client: mean(amounts) for client, amounts in client_total.items()
    }

    clients_per_country = defaultdict(set)
    for p in purchases: 
        clients_per_country[p.country].add(p.customer_name)
    
    clients_per_country = {
        country: len(clients) for country, clients in clients_per_country.items()
    }

    sales_forecast = None
    if forecast_days:
        today =  datetime.now(timezone.utc).date()
        recent_purchases = [p for p in purchases if (today - p.purchase_date).days <= 30]
        if recent_purchases: 
            daily_total= defaultdict(float)
            for p in recent_purchases:
                daily_total[p.purchase_date] += p.amount
            
            avg_daily_sales = mean(daily_total.values())
            sales_forecast = {f"Day {i+1}": round(avg_daily_sales, 2) for i in range(forecast_days)}


    return {
        "mean_purchases_per_client": avg_purchase_per_client,
        "clients_per_country": clients_per_country,
        "sales_forecast": sales_forecast if forecast_days else "Not requested"
    }


