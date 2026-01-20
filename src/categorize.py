import re
import pandas as pd

CATEGORY_RULES = [
    (r"\brent\b", "Rent"),
    (r"\bpayroll\b|\bgusto\b", "Payroll"),
    (r"\bstripe\b|\bsquare\b|\bprocessing fee\b", "Payment Processing"),
    (r"\bgoogle ads\b|\bmeta ads\b|\bfacebook ads\b", "Marketing"),
    (r"\baws\b|\bamazon web services\b|\bcloud\b", "Cloud/Hosting"),
    (r"\bcomcast\b|\binternet\b|\bphone\b", "Utilities"),
    (r"\badobe\b|\bo365\b|\bmicrosoft\b|\bsoftware\b", "Software Subscriptions"),
    (r"\buber\b|\blyft\b|\btaxi\b", "Travel"),
    (r"\boffice depot\b|\bstaples\b|\bsuppl(y|ies)\b", "Office Supplies"),
    (r"\bbank fee\b|\bservice fee\b|\bcharge\b", "Bank Fees"),
    (r"\binvoice\b|\bpayment\b|\bach\b|\bdeposit\b", "Revenue/Payments"),
]

def _normalize_merchant(desc: str) -> str:
    """
    Convert a raw description into a rough merchant key.
    This helps group together transactions from the same vendor.
    """
    s = str(desc).lower()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return " ".join(s.split()[:4])  # first 4 tokens

def categorize_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds:
      - merchant: normalized description key
      - category: rule-based category label
    """
    out = df.copy()
    out["merchant"] = out["description"].map(_normalize_merchant)
    out["category"] = "Other"

    desc_lower = out["description"].str.lower()

    for pattern, cat in CATEGORY_RULES:
        mask = desc_lower.str.contains(pattern, regex=True, na=False)
        out.loc[mask, "category"] = cat

    return out
