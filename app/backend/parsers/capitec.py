"""Capitec Bank statement parser.

Capitec statements expose two date columns (posting date & transaction date)
plus separate money-in / money-out columns.

Typical line format:
    DD/MM/YYYY  DD/MM/YYYY  <description>  [1 234.56]  [1 234.56]  9 876.54
"""
import re
import pandas as pd
from parsers.base import BaseParser

# Two dates, optional money-in, optional money-out, balance
_PATTERN = re.compile(
    r"(\d{2}/\d{2}/\d{4})"           # posting date
    r"\s+(\d{2}/\d{2}/\d{4})"        # transaction date
    r"\s+(.+?)\s+"                   # description
    r"([\d\s]+\.\d{2})?"             # money in (optional)
    r"\s*"
    r"([\d\s]+\.\d{2})?"             # money out (optional)
    r"\s+"
    r"([\d\s]+\.\d{2})"              # balance
)


def _clean(s: str | None) -> float:
    if not s:
        return 0.0
    return float(s.replace(" ", "").replace(",", ""))


class CapitecParser(BaseParser):
    def parse(self, text: str) -> pd.DataFrame:
        rows: list[dict] = []
        for line in text.splitlines():
            m = _PATTERN.search(line)
            if m:
                _post, trans_date, desc, money_in, money_out, bal = m.groups()
                try:
                    credits = _clean(money_in)
                    debits = _clean(money_out)
                    # Net amount: credits are positive, debits are negative
                    amount = credits - debits if (credits or debits) else 0.0
                    rows.append(
                        {
                            "Date": pd.to_datetime(trans_date, format="%d/%m/%Y"),
                            "Description": desc.strip(),
                            "Amount": amount,
                            "Balance": _clean(bal),
                        }
                    )
                except ValueError:
                    continue
        return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])
