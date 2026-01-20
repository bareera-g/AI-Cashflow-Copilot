"""
src/forecast.py

Baseline cash-balance forecasting for the AI Cashflow Copilot.

Approach (explainable baseline):
1) Aggregate transactions into daily net cashflow.
2) Predict future daily net using a moving average of recent days.
3) Overlay recurring items by scheduling them into future dates.
4) Convert predicted net cashflow into a predicted balance trajectory.
"""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd


def _daily_net_flow(df: pd.DataFrame) -> pd.Series:
    """Return daily net cashflow series (sum of amounts per day), missing days filled with 0."""
    s = df.groupby(df["date"].dt.date)["amount"].sum()
    s.index = pd.to_datetime(s.index)
    return s.asfreq("D").fillna(0.0)


def _safe_dom_date(year: int, month: int, day: int) -> pd.Timestamp:
    """Clamp day-of-month to valid last day of month."""
    last_day = calendar.monthrange(year, month)[1]
    day = min(max(1, int(day)), last_day)
    return pd.Timestamp(year=year, month=month, day=day)


def _schedule_monthly_items(
    df: pd.DataFrame,
    recurring_df: pd.DataFrame,
    future_dates: pd.DatetimeIndex,
    delay_rent_days: int = 0,
    invoice_earlier_days: int = 0,
) -> pd.Series:
    """
    Build a series of monthly recurring adjustments across future_dates.

    Scenario knobs:
    - delay rent by N days (shifts rent expense forward)
    - invoice paid earlier by N days (shifts income earlier)
    """
    adj = pd.Series(0.0, index=future_dates)

    if recurring_df is None or getattr(recurring_df, "empty", True):
        return adj

    if "frequency" in recurring_df.columns:
        monthly = recurring_df[recurring_df["frequency"] == "Monthly"].copy()
    else:
        monthly = recurring_df.copy()

    if monthly.empty:
        return adj

    # Infer a schedule day-of-month (DOM) for each recurring description
    dom_map: Dict[str, int] = {}
    for desc in monthly["description"].unique():
        hist = df[df["description"] == desc]
        if hist.empty:
            continue
        dom_map[desc] = int(pd.to_datetime(hist["date"]).dt.day.median())

    start = future_dates.min()
    end = future_dates.max()
    months = pd.period_range(start=start, end=end, freq="M")

    for _, row in monthly.iterrows():
        desc = str(row["description"])
        amt = float(row.get("avg_amount", 0.0))
        dom = dom_map.get(desc, 1)

        for p in months:
            dt = _safe_dom_date(p.year, p.month, dom)

            # Apply scenario shifts
            if "RENT" in desc.upper() and delay_rent_days > 0:
                dt = dt + pd.Timedelta(days=delay_rent_days)

            if "INVOICE" in desc.upper() and invoice_earlier_days > 0:
                dt = dt - pd.Timedelta(days=invoice_earlier_days)

            if dt in adj.index:
                adj.loc[dt] += amt

    return adj



def forecast_cashflow(
    df: pd.DataFrame,
    starting_balance: float = 0.0,
    horizon_days: int = 60,
    ma_window: int = 14,
    recurring_df: Optional[pd.DataFrame] = None,
    delay_rent_days: int = 0,
    invoice_earlier_days: int = 0,
) -> Dict[str, Any]:
    """
    Forecast future cash balance.

    Returns a dict with:
      - current_balance
      - metrics: min_balance, days_to_negative
      - forecast_df: a DataFrame with columns [date, predicted_net, predicted_balance]
    """
    if df.empty:
        forecast_df = pd.DataFrame(columns=["date", "predicted_net", "predicted_balance"])
        return {"current_balance": starting_balance, "metrics": {"min_balance": None, "days_to_negative": None}, "forecast_df": forecast_df}

    # Ensure datetime
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])

    flow = _daily_net_flow(d)
    last_day = flow.index.max()

    # Future date index
    future_dates = pd.date_range(last_day + pd.Timedelta(days=1), periods=horizon_days, freq="D")

    # Baseline predicted net cashflow = moving average of recent daily net flow
    ma = flow.rolling(ma_window).mean()
    base = float(ma.iloc[-1]) if not np.isnan(ma.iloc[-1]) else float(flow.mean())
    predicted_net = pd.Series(base, index=future_dates)

    # Add recurring monthly adjustments on top of baseline
    recurring_adj = _schedule_monthly_items(
    d, recurring_df, future_dates,
    delay_rent_days=delay_rent_days,
    invoice_earlier_days=invoice_earlier_days,
)

    predicted_net = predicted_net + recurring_adj

    # Compute current balance and predicted balance trajectory
    current_balance = float(starting_balance)
    predicted_balance = current_balance + predicted_net.cumsum()

    forecast_df = pd.DataFrame({
        "date": future_dates,
        "predicted_net": predicted_net.values,
        "predicted_balance": predicted_balance.values,
    })

    # Risk metrics
    min_balance = float(forecast_df["predicted_balance"].min())
    neg = forecast_df[forecast_df["predicted_balance"] < 0]
    days_to_negative = int((neg["date"].iloc[0] - forecast_df["date"].iloc[0]).days) if not neg.empty else None

    return {
        "current_balance": round(current_balance, 2),
        "metrics": {
            "min_balance": round(min_balance, 2),
            "days_to_negative": days_to_negative,
        },
        "forecast_df": forecast_df,
    }
