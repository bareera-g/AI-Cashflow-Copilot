"""
app.py

Streamlit entrypoint for the AI Cashflow Copilot (SMB).

This app:
1) Uploads a bank transactions CSV
2) Cleans + standardizes data
3) Categorizes transactions (rule-based)
4) Detects recurring transactions
5) Forecasts future cash balance
6) Shows risk metrics + drivers + insights
7) Supports simple what-if scenarios (delay rent, reduce ads, accelerate invoice)
"""

import streamlit as st
import pandas as pd

from src.io_utils import load_transactions, add_balance
from src.categorize import categorize_transactions
from src.recurring import find_recurring_transactions
from src.forecast import forecast_cashflow
from src.insights import generate_insights


# -----------------------------
# Page config
# -----------------------------
st.set_page_config(page_title="AI Cashflow Copilot", layout="wide")
st.title("AI Cashflow Copilot (SMB)")


# -----------------------------
# Sidebar inputs
# -----------------------------
st.sidebar.header("Inputs")

starting_balance = st.sidebar.number_input(
    "Starting balance ($)",
    value=25000.0,
    step=1000.0,
)

horizon = st.sidebar.slider(
    "Forecast horizon (days)",
    min_value=30,
    max_value=90,
    value=60,
    step=10,
)

# What-if scenarios must be defined BEFORE we use them
st.sidebar.subheader("What-if scenarios")

delay_rent_days = st.sidebar.slider("Delay RENT by (days)", 0, 30, 0, 1)
reduce_ads_pct = st.sidebar.slider("Reduce GOOGLE ADS by (%)", 0, 80, 0, 5)
invoice_earlier_days = st.sidebar.slider("ACME invoice paid earlier by (days)", 0, 14, 0, 1)


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

# Add running balance column for display and canonical current balance
df_bal = add_balance(df, starting_balance)
current_balance = float(df_bal["balance"].iloc[-1])


# -----------------------------
# Transactions + quick stats
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
# Spend breakdowns
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
    recurring_income = recurring_df[recurring_df["avg_amount"] > 0].copy()
    recurring_expenses = recurring_df[recurring_df["avg_amount"] < 0].copy()

    rc1, rc2 = st.columns(2)
    with rc1:
        st.markdown("### Recurring Expenses")
        if recurring_expenses.empty:
            st.write("None detected.")
        else:
            st.dataframe(recurring_expenses, use_container_width=True)

    with rc2:
        st.markdown("### Recurring Income")
        if recurring_income.empty:
            st.write("None detected.")
        else:
            st.dataframe(recurring_income, use_container_width=True)

st.divider()


# -----------------------------
# Apply what-if scenarios
# -----------------------------
def apply_scenarios(recurring_df: pd.DataFrame, reduce_ads_pct: int) -> pd.DataFrame:
    """
    Return a modified copy of recurring_df based on scenario controls.

    Currently modifies:
      - GOOGLE ADS avg_amount (reduced by reduce_ads_pct)
    """
    if recurring_df is None or recurring_df.empty:
        return recurring_df

    out = recurring_df.copy()

    # Reduce Google Ads spend
    if reduce_ads_pct > 0:
        mask = out["description"].str.contains("GOOGLE ADS", case=False, na=False)
        out.loc[mask, "avg_amount"] = out.loc[mask, "avg_amount"] * (1 - reduce_ads_pct / 100.0)

    return out


scenario_recurring_df = apply_scenarios(recurring_df, reduce_ads_pct)


# -----------------------------
# Forecast + insights
# -----------------------------
st.subheader("Forecast + insights")

# NOTE: This requires forecast_cashflow in src/forecast.py to accept delay_rent_days and invoice_earlier_days.
forecast_dict = forecast_cashflow(
    df,
    starting_balance=current_balance,  # forecast starts from current balance
    horizon_days=horizon,
    ma_window=14,
    recurring_df=scenario_recurring_df,  # scenario-adjusted recurring
    delay_rent_days=delay_rent_days,
    invoice_earlier_days=invoice_earlier_days,
)

forecast_df = forecast_dict["forecast_df"]
metrics = forecast_dict["metrics"]

# Risk banner
if metrics.get("days_to_negative") is not None and metrics["days_to_negative"] <= horizon:
    st.warning(
        f"⚠️ Cash risk: projected to go negative in {metrics['days_to_negative']} days. "
        f"Lowest projected balance: ${metrics['min_balance']:,.2f}"
    )
else:
    st.success("✅ No negative balance projected in the forecast horizon.")

# Key metrics
m1, m2, m3 = st.columns(3)
with m1:
    st.metric("Current balance", f"${forecast_dict['current_balance']:,.2f}")
with m2:
    st.metric("Lowest projected balance", f"${metrics['min_balance']:,.2f}")
with m3:
    st.metric(
        "Days until negative",
        str(metrics["days_to_negative"]) if metrics.get("days_to_negative") is not None else "Not projected",
    )

# Balance chart
if forecast_df is not None and not forecast_df.empty:
    st.line_chart(forecast_df.set_index("date")["predicted_balance"])

# Forecast drivers (use scenario table so it matches)
if scenario_recurring_df is not None and not scenario_recurring_df.empty:
    top_exp = scenario_recurring_df[scenario_recurring_df["avg_amount"] < 0].sort_values("avg_amount").head(3)
    top_inc = scenario_recurring_df[scenario_recurring_df["avg_amount"] > 0].sort_values("avg_amount", ascending=False).head(3)

    st.markdown("### Forecast drivers (recurring)")
    d1, d2 = st.columns(2)

    with d1:
        st.markdown("**Top recurring expenses**")
        if top_exp.empty:
            st.write("None")
        else:
            for _, r in top_exp.iterrows():
                st.write(
                    f"- {r['description']}: ${r['avg_amount']:,.2f} "
                    f"({r.get('frequency','')}, {r.get('confidence','')})"
                )

    with d2:
        st.markdown("**Top recurring income**")
        if top_inc.empty:
            st.write("None")
        else:
            for _, r in top_inc.iterrows():
                st.write(
                    f"- {r['description']}: ${r['avg_amount']:,.2f} "
                    f"({r.get('frequency','')}, {r.get('confidence','')})"
                )

# Insights (use scenario recurring so narrative matches)
insights = generate_insights(df, scenario_recurring_df, forecast_dict)

st.subheader("AI Cashflow Copilot Insights")
if insights:
    for i in insights:
        st.markdown(f"- {i}")
else:
    st.write("No insights generated.")

# Raw output (once)
with st.expander("Forecast (raw)"):
    raw = dict(forecast_dict)
    if forecast_df is not None and not forecast_df.empty:
        raw["forecast_df"] = forecast_df.assign(date=forecast_df["date"].astype(str)).to_dict(orient="records")
    st.json(raw)
