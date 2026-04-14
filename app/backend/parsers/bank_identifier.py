"""Identify the issuing bank from extracted PDF text."""
import re

BANK_KEYWORDS: dict[str, list[str]] = {
    "ABSA": ["absa", "absa bank"],
    "FNB": ["first national bank", "fnb", "firstrand"],
    "Nedbank": ["nedbank"],
    "Standard Bank": ["standard bank", "standardbank"],
    "Capitec": ["capitec"],
}


def identify_bank(text: str) -> str:
    """Return the bank name or 'Unknown' if not detected."""
    lower = text.lower()
    for bank, keywords in BANK_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                return bank
    return "Unknown"
