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


def generate_insights(
    df: pd.DataFrame,
    recurring_df: pd.DataFrame,
    forecast: dict
) -> list[str]:
    """
    Create a list of human-readable insights from the analysis results.

    Insights generated:
        1) Largest spending category (based on total negative amounts).
        2) Count of recurring transactions detected.
        3) Average monthly cashflow forecast.

    Args:
        df: Transaction DataFrame containing at least:
            - amount (numeric)
            - category (string)
        recurring_df: DataFrame of recurring candidates containing:
            - description, amount, count
        forecast: Dictionary from forecast_cashflow containing:
            - average_monthly_cashflow

    Returns:
        A list of strings, each string being one insight.
    """
    insights = []

    expenses = df[(df["amount"] < 0) & (df["category"] != "Income")]

    if not expenses.empty:
        spending_by_category = expenses.groupby("category")["amount"].sum()
        top_spend_category = spending_by_category.idxmin()  # most negative = biggest spend
        insights.append(f"Your biggest spending category is {top_spend_category}.")
    else:
        insights.append("No expenses detected in the dataset.")


    # Recurring transaction insight:
    # If recurring_df has rows, that means we found repeating transactions.
    if recurring_df is not None and not recurring_df.empty:
        insights.append(
            f"You have {len(recurring_df)} recurring transactions worth reviewing."
        )
    else:
        insights.append("No clear recurring transactions detected.")

    # Forecast insight: pull out the average monthly cashflow.
    avg_cashflow = forecast.get("average_monthly_cashflow")

    # Only add the forecast insight if the value is present.
    if avg_cashflow is not None:
        insights.append(f"Your average monthly cashflow is ${avg_cashflow}.")
    else:
        insights.append("Could not compute a monthly cashflow forecast.")

    return insights
