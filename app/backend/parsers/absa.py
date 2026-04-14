"""ABSA bank statement parser.

Transaction line format:
    YYYY-MM-DD  <description>  [-]R1,234.56  [-]R9,876.54
"""
import re
import pandas as pd
from parsers.base import BaseParser

_PATTERN = re.compile(
    r"(\d{4}-\d{2}-\d{2})"          # date
    r"\s+(.+?)\s+"                   # description
    r"(-?R?\d+(?:,\d{3})*(?:\.\d{2})?)"  # amount
    r"\s+"
    r"(-?R?\d+(?:,\d{3})*(?:\.\d{2})?)"  # balance
)


def _clean_amount(s: str) -> float:
    return float(s.replace(",", "").replace("R", "").replace(" ", ""))


class AbsaParser(BaseParser):
    def parse(self, text: str) -> pd.DataFrame:
        rows = []
        for line in text.splitlines():
            m = _PATTERN.search(line)
            if m:
                date_str, desc, amt_str, bal_str = m.groups()
                try:
                    rows.append(
                        {
                            "Date": pd.to_datetime(date_str, format="%Y-%m-%d"),
                            "Description": desc.strip(),
                            "Amount": _clean_amount(amt_str),
                            "Balance": _clean_amount(bal_str),
                        }
                    )
                except ValueError:
                    continue
        return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])
