"""Enhanced expense categoriser with 15+ consumer-relevant categories.

Uses keyword matching with priority ordering.  Each transaction description
is matched against a list of keyword rules; the first match wins.
Users can override individual categories (handled at the API layer).
"""
from __future__ import annotations

CATEGORY_RULES: list[tuple[str, list[str]]] = [
    # Income / Credits
    ("Salary", ["salary", "payroll", "wages", "remuneration", "pay slip"]),
    ("Credits", [
        "acb credit", "immediate trf cr", "realtime credit", "rtc", "magtape credit",
        "payment from", "transfer in", "deposit", "cash deposit",
    ]),
    # Housing
    ("Rent & Utilities", [
        "rent", "lease", "body corporate", "hoa", "electricity", "eskom",
        "city power", "water", "rates ", "municipal", "nedbank home", "bond payment",
    ]),
    # Groceries
    ("Groceries", [
        "pick n pay", "pnp", "checkers", "woolworths food", "spar", "shoprite",
        "food lover", "makro", "game store", "costco", "grocery",
    ]),
    # Transport
    ("Transport", [
        "fuel", "petrol", "engen", "bp ", "shell ", "caltex", "sasol",
        "uber", "bolt ", "taxify", "mta", "traffic fine", "e-toll", "sanral",
        "parking", "car wash", "auto service",
    ]),
    # Insurance
    ("Insurance", [
        "insurance", "assurance", "discovery", "old mutual", "sanlam",
        "momentum", "auto & general", "santam", "nedgroup", "outsurance",
    ]),
    # Medical / Health
    ("Medical", [
        "medical", "pharmacy", "clicks", "dischem", "hospital", "doctor",
        "dentist", "optometrist", "medihelp", "bonitas", "bestmed",
    ]),
    # Entertainment / Dining
    ("Entertainment", [
        "restaurant", "kfc", "mcdonald", "steers", "nando", "spur",
        "wimpy", "ocean basket", "mugg & bean", "netflix", "showmax",
        "dstv", "spotify", "apple music", "youtube", "cinema", "ster-kinekor",
        "nu metro", "bar ", "pub ", "club ", "casino", "hollywoodbets",
        "betway", "playstation", "xbox",
    ]),
    # Clothing & Shopping
    ("Shopping", [
        "mr price", "mrp", "truworths", "edgars", "jet ", "pep ", "ackermans",
        "h&m", "zara", "cotton on", "relay", "foschini", "totalsports",
        "sportscene", "takealot", "amazon", "ebay", "shein",
    ]),
    # Cellular / Airtime
    ("Cellular Expenses", [
        "airtime", "prepaid airtime", "mtn", "vodacom", "cell c", "telkom",
        "rain ", "device payment", "top up",
    ]),
    # Bank Charges & Fees
    ("Bank Charges", [
        "service fee", "monthly fee", "account fee", "bank charge",
        "statement cost", "atm fee", "sms fee", "admin fee", "fixed monthly",
        "transaction fee", "cash handling",
    ]),
    # Payments & Transfers Out
    ("Payments", [
        "cashsend", "immediate trf", "digital payment", "eft payment",
        "internet pmt", "fnb app rtc pmt", "online transfer",
    ]),
    # ATM Cash
    ("Cash Deposits/Withdrawals", [
        "atm cash", "atm withdrawal", "cash withdrawal",
    ]),
    # Interest & Penalties
    ("Interest and Fees", [
        "interest charged", "interest on", "overdraft interest",
        "penalty", "late payment", "returned debit", "item paid no funds",
        "hybrid subscription", "insufficient funds",
    ]),
    # Unsuccessful Transactions
    ("Unsuccessful Transactions", ["unsuccessful", "declined", "reversal", "refund"]),
    # Education
    ("Education", [
        "school fees", "university", "college", "tuition", "educat",
        "unisa", "wits", "uct ", "uj ", "student loan",
    ]),
    # Savings & Investments
    ("Savings & Investments", [
        "savings", "investment", "unit trust", "retirement", "pension",
        "provident", "ra contribution", "tax free",
    ]),
]


def categorize(description: str) -> str:
    """Return the best matching category for a transaction description."""
    lower = description.lower()
    for category, keywords in CATEGORY_RULES:
        for kw in keywords:
            if kw in lower:
                return category
    return "Others"
