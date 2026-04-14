"""CSV / OFX / QIF import parser.

Accepts any of:
  - Generic CSV  (columns: date, description, amount  OR  debit/credit + balance)
  - OFX / QFX   (SGML/XML bank transaction feed)
  - QIF          (Quicken Interchange Format)

The normalised output is always:
    Date (datetime), Description (str), Amount (float), Balance (float)
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET
from typing import IO

import pandas as pd


# ── Generic CSV ───────────────────────────────────────────────────────────────

_DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%d %b %Y", "%d %b %y"]

_AMOUNT_COLUMNS = ["amount", "amt", "debit", "credit", "money_in", "money_out"]
_DATE_COLUMNS = ["date", "transaction_date", "trans_date", "posting_date"]
_DESC_COLUMNS = ["description", "desc", "narrative", "details", "reference"]
_BAL_COLUMNS = ["balance", "bal", "running_balance"]


def _try_parse_date(s: str) -> pd.Timestamp:
    for fmt in _DATE_FORMATS:
        try:
            return pd.to_datetime(s, format=fmt)
        except ValueError:
            continue
    return pd.to_datetime(s, infer_datetime_format=True)


def _find_col(cols: list[str], candidates: list[str]) -> str | None:
    lower = {c.lower().strip(): c for c in cols}
    for cand in candidates:
        if cand in lower:
            return lower[cand]
    return None


def parse_csv(content: bytes | str) -> pd.DataFrame:
    raw = pd.read_csv(io.StringIO(content if isinstance(content, str) else content.decode("utf-8", errors="replace")))
    raw.columns = [c.strip() for c in raw.columns]
    cols = list(raw.columns)

    date_col = _find_col(cols, _DATE_COLUMNS)
    desc_col = _find_col(cols, _DESC_COLUMNS)
    bal_col = _find_col(cols, _BAL_COLUMNS)
    amt_col = _find_col(cols, _AMOUNT_COLUMNS)

    if date_col is None or desc_col is None:
        raise ValueError("CSV must contain at minimum date and description columns.")

    rows: list[dict] = []
    for _, row in raw.iterrows():
        try:
            date = _try_parse_date(str(row[date_col]))
            desc = str(row[desc_col])

            if amt_col:
                val = str(row[amt_col]).replace(",", "").replace("R", "").strip()
                amount = float(val) if val not in ("", "nan") else 0.0
            elif _find_col(cols, ["credit"]) and _find_col(cols, ["debit"]):
                cr_col = _find_col(cols, ["credit"])
                db_col = _find_col(cols, ["debit"])
                cr = float(str(row[cr_col]).replace(",", "").replace("R", "").strip() or 0)
                db = float(str(row[db_col]).replace(",", "").replace("R", "").strip() or 0)
                amount = cr - db
            else:
                amount = 0.0

            balance = float(str(row[bal_col]).replace(",", "").replace("R", "").strip()) if bal_col else 0.0
            rows.append({"Date": date, "Description": desc, "Amount": amount, "Balance": balance})
        except (ValueError, KeyError):
            continue

    return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])


# ── OFX / QFX ────────────────────────────────────────────────────────────────

def parse_ofx(content: bytes | str) -> pd.DataFrame:
    """Parse a basic OFX/QFX file.  Strips the SGML header and uses ElementTree."""
    text = content if isinstance(content, str) else content.decode("utf-8", errors="replace")
    # Convert SGML to minimal XML (close all open tags)
    xml_text = re.sub(r"<([A-Z.]+)>([^<\n]+)", r"<\1>\2</\1>", text)
    # Wrap in root if needed
    if not xml_text.strip().startswith("<?xml") and "<OFX>" in xml_text:
        xml_text = "<ROOT>" + xml_text + "</ROOT>"
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return pd.DataFrame(columns=["Date", "Description", "Amount", "Balance"])

    rows: list[dict] = []
    balance = 0.0
    running = 0.0
    for stmttrn in root.iter("STMTTRN"):
        try:
            dtposted = (stmttrn.findtext("DTPOSTED") or "")[:8]
            date = pd.to_datetime(dtposted, format="%Y%m%d")
            amount = float(stmttrn.findtext("TRNAMT") or 0)
            memo = stmttrn.findtext("MEMO") or stmttrn.findtext("NAME") or ""
            running += amount
            rows.append({"Date": date, "Description": memo.strip(), "Amount": amount, "Balance": running})
        except (ValueError, TypeError):
            continue

    return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])


# ── QIF ───────────────────────────────────────────────────────────────────────

def parse_qif(content: bytes | str) -> pd.DataFrame:
    text = content if isinstance(content, str) else content.decode("utf-8", errors="replace")
    rows: list[dict] = []
    current: dict = {}
    running = 0.0
    for line in text.splitlines():
        if not line.strip():
            continue
        code = line[0]
        value = line[1:].strip()
        if code == "D":  # date
            current["date"] = value
        elif code == "T":  # amount
            current["amount"] = float(value.replace(",", "").replace("$", "").replace("R", ""))
        elif code == "P":  # payee / description
            current["desc"] = value
        elif code == "^":  # end of record
            if current:
                try:
                    date = _try_parse_date(current.get("date", ""))
                    amount = current.get("amount", 0.0)
                    running += amount
                    rows.append({
                        "Date": date,
                        "Description": current.get("desc", ""),
                        "Amount": amount,
                        "Balance": running,
                    })
                except ValueError:
                    pass
            current = {}
    return pd.DataFrame(rows, columns=["Date", "Description", "Amount", "Balance"])


# ── Unified entry point ───────────────────────────────────────────────────────

class CsvImportParser:
    """Parse CSV, OFX or QIF file bytes into a normalised DataFrame."""

    def parse_bytes(self, content: bytes, filename: str) -> pd.DataFrame:
        ext = filename.rsplit(".", 1)[-1].lower()
        if ext in ("ofx", "qfx"):
            return parse_ofx(content)
        if ext == "qif":
            return parse_qif(content)
        # Default: CSV
        return parse_csv(content)
