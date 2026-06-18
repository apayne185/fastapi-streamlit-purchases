import os
import streamlit as st
import requests
import pandas as pd
import plotly.express as px

CURRENCIES = ["USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CHF", "SEK", "NOK", "DKK"]

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


# --- Auth helpers ---

def _auth_header() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _do_login(username: str, password: str):
    try:
        resp = requests.post(
            f"{API_URL}/token",
            data={"username": username, "password": password},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        st.sidebar.error("Cannot reach the API.")
        return
    if resp.status_code == 200:
        st.session_state.token = resp.json()["access_token"]
        st.session_state.username = username
        st.rerun()
    else:
        st.sidebar.error("Invalid username or password.")


def _do_register(username: str, password: str, confirm: str):
    if not username.strip():
        st.sidebar.error("Username is required.")
        return
    if len(password) < 8:
        st.sidebar.error("Password must be at least 8 characters.")
        return
    if password != confirm:
        st.sidebar.error("Passwords do not match.")
        return
    try:
        resp = requests.post(
            f"{API_URL}/register",
            json={"username": username.strip(), "password": password},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        st.sidebar.error("Cannot reach the API.")
        return
    if resp.status_code == 200:
        _do_login(username.strip(), password)
    elif resp.status_code == 409:
        st.sidebar.error("Username already taken.")
    else:
        st.sidebar.error(resp.json().get("detail", "Registration failed."))


def api_get(path, params=None):
    try:
        return requests.get(f"{API_URL}{path}", params=params, headers=_auth_header(), timeout=10)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Is the backend running?")
        st.stop()


def api_post(path, **kwargs):
    try:
        headers = kwargs.pop("headers", {})
        headers.update(_auth_header())
        return requests.post(f"{API_URL}{path}", timeout=10, headers=headers, **kwargs)
    except requests.exceptions.ConnectionError:
        st.error("Cannot reach the API. Is the backend running?")
        st.stop()


# ── Sidebar ────────────────────────────────────────────────────────────────────
st.sidebar.title("Customer Purchases")
st.sidebar.caption("Purchase analytics and management platform")
st.sidebar.divider()

if st.session_state.get("token"):
    st.sidebar.success(f"Signed in as **{st.session_state.username}**")
    if st.sidebar.button("Sign out"):
        st.session_state.pop("token", None)
        st.session_state.pop("username", None)
        st.rerun()
else:
    auth_mode = st.sidebar.radio("Auth mode", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed")

    if auth_mode == "Sign in":
        with st.sidebar.form("login_form"):
            st.subheader("Sign in")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login", use_container_width=True):
                _do_login(username, password)
    else:
        with st.sidebar.form("register_form"):
            st.subheader("Create account")
            new_username = st.text_input("Username")
            new_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            if st.form_submit_button("Register", use_container_width=True):
                _do_register(new_username, new_password, confirm_password)

st.sidebar.divider()
tab = st.sidebar.radio("Navigate", ["Upload Purchases", "Analyze Purchases"])
st.sidebar.divider()
st.sidebar.caption(f"API: `{API_URL}`")


# ── Tab 1: Upload ──────────────────────────────────────────────────────────────
if tab == "Upload Purchases":
    st.title("Upload Purchases")

    if not st.session_state.get("token"):
        st.warning("Please sign in using the sidebar to upload purchases.")
        st.stop()

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
                elif response.status_code == 401:
                    st.error("Session expired — please sign in again.")
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
                elif response.status_code == 401:
                    st.error("Session expired — please sign in again.")
                else:
                    st.error(f"Upload failed: {response.text}")


# ── Tab 2: Analyse ─────────────────────────────────────────────────────────────
elif tab == "Analyze Purchases":
    st.title("Analyze Purchases")

    display_currency = st.selectbox(
        "Display currency",
        CURRENCIES,
        help="All amounts are converted to this currency for display. Rates are illustrative, not live.",
    )

    with st.expander("Filters", expanded=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            country_filter = st.text_input("Country")
        with col2:
            start_date = st.date_input("From", value=None)
        with col3:
            end_date = st.date_input("To", value=None)
        with col4:
            page_size = st.selectbox("Rows per page", [100, 250, 500, 1000], index=1)

    if "page_offset" not in st.session_state:
        st.session_state.page_offset = 0

    params = {"limit": page_size, "offset": st.session_state.page_offset}
    if country_filter:
        params["country"] = country_filter
    if start_date:
        params["start_date"] = str(start_date)
    if end_date:
        params["end_date"] = str(end_date)

    filter_key = (country_filter, str(start_date), str(end_date), page_size)
    if st.session_state.get("_last_filter") != filter_key:
        st.session_state.page_offset = 0
        st.session_state["_last_filter"] = filter_key

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

    df["amount_display"] = df.apply(
        lambda r: convert(to_usd(r["amount"], r["currency"]), display_currency), axis=1
    )

    sym = display_currency

    current_page = st.session_state.page_offset // page_size + 1
    st.caption(
        f"Showing {st.session_state.page_offset + 1}–{st.session_state.page_offset + len(df):,} "
        f"(page {current_page}) — amounts in {display_currency}"
    )
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"{sym} {df['amount_display'].sum():,.2f}")
    m2.metric("Total Purchases", f"{len(df):,}")
    m3.metric("Avg Order Value", f"{sym} {df['amount_display'].mean():,.2f}")
    m4.metric("Unique Customers", f"{df['customer_name'].nunique():,}")

    prev_col, _, next_col = st.columns([1, 8, 1])
    with prev_col:
        if st.button("← Prev", disabled=st.session_state.page_offset == 0):
            st.session_state.page_offset = max(0, st.session_state.page_offset - page_size)
            st.rerun()
    with next_col:
        if st.button("Next →", disabled=len(df) < page_size):
            st.session_state.page_offset += page_size
            st.rerun()

    st.divider()

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.subheader(f"Revenue by Country ({display_currency})")
        country_revenue = (
            df.groupby("country")["amount_display"]
            .sum()
            .sort_values(ascending=False)
            .reset_index()
            .rename(columns={"country": "Country", "amount_display": f"Revenue ({display_currency})"})
        )
        fig = px.bar(
            country_revenue,
            x="Country",
            y=f"Revenue ({display_currency})",
            color="Country",
            color_discrete_sequence=px.colors.qualitative.Safe,
        )
        fig.update_layout(showlegend=False, xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    with chart_col2:
        st.subheader(f"Revenue Over Time ({display_currency})")
        daily_revenue = (
            df.groupby("purchase_date")["amount_display"]
            .sum()
            .reset_index()
            .rename(columns={"purchase_date": "Date", "amount_display": f"Revenue ({display_currency})"})
        )
        fig = px.area(
            daily_revenue,
            x="Date",
            y=f"Revenue ({display_currency})",
            color_discrete_sequence=["#2563eb"],
        )
        fig.update_layout(xaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    st.subheader(f"Top 10 Customers ({display_currency})")
    top_customers = (
        df.groupby("customer_name")["amount_display"]
        .sum()
        .nlargest(10)
        .sort_values()
        .reset_index()
        .rename(columns={"customer_name": "Customer", "amount_display": f"Total Spend ({display_currency})"})
    )
    fig = px.bar(
        top_customers,
        x=f"Total Spend ({display_currency})",
        y="Customer",
        orientation="h",
        color=f"Total Spend ({display_currency})",
        color_continuous_scale="Blues",
    )
    fig.update_layout(coloraxis_showscale=False, yaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    with st.expander("Raw Data Table"):
        display_df = df[["id", "customer_name", "country", "purchase_date", "amount", "currency", "amount_display"]].copy()
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

        if st.session_state.get("token"):
            st.divider()
            st.subheader("Delete a Purchase")
            valid_ids = df["id"].tolist()
            del_id = st.number_input(
                "Purchase ID to delete",
                min_value=1,
                step=1,
                help="Enter the ID from the table above.",
            )
            if st.button("Delete Purchase", type="primary"):
                if int(del_id) not in valid_ids:
                    st.warning(f"ID {int(del_id)} is not in the current page — check the ID and filters.")
                else:
                    try:
                        del_resp = requests.delete(
                            f"{API_URL}/purchase/{int(del_id)}",
                            headers=_auth_header(),
                            timeout=10,
                        )
                    except requests.exceptions.ConnectionError:
                        st.error("Cannot reach the API.")
                    else:
                        if del_resp.status_code == 200:
                            st.success(del_resp.json()["message"])
                            st.rerun()
                        elif del_resp.status_code == 404:
                            st.error("Purchase not found.")
                        elif del_resp.status_code == 401:
                            st.error("Session expired — please sign in again.")
                        else:
                            st.error(f"Delete failed: {del_resp.text}")

    st.subheader("KPIs & Sales Forecast")
    forecast_days = st.number_input("Forecast horizon (days):", min_value=1, max_value=30, value=5)

    if st.button("Compute KPIs", type="primary"):
        with st.spinner("Computing..."):
            kpi_resp = api_get("/purchases/kpis", params={"forecast_days": forecast_days})

        if kpi_resp.status_code == 400:
            st.warning(kpi_resp.json().get("detail", "Could not compute KPIs."))
            st.stop()
        elif kpi_resp.status_code != 200:
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
                fig = px.bar(
                    df_countries,
                    x="Country",
                    y="Clients",
                    color="Clients",
                    color_continuous_scale="Blues",
                )
                fig.update_layout(coloraxis_showscale=False, xaxis_title=None)
                st.plotly_chart(fig, use_container_width=True)

        if kpi.get("sales_forecast") and kpi["sales_forecast"] != "Not requested":
            st.subheader(f"Sales Forecast — Next {forecast_days} Days")
            df_forecast = pd.DataFrame(
                kpi["sales_forecast"].items(), columns=["Day", "Projected Revenue ($)"]
            )
            fig = px.line(
                df_forecast,
                x="Day",
                y="Projected Revenue ($)",
                markers=True,
                color_discrete_sequence=["#2563eb"],
            )
            fig.update_traces(line=dict(dash="dot", width=2))
            fig.update_layout(xaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(
                df_forecast.style.format({"Projected Revenue ($)": "${:,.2f}"}),
                use_container_width=True,
            )
