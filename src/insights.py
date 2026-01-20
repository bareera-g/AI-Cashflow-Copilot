"""
insights.py

Generate human-readable insights.

This module takes:
- categorized transactions
- recurring candidates
- forecast results

…and turns them into short insights a user can understand quickly.

This is a great “copilot” layer because it bridges:
raw data -> useful advice
"""

import pandas as pd


import pandas as pd

def generate_insights(df: pd.DataFrame, recurring_df: pd.DataFrame, forecast_dict: dict) -> list[str]:
    """
    Generate human-readable insights grounded in computed stats.

    Expects forecast_dict to contain:
      - current_balance (float)
      - metrics: {min_balance, days_to_negative}
    """
    insights = []

    # Biggest spending category (expenses)
    if "category" in df.columns:
        exp = df[df["amount"] < 0].copy()
        if not exp.empty:
            by_cat = exp.groupby("category")["amount"].sum().sort_values()  # most negative first
            biggest_cat = by_cat.index[0]
            insights.append(f"Your biggest spending category is {biggest_cat}.")

    # Recurring count
    if recurring_df is not None and not getattr(recurring_df, "empty", True):
        insights.append(f"You have {len(recurring_df)} recurring transactions worth reviewing.")
    else:
        insights.append("No recurring transactions detected yet.")

    # Forecast risk insight (NEW)
    metrics = (forecast_dict or {}).get("metrics", {})
    days_to_neg = metrics.get("days_to_negative", None)
    min_bal = metrics.get("min_balance", None)
    cur_bal = (forecast_dict or {}).get("current_balance", None)

    if cur_bal is not None:
        insights.append(f"Current estimated cash balance is ${cur_bal:,.2f}.")

    if days_to_neg is not None and min_bal is not None:
        insights.append(f"Cash risk: projected to go negative in {days_to_neg} days (lowest projected balance ${min_bal:,.2f}).")
    elif min_bal is not None:
        insights.append(f"Lowest projected balance in the forecast horizon is ${min_bal:,.2f}.")

    return insights
