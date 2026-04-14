"""Financial health score (0–100) and grade.

Breakdown (max points):
  - Savings Rate          30 pts
  - Debt-to-Income        25 pts
  - Income Stability      25 pts  (recurring income)
  - Expense Consistency   20 pts  (low variability relative to avg)
"""
from __future__ import annotations

import pandas as pd


def compute(df: pd.DataFrame, features: dict) -> dict:
    score = 0
    breakdown: dict[str, dict] = {}

    # ── 1. Savings Rate (0–30) ────────────────────────────────────────────────
    sr = features.get("savings_rate", 0.0)
    if sr >= 0.30:
        sr_pts = 30
    elif sr >= 0.20:
        sr_pts = 22
    elif sr >= 0.10:
        sr_pts = 14
    elif sr >= 0.0:
        sr_pts = 6
    else:
        sr_pts = 0
    score += sr_pts
    breakdown["savings_rate"] = {
        "points": sr_pts,
        "max": 30,
        "value": round(sr * 100, 1),
        "label": f"{round(sr * 100, 1)}% savings rate",
    }

    # ── 2. Debt-to-Income (0–25) ──────────────────────────────────────────────
    dti = features.get("debt_to_income_ratio", 1.0)
    if dti <= 0.4:
        dti_pts = 25
    elif dti <= 0.6:
        dti_pts = 18
    elif dti <= 0.8:
        dti_pts = 10
    elif dti <= 1.0:
        dti_pts = 4
    else:
        dti_pts = 0
    score += dti_pts
    breakdown["debt_to_income"] = {
        "points": dti_pts,
        "max": 25,
        "value": round(dti * 100, 1),
        "label": f"{round(dti * 100, 1)}% debt-to-income",
    }

    # ── 3. Income Stability (0–25) ────────────────────────────────────────────
    ric = int(features.get("recurring_income_count", 0))
    if ric >= 3:
        inc_pts = 25
    elif ric == 2:
        inc_pts = 18
    elif ric == 1:
        inc_pts = 10
    else:
        inc_pts = 0
    score += inc_pts
    breakdown["income_stability"] = {
        "points": inc_pts,
        "max": 25,
        "value": ric,
        "label": f"{ric} recurring income source(s)",
    }

    # ── 4. Expense Consistency (0–20) ────────────────────────────────────────
    avg_tx = abs(features.get("avg_transaction_amount", 1))
    var = features.get("transaction_variability", 0)
    cv = var / avg_tx if avg_tx > 0 else 1.0  # coefficient of variation
    if cv <= 0.5:
        exp_pts = 20
    elif cv <= 1.0:
        exp_pts = 14
    elif cv <= 2.0:
        exp_pts = 7
    else:
        exp_pts = 0
    score += exp_pts
    breakdown["expense_consistency"] = {
        "points": exp_pts,
        "max": 20,
        "value": round(cv, 2),
        "label": f"CV {round(cv, 2)} (lower is better)",
    }

    # ── Grade ─────────────────────────────────────────────────────────────────
    if score >= 80:
        grade = "A"
    elif score >= 65:
        grade = "B"
    elif score >= 50:
        grade = "C"
    elif score >= 35:
        grade = "D"
    else:
        grade = "F"

    return {"score": score, "grade": grade, "breakdown": breakdown}
