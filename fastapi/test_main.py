import pytest
from fastapi.testclient import TestClient
from datetime import date
from io import StringIO
import csv
from main import app
 

client = TestClient(app) 


@pytest.fixture 
def sample_purchase(): 
    return {
        "customer_name": "John Doe",
        "country": "USA",
        "purchase_date": str(date.today()),  
        "amount": 150.50  
    }   
 


@pytest.fixture
def sample_csv():
    csv_data = """customer_name,country,purchase_date,amount
    Alice Person,Canada,2024-12-05,250.75
    Bob Smith,UK,2024-12-06,320.40"""

    return csv_data.encode("utf-8")  
 



def test_add_purchase(sample_purchase): 
    response = client.post("/purchase/", json=sample_purchase)   
    assert response.status_code == 200
    data = response.json()  

    assert data["customer_name"] == sample_purchase["customer_name"] 
    assert data["country"] == sample_purchase["country"] 
    assert data["amount"] == sample_purchase["amount"]    
     


def test_add_bulk_purchases(sample_csv):   
    files = {"file": ("purchases.csv", sample_csv,"text/csv")}
    response = client.post("/purchase/bulk/", files=files) 

    assert response.status_code==200  
    assert "added" in response.json()     
     
  


def test_get_purchases():
    response = client.get("/purchases/")

    assert response.status_code == 200    
    assert isinstance(response.json(),list)    




def test_get_purchases_with_filters():
    response = client.get(f"/purchases/?country=Canada&start_date=2024-12-02&end_date=2024-12-10")
    
    assert response.status_code== 200 
    assert isinstance(response.json(), list)    




def test_get_kpis():
    response = client.get("/purchases/kpis")   
    
    assert response.status_code == 200    
    assert "mean_purchases_per_client" in response.json()    



def test_get_kpis_with_forecast():
    response = client.get("/purchases/kpis?forecast_days=5")

    assert response.status_code in [200, 400]        #  400 if not enough data
    if response.status_code == 200:
        assert "sales_forecast" in response.json()