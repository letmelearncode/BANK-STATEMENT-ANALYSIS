"""FNB bank statement parser.

Transaction line format:
    DD MMM  <description>  1,234.56(Cr|Dr)  9,876.54
"""
import re
import pandas as pd
from parsers.base import BaseParser

_PATTERN = re.compile(
    r"(\d{2}\s+\w{3})"                    # date  e.g. "15 Jan"
    r"\s+(.+?)\s+"                         # description
    r"(\d+(?:,\d{3})*(?:\.\d{2})?)"       # amount (no sign yet)
    r"(Cr|Dr)?"                            # optional credit/debit indicator
    r"\s+"
    r"(\d+(?:,\d{3})*(?:\.\d{2})?)"       # balance
)


def _clean(s: str) -> float:
    return float(s.replace(",", ""))


class FnbParser(BaseParser):
    def parse(self, text: str) -> pd.DataFrame:
        rows: list[dict] = []
        for line in text.splitlines():
            m = _PATTERN.search(line)
            if m:
                date_str, desc, amt_str, indicator, bal_str = m.groups()
                try:
                    amount = _clean(amt_str)
                    # FNB uses Cr for credits (money in, positive) and Dr for debits (money out, negative)
                    if indicator == "Dr":
                        amount = -amount
                    rows.append(
                        {
                            "Date": pd.to_datetime(date_str, format="%d %b"),
                            "Description": desc.strip(),
                            "Amount": amount,
                            "Balance": _clean(bal_str),
                        }
                    )
                except ValueError:
                    continue
        df = pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])
        # FNB dates lack a year — infer from current year
        if not df.empty:
            current_year = pd.Timestamp.now().year
            df["Date"] = df["Date"].apply(lambda d: d.replace(year=current_year))
        return df
