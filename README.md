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

This will start the backend on  `http://localhost:8000` and the frontend on `http://localhost:8501`.   To acess the website, enter `http://localhost:8501` into your search engine. 

To stop the services, run: 

```docker-compose down```


## FastAPI Backend 
### Features
* Add a single customer purchase with the API
* Add a bulk upload of customer purchases using a CSV file. 
* Retrieve purhcase information using filters (country, date range)
* Delete all purchases 



- Use the provided repository as your starting point:
  - **FastAPI code:** located at `fastapi/main.py`
  - **Sample CSV file:** `sample_purchase.csv` (CSV format only)
- Data should be stored in-memory.
- Document your work in a custom README (this file should be replaced with your own version).
- Use Git with regular, small commits (feature branches recommended).
- Write unit tests for key backend functionality.


## Evaluation Criteria

- **Code Quality:** Clean, modular, and well-commented code.
- **Documentation:** A clear README explaining:
  - The system architecture.
  - Setup and running instructions.
  - Design decisions and any trade-offs.
- **Testing:** Adequate unit tests for backend endpoints.
- **Version Control:** Frequent commits and proper branching.
- **Dockerization:** Successful containerization with clear local run instructions.

## Getting Started

1. **Clone the Repository:**  
   `git clone https://github.com/merck-test/software-developer-test.git`

2. **Backend:**  
   - Review and enhance the FastAPI code in `fastapi/main.py`.

3. **Frontend:**  
   - Build a Streamlit app to interact with the FastAPI endpoints.

4. **Docker:**  
   - Create Dockerfiles for both the FastAPI and Streamlit applications.
   - Provide instructions to build and run the containers.

5. **Testing & Documentation:**  
   - Write unit tests for backend functionality.
   - Update this README with your explanations and setup instructions.

## Submission

Submit your GitHub repository link once completed. Ensure your repo includes:
- Your updated README.
- Enhanced FastAPI and Streamlit code.
- Dockerfiles and clear run instructions.
- Unit tests for the backend.

Good luck and happy coding!