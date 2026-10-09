"""Session 2: an interactive dashboard over the cleaned PaySim sample.

Run with: streamlit run app.py
"""
import pandas as pd
import streamlit as st

CLEANED_PATH = "data/cleaned.csv"
QUARANTINED_PATH = "data/quarantined.csv"

st.set_page_config(page_title="Mobile Money Transactions", layout="wide")


@st.cache_data
def load_data():
    """Cached so Streamlit only re-reads the CSVs when the files actually
    change, not on every filter click.
    """
    cleaned = pd.read_csv(CLEANED_PATH)
    quarantined = pd.read_csv(QUARANTINED_PATH)
    return cleaned, quarantined


cleaned, quarantined = load_data()

st.title("Mobile Money Transactions")
st.caption(
    "PaySim sample, cleaned via scripts/clean.py. Amounts are unitless "
    "(synthetic data), not a real currency."
)

# --- Sidebar filters ------------------------------------------------------

st.sidebar.header("Filters")

selected_types = st.sidebar.multiselect(
    "Transaction type",
    options=sorted(cleaned["type"].unique()),
    default=sorted(cleaned["type"].unique()),
)

min_amount, max_amount = float(cleaned["amount"].min()), float(cleaned["amount"].max())
amount_range = st.sidebar.slider(
    "Amount range",
    min_value=min_amount,
    max_value=max_amount,
    value=(min_amount, max_amount),
)

fraud_filter = st.sidebar.radio(
    "Fraud status",
    options=["All", "Fraud only", "Non-fraud only"],
    index=0,
)

filtered = cleaned[
    cleaned["type"].isin(selected_types)
    & cleaned["amount"].between(*amount_range)
]
if fraud_filter == "Fraud only":
    filtered = filtered[filtered["isFraud"] == 1]
elif fraud_filter == "Non-fraud only":
    filtered = filtered[filtered["isFraud"] == 0]

# --- KPI row ---------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)
col1.metric("Transactions (filtered)", f"{len(filtered):,}")
col2.metric("Total amount", f"{filtered['amount'].sum():,.0f}")
col3.metric("Fraud count", f"{int((filtered['isFraud'] == 1).sum()):,}")
fraud_rate = filtered["isFraud"].mean() if len(filtered) else 0.0
col4.metric("Fraud rate (this filter)", f"{fraud_rate:.2%}")

st.divider()

# --- Chart: transaction count by type, split by fraud status --------------

st.subheader("Transaction count by type")
chart_data = (
    filtered.assign(status=filtered["isFraud"].map({0: "Non-fraud", 1: "Fraud"}))
    .groupby(["type", "status"])
    .size()
    .unstack(fill_value=0)
)
st.bar_chart(chart_data)

# --- Summary table -----------------------------------------------------

st.subheader("Summary by transaction type")
summary = filtered.groupby("type").agg(
    count=("amount", "size"),
    total_amount=("amount", "sum"),
    median_amount=("amount", "median"),
    fraud_count=("isFraud", "sum"),
)
summary["fraud_rate"] = (summary["fraud_count"] / summary["count"]).map("{:.2%}".format)
st.dataframe(summary, use_container_width=True)

# --- Data quality transparency ------------------------------------------

with st.expander(f"Data quality: {len(quarantined):,} rows were quarantined, not silently dropped"):
    st.write(
        "These rows failed at least one validation rule in scripts/clean.py "
        "and are excluded from everything above, but they're not hidden - "
        "here's why each one was excluded:"
    )
    reason_counts = (
        quarantined["failed_rules"]
        .str.split(", ")
        .explode()
        .value_counts()
        .rename("row_count")
    )
    st.dataframe(reason_counts)