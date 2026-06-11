import os
import pytest
from fastapi.testclient import TestClient
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["RATELIMIT_ENABLED"] = "false"  # disable rate limiting in tests

from database import Base, get_db
from main import app

# Use SQLite in-memory so tests need no running PostgreSQL
SQLITE_URL = "sqlite:///./test_purchases.db"
test_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def sample_purchase():
    return {
        "customer_name": "John Doe",
        "country": "USA",
        "purchase_date": str(date.today()),
        "amount": 150.50,
    }


@pytest.fixture
def sample_csv():
    csv_data = "customer_name,country,purchase_date,amount\nAlice Person,Canada,2024-12-05,250.75\nBob Smith,UK,2024-12-06,320.40"
    return csv_data.encode("utf-8")


def test_health_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_add_purchase(sample_purchase):
    response = client.post("/purchase/", json=sample_purchase)
    assert response.status_code == 200
    data = response.json()
    assert data["customer_name"] == sample_purchase["customer_name"]
    assert data["country"] == sample_purchase["country"]
    assert data["amount"] == sample_purchase["amount"]


def test_add_bulk_purchases(sample_csv):
    files = {"file": ("purchases.csv", sample_csv, "text/csv")}
    response = client.post("/purchase/bulk/", files=files)
    assert response.status_code == 200
    assert response.json()["added"] == 2


def test_get_purchases(sample_purchase):
    client.post("/purchase/", json=sample_purchase)
    response = client.get("/purchases/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_get_purchases_with_filters(sample_csv):
    client.post("/purchase/bulk/", files={"file": ("purchases.csv", sample_csv, "text/csv")})
    response = client.get("/purchases/?country=Canada&start_date=2024-12-02&end_date=2024-12-10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(p["country"].lower() == "canada" for p in data)


def test_get_kpis(sample_purchase):
    client.post("/purchase/", json=sample_purchase)
    response = client.get("/purchases/kpis")
    assert response.status_code == 200
    assert "mean_purchases_per_client" in response.json()
    assert "clients_per_country" in response.json()


def test_get_kpis_with_forecast():
    response = client.get("/purchases/kpis?forecast_days=5")
    assert response.status_code in [200, 404, 400]


def test_get_purchases_empty():
    response = client.get("/purchases/")
    assert response.status_code == 200
    assert response.json() == []


def test_bulk_upload_invalid_content_type():
    files = {"file": ("data.txt", b"not,csv,data", "text/plain")}
    response = client.post("/purchase/bulk/", files=files)
    assert response.status_code == 400
