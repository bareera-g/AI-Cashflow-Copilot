"""
app.py

Streamlit entrypoint for the AI Cashflow Copilot (SMB).

This app allows a user to:
1. Upload a bank transactions CSV.
2. Clean and standardize the data.
3. Categorize transactions into spending buckets.
4. Detect recurring expenses (e.g. rent, payroll, subscriptions).
5. Forecast future cash balance (MVP: basic forecast).
6. Generate human-readable insights.

Note:
- This version uses the function names currently implemented in your src/ files:
  categorize_transactions, find_recurring_transactions, forecast_cashflow, generate_insights.
"""

import streamlit as st

from src.io_utils import load_transactions, add_balance
from src.categorize import categorize_transactions
from src.recurring import find_recurring_transactions
from src.forecast import forecast_cashflow
from src.insights import generate_insights

st.set_page_config(page_title="AI Cashflow Copilot", layout="wide")
st.title("AI Cashflow Copilot (SMB)")

# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.header("Inputs")
starting_balance = st.sidebar.number_input("Starting balance ($)", value=25000.0, step=1000.0)

# If your current forecast_cashflow() doesn’t support these yet, keep them in UI for later,
# but don’t pass them into the function unless you update the function signature.
horizon = st.sidebar.slider("Forecast horizon (days)", min_value=30, max_value=90, value=60, step=10)

# -----------------------------
# Upload CSV
# -----------------------------
uploaded = st.file_uploader("Upload bank transactions CSV", type=["csv"])
st.caption("CSV must include: date, description, amount (expenses negative, income positive).")

if uploaded is None:
    st.info("Upload a CSV to begin. Tip: use data/sample_transactions.csv as a starter.")
    st.stop()

# -----------------------------
# Load + clean
# -----------------------------
try:
    df = load_transactions(uploaded)
except Exception as e:
    st.error(f"Could not read CSV: {e}")
    st.stop()

# -----------------------------
# Categorize + enrich
# -----------------------------
df = categorize_transactions(df)

# Add running balance column for display
df_bal = add_balance(df, starting_balance)

# -----------------------------
# Display: transactions + stats
# -----------------------------
col1, col2 = st.columns([1.4, 1.0])

with col1:
    st.subheader("Transactions (cleaned)")
    st.dataframe(df_bal, use_container_width=True, height=280)

with col2:
    st.subheader("Quick stats")
    total_income = df[df["amount"] > 0]["amount"].sum()
    total_exp = df[df["amount"] < 0]["amount"].sum()
    st.metric("Total income", f"${total_income:,.2f}")
    st.metric("Total expenses", f"${total_exp:,.2f}")
    st.metric("Net", f"${(total_income + total_exp):,.2f}")

st.divider()

# -----------------------------
# Spend by category + merchants (only works if categorize_transactions adds category/merchant)
# -----------------------------
c1, c2 = st.columns([1.0, 1.0])

with c1:
    st.subheader("Spend by category")
    if "category" in df.columns:
        by_cat = df.groupby("category")["amount"].sum().sort_values()
        chart = (-by_cat[by_cat < 0]).sort_values(ascending=False)
        st.bar_chart(chart)
    else:
        st.warning("No 'category' column found. Make sure categorize_transactions() adds a category column.")

with c2:
    st.subheader("Top merchants (expenses)")
    if "merchant" in df.columns:
        exp = df[df["amount"] < 0].copy()
        by_merch = exp.groupby("merchant")["amount"].sum().sort_values().head(10)
        st.dataframe(
            by_merch.reset_index().rename(columns={"amount": "total_amount"}),
            use_container_width=True,
            height=260,
        )
    else:
        st.warning("No 'merchant' column found. Make sure categorize_transactions() adds a merchant column.")

st.divider()

# -----------------------------
# Recurring detection
# -----------------------------
st.subheader("Recurring bills")

recurring_df = find_recurring_transactions(df)

if recurring_df is None or getattr(recurring_df, "empty", True):
    st.write("No recurring transactions detected yet (try more data / longer time range).")
else:
    # Split income vs expenses using avg_amount sign
    recurring_income = recurring_df[recurring_df["avg_amount"] > 0].copy()
    recurring_expenses = recurring_df[recurring_df["avg_amount"] < 0].copy()

    c1, c2 = st.columns(2)

    with c1:
        st.markdown("### Recurring Expenses")
        if recurring_expenses.empty:
            st.write("None detected.")
        else:
            st.dataframe(recurring_expenses, use_container_width=True)

    with c2:
        st.markdown("### Recurring Income")
        if recurring_income.empty:
            st.write("None detected.")
        else:
            st.dataframe(recurring_income, use_container_width=True)


# -----------------------------
# Forecast + insights
# -----------------------------
st.subheader("Forecast + insights")

forecast_dict = forecast_cashflow(df)  # keep signature as-is for now
insights = generate_insights(df, recurring_df, forecast_dict)

# Display forecast outputs in a friendly way
with st.expander("Forecast (raw)"):
    st.json(forecast_dict if forecast_dict is not None else {})

st.subheader("AI Cashflow Copilot Insights")
if insights:
    for i in insights:
        st.markdown(f"- {i}")
else:
    st.write("No insights generated.")
