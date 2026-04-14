"""NedBank statement parser.

Transaction line format:
    DD/MM/YYYY  <description>  [-]R1,234.56  [-]R9,876.54
"""
import re
import pandas as pd
from parsers.base import BaseParser

_PATTERN = re.compile(
    r"(\d{2}/\d{2}/\d{4})"                              # date DD/MM/YYYY
    r"\s+(.+?)\s+"
    r"(-?R?\d+(?:,\d{3})*(?:\.\d{2})?)"                 # amount
    r"\s+"
    r"(-?R?\d+(?:,\d{3})*(?:\.\d{2})?)"                 # balance
)


def _clean(s: str) -> float:
    return float(s.replace(",", "").replace("R", "").replace(" ", ""))


class NedbankParser(BaseParser):
    def parse(self, text: str) -> pd.DataFrame:
        rows: list[dict] = []
        prev_balance: float | None = None

        for line in text.splitlines():
            m = _PATTERN.search(line)
            if m:
                date_str, desc, amt_str, bal_str = m.groups()
                try:
                    amount = _clean(amt_str)
                    balance = _clean(bal_str)
                    # Infer sign from balance movement when amount has no sign
                    if amount > 0 and prev_balance is not None and balance < prev_balance:
                        amount = -amount
                    rows.append(
                        {
                            "Date": pd.to_datetime(date_str, format="%d/%m/%Y"),
                            "Description": desc.strip(),
                            "Amount": amount,
                            "Balance": balance,
                        }
                    )
                    prev_balance = balance
                except ValueError:
                    continue
        return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])
