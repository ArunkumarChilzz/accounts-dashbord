import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

st.set_page_config(page_title="SLA Executive Dashboard", layout="wide")

# ---------------------------------------------------
# GOOGLE SHEETS CONNECTION
# ---------------------------------------------------

@st.cache_resource
def connect():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )
    return gspread.authorize(creds)


@st.cache_data(ttl=300)
def load_data():
    client = connect()
    sheet = client.open("Non compliance 2025_Jan to 2026_Jan").sheet1
    data = sheet.get_all_records()
    return pd.DataFrame(data)


df = load_data()

# ---------------------------------------------------
# BASIC CLEANING
# ---------------------------------------------------

df.columns = df.columns.str.strip()

required_cols = ["MM-YYYY", "RCA", "Final Status-4BD"]

for col in required_cols:
    if col not in df.columns:
        st.error(f"Column '{col}' not found in sheet.")
        st.stop()

# Convert Month to datetime
df["Month_Date"] = pd.to_datetime(df["MM-YYYY"], errors="coerce")
df = df.dropna(subset=["Month_Date"])

# Filter only Not Met
df_notmet = df[df["Final Status-4BD"].str.strip().str.lower() == "not met"]

# ---------------------------------------------------
# SIDEBAR FILTERS
# ---------------------------------------------------

st.sidebar.title("Filters")

months = sorted(df_notmet["MM-YYYY"].dropna().unique())
selected_months = st.sidebar.multiselect(
    "Select Month", months, default=months
)

rcas = sorted(df_notmet["RCA"].dropna().unique())
selected_rca = st.sidebar.multiselect(
    "Select RCA", rcas, default=rcas
)

filtered_df = df_notmet[
    (df_notmet["MM-YYYY"].isin(selected_months)) &
    (df_notmet["RCA"].isin(selected_rca))
]

# ---------------------------------------------------
# DASHBOARD TITLE
# ---------------------------------------------------

st.title("🚦 SLA Not Met Executive Dashboard")

total = len(filtered_df)

# ---------------------------------------------------
# KPI SECTION
# ---------------------------------------------------

if not filtered_df.empty:

    monthly_counts = (
        df_notmet.groupby("Month_Date")
        .size()
        .sort_index()
    )

    latest_month = monthly_counts.index.max()
    latest_value = monthly_counts.loc[latest_month]

    top_rca = filtered_df["RCA"].value_counts()

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Not Met", f"{total:,}")
    col2.metric(
        "Latest Month",
        latest_month.strftime("%b-%Y"),
        f"{latest_value:,}"
    )
    col3.metric(
        "Top RCA",
        top_rca.index[0] if not top_rca.empty else "N/A"
    )

else:
    st.warning("No data available.")

st.markdown("---")

# ---------------------------------------------------
# MONTHLY TREND
# ---------------------------------------------------

monthly_trend = (
    filtered_df.groupby("MM-YYYY")
    .size()
    .reset_index(name="Count")
)

fig_line = px.line(
    monthly_trend,
    x="MM-YYYY",
    y="Count",
    markers=True,
    title="📈 Monthly Trend"
)

st.plotly_chart(fig_line, use_container_width=True)

# ---------------------------------------------------
# STACKED BAR
# ---------------------------------------------------

stacked = (
    filtered_df.groupby(["MM-YYYY", "RCA"])
    .size()
    .reset_index(name="Count")
)

fig_stack = px.bar(
    stacked,
    x="MM-YYYY",
    y="Count",
    color="RCA",
    title="📊 Month vs RCA Distribution"
)

st.plotly_chart(fig_stack, use_container_width=True)

# ---------------------------------------------------
# RCA CONTRIBUTION
# ---------------------------------------------------

rca_summary = (
    filtered_df["RCA"]
    .value_counts()
    .reset_index()
)

rca_summary.columns = ["RCA", "Count"]

fig_bar = px.bar(
    rca_summary,
    x="Count",
    y="RCA",
    orientation="h",
    title="📌 RCA Contribution"
)

st.plotly_chart(fig_bar, use_container_width=True)

# ---------------------------------------------------
# PIE CHART
# ---------------------------------------------------

fig_pie = px.pie(
    rca_summary,
    names="RCA",
    values="Count",
    title="🥧 RCA Share %"
)

st.plotly_chart(fig_pie, use_container_width=True)

# ---------------------------------------------------
# HEATMAP
# ---------------------------------------------------

if "statementId" in filtered_df.columns:

    heatmap_data = pd.pivot_table(
        filtered_df,
        values="statementId",
        index="RCA",
        columns="MM-YYYY",
        aggfunc="count",
        fill_value=0
    )

    fig_heat = px.imshow(
        heatmap_data,
        aspect="auto",
        title="🔥 RCA vs Month Heatmap"
    )

    st.plotly_chart(fig_heat, use_container_width=True)
