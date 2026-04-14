"""Standard Bank statement parser.

Transaction line format:
    DD MMM YY  <description>  -1,234.56  9,876.54
e.g. "15 Jan 24  Groceries pick n pay  -1500.00  8376.54"
"""
import re
import pandas as pd
from parsers.base import BaseParser

_PATTERN = re.compile(
    r"(\d{2}\s+\w{3}\s+\d{2})"                          # date DD MMM YY
    r"\s+(.+?)\s+"
    r"(-?\d+(?:,\d{3})*(?:\.\d{2})?)"                   # amount
    r"\s+"
    r"(-?\d+(?:,\d{3})*(?:\.\d{2})?)"                   # balance
)


def _clean(s: str) -> float:
    return float(s.replace(",", ""))


class StandardBankParser(BaseParser):
    def parse(self, text: str) -> pd.DataFrame:
        rows: list[dict] = []
        for line in text.splitlines():
            m = _PATTERN.search(line)
            if m:
                date_str, desc, amt_str, bal_str = m.groups()
                try:
                    rows.append(
                        {
                            "Date": pd.to_datetime(date_str, format="%d %b %y"),
                            "Description": desc.strip(),
                            "Amount": _clean(amt_str),
                            "Balance": _clean(bal_str),
                        }
                    )
                except ValueError:
                    continue
        return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])
