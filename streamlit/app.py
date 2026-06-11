import os
import streamlit as st
import requests
import pandas as pd

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "SEK", "NOK", "DKK"]

# Illustrative static rates vs USD (not live)
RATES_TO_USD = {
    "USD": 1.00, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0067,
    "CAD": 0.74, "AUD": 0.65, "CHF": 1.13, "SEK": 0.095,
    "NOK": 0.094, "DKK": 0.145,
}

def to_usd(amount: float, currency: str) -> float:
    return amount * RATES_TO_USD.get(currency, 1.0)

def convert(amount_usd: float, target: str) -> float:
    return amount_usd / RATES_TO_USD.get(target, 1.0)

API_URL = os.getenv("API_URL", "http://fastapi:8000")

st.set_page_config(page_title="Customer Purchases", page_icon="assets/icon.png" if os.path.exists("assets/icon.png") else None, layout="wide")

# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Customer Purchases")
st.sidebar.caption("Purchase analytics and management platform")
st.sidebar.divider()
tab = st.sidebar.radio("Navigate", ["Upload Purchases", "Analyze Purchases"])
st.sidebar.divider()
st.sidebar.caption(f"API: `{API_URL}`")


def api_get(path, params=None):
    try:
        return requests.get(f"{API_URL}{path}", params=params, timeout=10)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Is the backend running?")
        st.stop()


def api_post(path, **kwargs):
    try:
        return requests.post(f"{API_URL}{path}", timeout=10, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Is the backend running?")
        st.stop()


# ── Tab 1: Upload ──────────────────────────────────────────────────────────────
if tab == "Upload Purchases":
    st.title("Upload Purchases")

    col_single, col_bulk = st.columns(2, gap="large")

    with col_single:
        st.subheader("Single Purchase")

        if "form_key" not in st.session_state:
            st.session_state.form_key = 0
        if "submit_attempted" not in st.session_state:
            st.session_state.submit_attempted = False

        _err = '<p style="color:#e53e3e;font-size:0.8em;margin-top:-12px;margin-bottom:8px">Required field</p>'

        customer_name = st.text_input("Customer Name *", key=f"name_{st.session_state.form_key}")
        if st.session_state.submit_attempted and not customer_name.strip():
            st.markdown(_err, unsafe_allow_html=True)

        country = st.text_input("Country *", key=f"country_{st.session_state.form_key}")
        if st.session_state.submit_attempted and not country.strip():
            st.markdown(_err, unsafe_allow_html=True)

        purchase_date = st.date_input("Purchase Date", key=f"date_{st.session_state.form_key}")
        amt_col, cur_col = st.columns([3, 1])
        with amt_col:
            amount = st.number_input("Amount", min_value=0.01, format="%.2f", key=f"amount_{st.session_state.form_key}")
        with cur_col:
            currency = st.selectbox("Currency", CURRENCIES, key=f"currency_{st.session_state.form_key}")

        submit = st.button("Submit Purchase", use_container_width=True, type="primary")

        if submit:
            if not customer_name.strip() or not country.strip():
                st.session_state.submit_attempted = True
                st.rerun()
            else:
                st.session_state.submit_attempted = False
                with st.spinner("Saving..."):
                    response = api_post(
                        "/purchase/",
                        json={
                            "customer_name": customer_name.strip(),
                            "country": country.strip(),
                            "purchase_date": str(purchase_date),
                            "amount": amount,
                            "currency": currency,
                        },
                    )
                if response.status_code == 200:
                    st.success(f"Purchase saved — {currency} {amount:,.2f}")
                    st.session_state.form_key += 1
                    st.session_state.submit_attempted = False
                    st.rerun()
                else:
                    st.error(f"Error: {response.json()}")

    with col_bulk:
        st.subheader("Bulk Upload (CSV)")
        st.caption("Required columns: `customer_name`, `country`, `purchase_date` (YYYY-MM-DD), `amount`")
        uploaded_file = st.file_uploader("Choose a CSV file", type=["csv"])

        if uploaded_file:
            preview = pd.read_csv(uploaded_file)
            st.dataframe(preview.head(5), use_container_width=True)
            uploaded_file.seek(0)

            if st.button("Upload", use_container_width=True, type="primary"):
                with st.spinner(f"Uploading {len(preview)} rows..."):
                    response = api_post(
                        "/purchase/bulk/",
                        files={"file": ("purchases.csv", uploaded_file.read(), "text/csv")},
                    )
                if response.status_code == 200:
                    st.success(f"Successfully uploaded {response.json()['added']} purchases")
                else:
                    st.error(f"Upload failed: {response.text}")


# ── Tab 2: Analyse ─────────────────────────────────────────────────────────────
elif tab == "Analyze Purchases":
    st.title("Analyze Purchases")

    # Display currency
    display_currency = st.selectbox(
        "Display currency",
        CURRENCIES,
        help="All amounts are converted to this currency for display. Rates are illustrative, not live.",
    )

    # Filters
    with st.expander("Filters", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            country_filter = st.text_input("Country")
        with col2:
            start_date = st.date_input("From", value=None)
        with col3:
            end_date = st.date_input("To", value=None)

    params = {}
    if country_filter:
        params["country"] = country_filter
    if start_date:
        params["start_date"] = str(start_date)
    if end_date:
        params["end_date"] = str(end_date)

    with st.spinner("Loading purchases..."):
        response = api_get("/purchases/", params=params)

    if response.status_code != 200:
        st.error("Failed to fetch data")
        st.stop()

    data = response.json()

    if not data:
        st.info("No purchases found for the selected filters.")
        st.stop()

    df = pd.DataFrame(data)
    df["purchase_date"] = pd.to_datetime(df["purchase_date"])
    df["amount"] = df["amount"].astype(float)
    if "currency" not in df.columns:
        df["currency"] = "USD"

    # Convert all amounts to the selected display currency via USD as base
    df["amount_display"] = df.apply(
        lambda r: convert(to_usd(r["amount"], r["currency"]), display_currency), axis=1
    )

    sym = display_currency

    # ── Summary metrics ────────────────────────────────────────────────────────
    st.caption(f"Showing {len(df):,} purchase{'s' if len(df) != 1 else ''} — amounts in {display_currency}")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"{sym} {df['amount_display'].sum():,.2f}")
    m2.metric("Total Purchases", f"{len(df):,}")
    m3.metric("Avg Order Value", f"{sym} {df['amount_display'].mean():,.2f}")
    m4.metric("Unique Customers", f"{df['customer_name'].nunique():,}")

    st.divider()

    # ── Charts ─────────────────────────────────────────────────────────────────
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader(f"Revenue by Country ({display_currency})")
        country_revenue = (
            df.groupby("country")["amount_display"]
            .sum()
            .sort_values(ascending=False)
            .rename(f"Revenue ({display_currency})")
        )
        st.bar_chart(country_revenue)

    with chart_col2:
        st.subheader(f"Revenue Over Time ({display_currency})")
        daily_revenue = (
            df.groupby("purchase_date")["amount_display"]
            .sum()
            .rename(f"Revenue ({display_currency})")
        )
        st.line_chart(daily_revenue)

    st.subheader(f"Top 10 Customers ({display_currency})")
    top_customers = (
        df.groupby("customer_name")["amount_display"]
        .sum()
        .nlargest(10)
        .rename(f"Total Spend ({display_currency})")
    )
    st.bar_chart(top_customers)

    st.divider()

    with st.expander("Raw Data Table"):
        display_df = df[["customer_name", "country", "purchase_date", "amount", "currency", "amount_display"]].copy()
        display_df = display_df.rename(columns={"amount_display": f"amount ({display_currency})"})
        st.dataframe(
            display_df.style.format({
                "amount": "{:,.2f}",
                f"amount ({display_currency})": "{:,.2f}",
            }),
            use_container_width=True,
        )
        st.download_button(
            label="Download as CSV",
            data=df.to_csv(index=False),
            file_name="purchases_export.csv",
            mime="text/csv",
        )

    # ── KPIs & Forecast ────────────────────────────────────────────────────────
    st.subheader("KPIs & Sales Forecast")
    forecast_days = st.number_input("Forecast horizon (days):", min_value=1, max_value=30, value=5)

    if st.button("Compute KPIs", type="primary"):
        with st.spinner("Computing..."):
            kpi_resp = api_get("/purchases/kpis", params={"forecast_days": forecast_days})

        if kpi_resp.status_code != 200:
            st.error(f"Failed to fetch KPIs: {kpi_resp.text}")
            st.stop()

        kpi = kpi_resp.json()
        kpi_col1, kpi_col2 = st.columns(2)

        with kpi_col1:
            st.subheader("Avg Purchase per Client")
            if kpi.get("mean_purchases_per_client"):
                df_clients = (
                    pd.DataFrame(kpi["mean_purchases_per_client"].items(), columns=["Client", "Avg ($)"])
                    .sort_values("Avg ($)", ascending=False)
                )
                st.dataframe(
                    df_clients.style.format({"Avg ($)": "${:,.2f}"}),
                    use_container_width=True,
                )

        with kpi_col2:
            st.subheader("Clients per Country")
            if kpi.get("clients_per_country"):
                df_countries = (
                    pd.DataFrame(kpi["clients_per_country"].items(), columns=["Country", "Clients"])
                    .sort_values("Clients", ascending=False)
                )
                st.dataframe(df_countries, use_container_width=True)
                st.bar_chart(df_countries.set_index("Country"))

        if kpi.get("sales_forecast") and kpi["sales_forecast"] != "Not requested":
            st.subheader(f"Sales Forecast — Next {forecast_days} Days")
            df_forecast = pd.DataFrame(
                kpi["sales_forecast"].items(), columns=["Day", "Projected Revenue ($)"]
            )
            st.line_chart(df_forecast.set_index("Day"))
            st.dataframe(
                df_forecast.style.format({"Projected Revenue ($)": "${:,.2f}"}),
                use_container_width=True,
            )
