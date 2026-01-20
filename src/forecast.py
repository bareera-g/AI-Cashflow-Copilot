"""
forecast.py

Cashflow forecasting.

For MVP:
- We compute monthly cashflow (sum of amounts per month).
- Then compute the average monthly cashflow.

This is intentionally simple and explainable.
Later you can upgrade to:
- moving averages
- ARIMA / Prophet
- ML regression
- LLM-based “what-if” scenario forecasts
"""

import pandas as pd


def forecast_cashflow(df: pd.DataFrame) -> dict:
    """
    Forecast cashflow using a simple average monthly net value.

    Steps:
        1) Create a "month" column from the "date" column.
        2) Group by month and sum amounts.
        3) Take the average of monthly totals.

    Assumptions:
        - df has columns: "date" (datetime) and "amount" (numeric)

    Args:
        df: pandas DataFrame of transactions.

    Returns:
        dict with:
            - average_monthly_cashflow (float rounded to 2 decimals)
            - monthly_cashflow_series (pandas Series, optional debugging use)
    """
    # Copy the DataFrame so we don't accidentally modify the original.
    monthly = df.copy()

    # Convert each date to a monthly period (e.g., 2026-01).
    # This allows us to group all transactions from the same month together.
    monthly["month"] = monthly["date"].dt.to_period("M")

    # Group by month and sum amounts:
    # - Positive amounts increase cash
    # - Negative amounts decrease cash
    cashflow_by_month = monthly.groupby("month")["amount"].sum()

    # Compute the average monthly cashflow (mean).
    avg_monthly_cashflow = cashflow_by_month.mean()

    # Return results in a dictionary.
    return {
        "average_monthly_cashflow": round(float(avg_monthly_cashflow), 2),
        "monthly_cashflow_series": cashflow_by_month,
    }
