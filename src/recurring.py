"""
recurring.py

Recurring transaction detection.

This module tries to identify transactions that happen repeatedly,
which is useful for spotting:
- subscriptions (Netflix, Spotify)
- rent
- monthly utilities

For the MVP:
- we define "recurring" as: same description + same amount appears at least N times
"""

import pandas as pd
import numpy as np

def _infer_frequency(dates: pd.Series, amounts: pd.Series) -> str:
    """
    Infer recurrence frequency using BOTH:
    - date spacing / month coverage
    - amount stability

    This handles cases like rent where billing date shifts (3rd vs 30th)
    but the amount is highly consistent.
    """
    ds = pd.to_datetime(dates).sort_values().dropna()
    amts = pd.to_numeric(amounts, errors="coerce").dropna()

    if len(ds) < 2:
        return "Irregular"

    unique_months = ds.dt.to_period("M").nunique()

    # Amount stability heuristic:
    # if amount barely changes and appears across multiple months → Monthly
    if len(amts) >= 2:
        amt_range = float(amts.max() - amts.min())
        amt_mean = float(amts.abs().mean()) if float(amts.abs().mean()) != 0 else 1.0
        stable_amount = (amt_range / amt_mean) <= 0.05  # <= 5% variation

        if unique_months >= 2 and stable_amount:
            return "Monthly"

    # Day-of-month consistency heuristic (looser, for “around the same time”)
    dom = ds.dt.day
    dom_med = float(dom.median())
    dom_close_ratio = float(((dom - dom_med).abs() <= 6).mean())  # within 6 days

    if unique_months >= 2 and dom_close_ratio >= 0.6:
        return "Monthly"

    # Fallback: gap-based
    gaps = ds.diff().dt.days.dropna()
    if gaps.empty:
        return "Irregular"

    median_gap = float(gaps.median())
    if 6 <= median_gap <= 8:
        return "Weekly"
    if 27 <= median_gap <= 33:
        return "Monthly"
    return "Irregular"



def _confidence_from_count(count: int) -> str:
    """
    Convert number of occurrences into a simple confidence label.
    """
    if count >= 5:
        return "High"
    if count >= 3:
        return "Medium"
    return "Low"


def find_recurring_transactions(df: pd.DataFrame, min_count: int = 3) -> pd.DataFrame:
    """
    Identify recurring transactions by grouping on description and summarizing:
      - count
      - avg/min/max amounts
      - inferred frequency (weekly/monthly/irregular)
      - confidence label based on count

    Assumes df contains columns: date, description, amount
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "description", "count", "avg_amount", "min_amount", "max_amount",
            "frequency", "confidence"
        ])

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date", "description", "amount"])

    # Group by exact description (your data uses consistent descriptions)
    grouped = d.groupby("description", as_index=False)

    summary = grouped.agg(
        count=("amount", "size"),
        avg_amount=("amount", "mean"),
        min_amount=("amount", "min"),
        max_amount=("amount", "max"),
    )

    # Filter to only items that repeat enough
    summary = summary[summary["count"] >= min_count].copy()

    if summary.empty:
        summary["frequency"] = []
        summary["confidence"] = []
        return summary

    # Add inferred frequency by looking at date gaps per description
    freq_map = {}
    for desc, g in d.groupby("description"):
        freq_map[desc] = _infer_frequency(g["date"], g["amount"])


    summary["frequency"] = summary["description"].map(freq_map).fillna("Irregular")
    summary["confidence"] = summary["count"].map(_confidence_from_count)

    # Round for display
    summary["avg_amount"] = summary["avg_amount"].round(2)
    summary["min_amount"] = summary["min_amount"].round(2)
    summary["max_amount"] = summary["max_amount"].round(2)

    # Sort: highest confidence first, then biggest magnitude recurring items
    conf_order = {"High": 0, "Medium": 1, "Low": 2}
    summary["_conf_rank"] = summary["confidence"].map(conf_order).fillna(3)
    summary["_abs_avg"] = summary["avg_amount"].abs()

    summary = summary.sort_values(["_conf_rank", "_abs_avg"], ascending=[True, False]).drop(columns=["_conf_rank", "_abs_avg"])

    return summary
