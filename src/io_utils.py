"""
io_utils.py

Input/Output utilities for the project.

Primary responsibility:
- Read transaction data from a CSV file and standardize it into a clean format
  that other modules can rely on.

We keep this in a separate file so:
- app.py stays clean
- any future changes to file formats only affect this module
"""

import pandas as pd


def load_transactions(path: str) -> pd.DataFrame:
    """
    Load a CSV of transactions into a cleaned pandas DataFrame.

    Expected CSV columns (case-insensitive):
        - date: date of transaction (e.g., "2025-01-12")
        - description: merchant or note (e.g., "Starbucks")
        - amount: numeric amount (negative for expense, positive for income)

    What this function does:
        1) Reads CSV into a DataFrame.
        2) Normalizes column names (lowercase + stripped).
        3) Parses the 'date' column into datetime objects (if present).

    Args:
        path: File path to the CSV file (e.g., "data/sample_transactions.csv").

    Returns:
        A pandas DataFrame with standardized column names and parsed dates.

    Raises:
        FileNotFoundError:
            If the CSV file path does not exist.
        pandas.errors.ParserError:
            If the CSV is malformed.
    """
    # Read the CSV file into a DataFrame.
    # This creates a table-like structure where each row is a transaction.
    df = pd.read_csv(path)

    # Normalize columns:
    # - lower() prevents mismatches like "Date" vs "date"
    # - strip() removes accidental spaces like "date " from CSV headers
    df.columns = [c.lower().strip() for c in df.columns]

    # If the CSV contains a 'date' column, convert it into datetime objects.
    # Datetime objects allow easy grouping by month, sorting by time, etc.
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # (Optional safety) You may want to ensure required columns exist.
    # For now we assume your CSV has the columns; we keep this minimal.

    # Return the cleaned DataFrame so other modules can use it.
    return df

def add_balance(df: pd.DataFrame, starting_balance: float) -> pd.DataFrame:
    """
    Add a running cash balance column based on transaction amounts.
    """
    df = df.copy()
    df["balance"] = starting_balance + df["amount"].cumsum()
    return df