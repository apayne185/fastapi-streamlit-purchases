import os
import pytest
from fastapi.testclient import TestClient
from datetime import date
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["RATELIMIT_ENABLED"] = "false"

from database import Base, get_db
from main import app

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
def auth_headers():
    """Register a test user and return a valid Bearer token header."""
    client.post("/register", json={"username": "testuser", "password": "testpass123"})
    resp = client.post("/token", data={"username": "testuser", "password": "testpass123"})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def sample_purchase():
    return {
        "customer_name": "John Doe",
        "country": "USA",
        "purchase_date": str(date.today()),
        "amount": 150.50,
        "currency": "USD",
    }


@pytest.fixture
def sample_csv():
    csv_data = "customer_name,country,purchase_date,amount,currency\nAlice Person,Canada,2024-12-05,250.75,CAD\nBob Smith,UK,2024-12-06,320.40,GBP"
    return csv_data.encode("utf-8")


# --- Health ---

def test_health_check():
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


# --- Auth ---

def test_register_success():
    resp = client.post("/register", json={"username": "newuser", "password": "securepass1"})
    assert resp.status_code == 200
    assert resp.json()["username"] == "newuser"


def test_register_duplicate():
    client.post("/register", json={"username": "dupeuser", "password": "securepass1"})
    resp = client.post("/register", json={"username": "dupeuser", "password": "securepass1"})
    assert resp.status_code == 409


def test_register_short_password():
    resp = client.post("/register", json={"username": "newuser", "password": "short"})
    assert resp.status_code == 400


def test_login_success():
    client.post("/register", json={"username": "loginuser", "password": "testpass123"})
    resp = client.post("/token", data={"username": "loginuser", "password": "testpass123"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password():
    client.post("/register", json={"username": "loginuser", "password": "testpass123"})
    resp = client.post("/token", data={"username": "loginuser", "password": "wrongpass"})
    assert resp.status_code == 401


def test_users_me(auth_headers):
    resp = client.get("/users/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


def test_users_me_unauthenticated():
    resp = client.get("/users/me")
    assert resp.status_code == 401


# --- Purchases ---

def test_add_purchase(auth_headers, sample_purchase):
    response = client.post("/purchase/", json=sample_purchase, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["customer_name"] == sample_purchase["customer_name"]
    assert data["country"] == sample_purchase["country"]
    assert data["amount"] == sample_purchase["amount"]


def test_add_purchase_unauthenticated(sample_purchase):
    response = client.post("/purchase/", json=sample_purchase)
    assert response.status_code == 401


def test_add_bulk_purchases(auth_headers, sample_csv):
    files = {"file": ("purchases.csv", sample_csv, "text/csv")}
    response = client.post("/purchase/bulk/", files=files, headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["added"] == 2


def test_get_purchases(auth_headers, sample_purchase):
    client.post("/purchase/", json=sample_purchase, headers=auth_headers)
    response = client.get("/purchases/")
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_get_purchases_with_filters(auth_headers, sample_csv):
    client.post("/purchase/bulk/", files={"file": ("purchases.csv", sample_csv, "text/csv")}, headers=auth_headers)
    response = client.get("/purchases/?country=Canada&start_date=2024-12-02&end_date=2024-12-10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert all(p["country"].lower() == "canada" for p in data)


def test_get_kpis(auth_headers, sample_purchase):
    client.post("/purchase/", json=sample_purchase, headers=auth_headers)
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


def test_bulk_upload_invalid_content_type(auth_headers):
    files = {"file": ("data.txt", b"not,csv,data", "text/plain")}
    response = client.post("/purchase/bulk/", files=files, headers=auth_headers)
    assert response.status_code == 400


def test_add_purchase_negative_amount(auth_headers):
    response = client.post("/purchase/", json={
        "customer_name": "Test", "country": "US",
        "purchase_date": str(date.today()), "amount": -10.0, "currency": "USD",
    }, headers=auth_headers)
    assert response.status_code == 422


def test_add_purchase_zero_amount(auth_headers):
    response = client.post("/purchase/", json={
        "customer_name": "Test", "country": "US",
        "purchase_date": str(date.today()), "amount": 0.0, "currency": "USD",
    }, headers=auth_headers)
    assert response.status_code == 422


def test_get_purchases_limit_exceeded():
    response = client.get("/purchases/?limit=9999")
    assert response.status_code == 422


def test_get_kpis_forecast_days_exceeded(auth_headers, sample_purchase):
    client.post("/purchase/", json=sample_purchase, headers=auth_headers)
    response = client.get("/purchases/kpis?forecast_days=999")
    assert response.status_code == 422


# --- Soft Delete ---

def test_delete_purchase(auth_headers, sample_purchase):
    add_resp = client.post("/purchase/", json=sample_purchase, headers=auth_headers)
    purchase_id = add_resp.json()["id"]
    del_resp = client.delete(f"/purchase/{purchase_id}", headers=auth_headers)
    assert del_resp.status_code == 200
    assert "deleted" in del_resp.json()["message"]
    # Should no longer appear in GET
    get_resp = client.get("/purchases/")
    assert all(p["id"] != purchase_id for p in get_resp.json())


def test_delete_purchase_unauthenticated(auth_headers, sample_purchase):
    add_resp = client.post("/purchase/", json=sample_purchase, headers=auth_headers)
    purchase_id = add_resp.json()["id"]
    del_resp = client.delete(f"/purchase/{purchase_id}")
    assert del_resp.status_code == 401


def test_delete_purchase_not_found(auth_headers):
    del_resp = client.delete("/purchase/99999", headers=auth_headers)
    assert del_resp.status_code == 404
