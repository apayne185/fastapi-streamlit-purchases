# Customer Purchases API & Streamlit App

## Overview

A system with three components:

1. **Backend (FastAPI)**  
   - A REST API that manages customer purchase data in-memory and provides analytics.
   - Endpoints to:
     - Add a single purchase (`/purchase/`).
     - Bulk upload purchases from a CSV (`/purchase/bulk/`).
     - Retrieves filtered purchase data (by date and country).
     - Computes KPIs (mean purchases per client, clients per country, and forecast sales).


2. **Frontend (Streamlit)**  
   - A web-based dashboard with two tabs that interacts with the API to provide insights on the data:
     - **Upload Tab**: Form for a single purchase entry and CSV file upload.
     - **Analyse Tab**: Filters (by date and country) and display KPIs from the API.


3. **Dockerization**  
   - Containerizes both the FastAPI and Streamlit applications.



## Requirements
1. Install Docker 
2. Install Docker Desktop

## Running the Project
### Running with Docker Compose

To build and start the Streamlit UI and the FastAPI, run:

```docker-compose up --build```

This will start the backend on  `http://localhost:8000` and the frontend on `http://localhost:8501`.  

**To acess the website, enter `http://localhost:8501` into your search engine.**

To stop the services, run: 

```docker-compose down```

### Running Locally
#### FastAPI Backend
1. `cd fastapi`
2. `pip install -r requirements.txt`
3. `uvicorn main:app --reload --host 0.0.0.0 --port 8000`

#### Streamlit Frontend
1. `cd streamlit`
2. `pip install -r requirements.txt`
3. `streamlit run app.py` 



## FastAPI Backend 
### Features
* Add a single customer purchase with the API
* Add a bulk upload of customer purchases using a CSV file. 
* Retrieve purhcase information using filters (country, date range).
* KPI's: computes average purchases per client and customer distribution per country.
* Forecasting for future sales (using Exponential Smoothing).
* Testing using pytest. 

## Streamlit Frontend
### Features
* Upload a single/bulk purchase
* Analyze, filter, and visualize purchases
* Connects with the FastAPI backend.


## API Endpoints
* POST
  * **/purchase/**   Add a single purchase
  * **/purchase/bulk/**   Upload purchases from CSV
* GET
  * **/purchases/**    Retrieve purchases with filters
  * **/purchases/kpis**    Get KPI/forecast sales


## Testing
To run the tests, 
1. `cd fastapi`
2. `pytest test_main.py`

