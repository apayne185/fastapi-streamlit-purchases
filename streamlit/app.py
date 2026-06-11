import os
import streamlit as st
import requests
import pandas as pd

API_URL = os.getenv("API_URL", "http://fastapi:8000")

st.set_page_config(page_title="Customer Purchases", layout="wide")
st.sidebar.title("Navigation")
tab = st.sidebar.radio("Go to:", ["Upload a Purchase", "Analyze Purchases"])


# ── Tab 1: Upload ──────────────────────────────────────────────────────────────
if tab == "Upload a Purchase":
    st.title("Upload Purchases")
    st.subheader("Add Single Purchase")

    if "form_key" not in st.session_state:
        st.session_state.form_key = 0

    with st.form(key=f"purchase_form_{st.session_state.form_key}"):
        customer_name = st.text_input("Name")
        country = st.text_input("Country")
        purchase_date = st.date_input("Purchase Date")
        amount = st.number_input("Amount ($)", min_value=0.01)
        submit = st.form_submit_button("Submit Purchase")

    if submit:
        payload = {
            "customer_name": customer_name,
            "country": country,
            "purchase_date": str(purchase_date),
            "amount": amount,
        }
        response = requests.post(f"{API_URL}/purchase/", json=payload)
        if response.status_code == 200:
            st.success("Purchase added successfully")
            st.session_state.form_key += 1
            st.rerun()
        else:
            st.error(f"Error: {response.json()}")

    st.subheader("Bulk Upload (CSV)")
    st.caption("CSV must have columns: `customer_name, country, purchase_date (YYYY-MM-DD), amount`")
    uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

    if uploaded_file:
        file_content = uploaded_file.read()
        if st.button("Upload CSV"):
            response = requests.post(
                f"{API_URL}/purchase/bulk/",
                files={"file": ("purchases.csv", file_content, "text/csv")},
            )
            if response.status_code == 200:
                st.success(f"Uploaded successfully: {response.json()['added']} purchases added")
            else:
                st.error(f"Upload failed: {response.text}")


# ── Tab 2: Analyse ─────────────────────────────────────────────────────────────
elif tab == "Analyze Purchases":
    st.title("Analyze Purchases")

    # Filters
    with st.expander("Filters", expanded=True):
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

    if response.status_code != 200:
        st.error("Failed to fetch data")
        st.stop()

    data = response.json()

    if not data:
        st.warning("No purchases found for the selected filters")
        st.stop()

    df = pd.DataFrame(data)
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    df["amount"] = df["amount"].astype(float)

    # ── Summary metrics ────────────────────────────────────────────────────────
    total_revenue = df["amount"].sum()
    total_purchases = len(df)
    avg_order = df["amount"].mean()
    unique_customers = df["customer_name"].nunique()

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"${total_revenue:,.2f}")
    m2.metric("Total Purchases", total_purchases)
    m3.metric("Avg Order Value", f"${avg_order:,.2f}")
    m4.metric("Unique Customers", unique_customers)

    st.divider()

    # ── Charts ─────────────────────────────────────────────────────────────────
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader("Revenue by Country")
        country_revenue = (
            df.groupby("country")["amount"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"country": "Country", "amount": "Revenue ($)"})
        )
        st.bar_chart(country_revenue.set_index("Country"))

    with chart_col2:
        st.subheader("Revenue Over Time")
        daily_revenue = (
            df.groupby("purchase_date")["amount"]
            .sum()
            .reset_index()
            .rename(columns={"purchase_date": "Date", "amount": "Revenue ($)"})
        )
        st.line_chart(daily_revenue.set_index("Date"))

    st.subheader("Top 10 Customers by Spend")
    top_customers = (
        df.groupby("customer_name")["amount"]
        .sum()
        .nlargest(10)
        .reset_index()
        .rename(columns={"customer_name": "Customer", "amount": "Total Spend ($)"})
    )
    st.bar_chart(top_customers.set_index("Customer"))

    st.divider()

    # ── Raw data table ─────────────────────────────────────────────────────────
    with st.expander("Raw Data", expanded=False):
        st.dataframe(df, use_container_width=True)

    # ── KPIs & Forecast ────────────────────────────────────────────────────────
    st.subheader("KPIs & Sales Forecast")
    forecast_days = st.number_input("Forecast horizon (days):", min_value=1, max_value=30, value=5)

    if st.button("Compute KPIs"):
        kpi_resp = requests.get(f"{API_URL}/purchases/kpis", params={"forecast_days": forecast_days})
        if kpi_resp.status_code != 200:
            st.error("Failed to fetch KPIs")
            st.stop()

        kpi = kpi_resp.json()

        kpi_col1, kpi_col2 = st.columns(2)

        with kpi_col1:
            st.subheader("Avg Purchase per Client")
            if kpi.get("mean_purchases_per_client"):
                df_clients = pd.DataFrame(
                    kpi["mean_purchases_per_client"].items(),
                    columns=["Client", "Avg Purchase ($)"],
                ).sort_values("Avg Purchase ($)", ascending=False)
                st.dataframe(
                    df_clients.style.format({"Avg Purchase ($)": "${:,.2f}"}),
                    use_container_width=True,
                )

        with kpi_col2:
            st.subheader("Clients per Country")
            if kpi.get("clients_per_country"):
                df_countries = pd.DataFrame(
                    kpi["clients_per_country"].items(),
                    columns=["Country", "Clients"],
                ).sort_values("Clients", ascending=False)
                st.dataframe(df_countries, use_container_width=True)
                st.bar_chart(df_countries.set_index("Country"))

        if kpi.get("sales_forecast") and kpi["sales_forecast"] != "Not requested":
            st.subheader(f"Sales Forecast — Next {forecast_days} Days")
            df_forecast = pd.DataFrame(
                kpi["sales_forecast"].items(),
                columns=["Day", "Projected Revenue ($)"],
            )
            st.line_chart(df_forecast.set_index("Day"))
            st.dataframe(
                df_forecast.style.format({"Projected Revenue ($)": "${:,.2f}"}),
                use_container_width=True,
            )
