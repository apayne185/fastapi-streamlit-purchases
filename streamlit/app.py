import streamlit as st
import requests
import pandas as pd

API_URL =  "http://localhost:8000"

st.set_page_config(page_title="Customers Purchases", layout="wide")
st.sidebar.title("Naviagtion")

tab = st.sidebar.radio("Go to:", ["Upload a Purchase", "Analyze a Purchase"])

if tab == "Upload a Purchase": 
    st.title('Upload Purchases')
    st.subheader("Add Purchase")
    
    with st.form("purchase_form"):
        customer_name = st.text_input("Name") 
        country = st.text_input("Country")  
        purchase_date = st.date_input("Purchase Date") 
        amount = st.number_input("Amount", min_value=0.01)  
        submit = st.form_submit_button("Submit Purchase")   

    if submit:
        payload = {
            "customer_name": customer_name,
            "country": country,
            "purchase_date": str(purchase_date),
            "amount": amount
        }
        response = requests.post(f"{API_URL}/purchase/", json=payload)
        if response.status_code == 200:
            st.success("Purchase added succesfully")
        else:
            st.error(f"Error: {response.json()}")


    st.subheader("Add Bulk Purchase")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])  

    if uploaded_file:
        if st.button("Upload CSV"):
            file = {"file": uploaded_file.getvalue()}
            response = requests.post(
                f"{API_URL}/purchase/bulk/",
                files={"file": ("purchases.csv", uploaded_file.read(),"text/csv")}
            )   


            if response.status_code == 200:
                st.success(f"Purchase added succesfully: {response.json()['added']} purchases")
            else:
                st.error(f"Upload Failed")

        


elif tab == "Analyze a Purchase":
    st.title('Analzye a Purchase')

    country_filter = st.text_input("Filter by Country")
    col1, col2 = st.columns(2)

    with col1:
        start_date = st.date_input("Start Date", value=None)
    with col2: 
        end_date = st.date_input("End Date", value=None)


    params = {}
    if country_filter:
        params["country"] = country_filter
    if start_date: 
        params["start_date"] = str(start_date)
    if end_date: 
        params["end_date"] = str(end_date)  
        
    response = requests.get(f"{API_URL}/purchases/", params=params)
    if response.status_code == 200:   
        data= response.json()
        if data: 
            df = pd.DataFrame(data)
            st.dataframe(df)   
        else:
            st.warning("No purchases found for the filters") 
    else:
        st.error("Failed to fetch data") 

  



    st.subheader("KPIs")
    forecast_days = st.number_input("Forecast Sales (in Days): ", min_value=1, max_value=30, value=5)

    if st.button("Compute KPIs"):
        response = requests.get(f"{API_URL}/purchases/kpis/", params={"forecast_days": forecast_days})
        if response.status_code == 200:
            kpi_data = response.json()
            # st.write("Raw API Response:", kpi_data)

            st.subheader("Average Purchases Per Client")
            if kpi_data.get("mean_purchases_per_client"):   
                df_clients = pd.DataFrame(kpi_data["mean_purchases_per_client"].items(),columns=["Client", "Average Purchase ($)"])
                st.dataframe(df_clients.style.format({"Average Purchase ($)": "${:,.2f}"}))
            else: 
                st.warning("No purchase data available.")  
     

            st.subheader("Clients Per Country")
            if kpi_data.get("clients_per_country"):
                df_countries = pd.DataFrame(kpi_data["clients_per_country"].items(), columns=["Country", "Number of Clients"])   
                st.dataframe(df_countries)
            else: 
                st.warning("No country data available.")  

             
            if kpi_data.get("sales_forecast") and kpi_data["sales_forecast"] != "Not requested": 
                st.subheader(f"Sales Forecast for Next {forecast_days} Days")
                df_forecast = pd.DataFrame(list(kpi_data["sales_forecast"].items()), columns=["Day", "Projected Sales ($)"])   
                st.dataframe(df_forecast.style.format({"Projected Sales ($)": "${:,.2f}"}))   
            else: 
                st.info("No sles forecast requested.") 
                
        
        else:
            st.error("Failed to fetch KPIs")  







