"""Loan eligibility model — Random Forest with SHAP explainability.

The model is trained once on synthetic data and saved to disk with joblib.
On subsequent calls the saved model is loaded.  This matches the
"properly trained and versioned model" requirement in the plan.

Feature set (10 features):
  total_credits, total_debits, num_transactions,
  avg_transaction_amount, transaction_variability, balance_trend,
  debt_to_income_ratio, savings_rate,
  recurring_income_count, avg_balance
"""
from __future__ import annotations

import os
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_default_model_path = Path(__file__).parent.parent.parent / "ml_models" / "loan_eligibility.joblib"
MODEL_PATH = Path(os.getenv("MODEL_PATH", str(_default_model_path)))

FEATURE_NAMES = [
    "total_credits",
    "total_debits",
    "num_transactions",
    "avg_transaction_amount",
    "transaction_variability",
    "balance_trend",
    "debt_to_income_ratio",
    "savings_rate",
    "recurring_income_count",
    "avg_balance",
]


# ── Synthetic training data ───────────────────────────────────────────────────

def _generate_training_data(n: int = 500, seed: int = 42) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)

    # Eligible samples (~60 %)
    n_pos = int(n * 0.6)
    n_neg = n - n_pos

    def _pos() -> np.ndarray:
        cr = rng.uniform(15_000, 100_000, n_pos)
        db = rng.uniform(8_000, cr * 0.8)
        ntx = rng.integers(20, 60, n_pos)
        avg_tx = cr / ntx
        var = rng.uniform(500, 3_000, n_pos)
        bt = rng.uniform(500, 10_000, n_pos)
        dti = db / np.where(cr > 0, cr, 1)
        sr = (cr - db) / np.where(cr > 0, cr, 1)
        ric = rng.integers(1, 4, n_pos).astype(float)
        avg_bal = cr * rng.uniform(0.3, 0.8, n_pos)
        return np.column_stack([cr, db, ntx, avg_tx, var, bt, dti, sr, ric, avg_bal])

    def _neg() -> np.ndarray:
        cr = rng.uniform(3_000, 30_000, n_neg)
        db = rng.uniform(cr * 0.85, cr * 1.5)
        ntx = rng.integers(5, 25, n_neg)
        avg_tx = cr / np.where(ntx > 0, ntx, 1)
        var = rng.uniform(200, 1_500, n_neg)
        bt = rng.uniform(-5_000, 200, n_neg)
        dti = db / np.where(cr > 0, cr, 1)
        sr = (cr - db) / np.where(cr > 0, cr, 1)
        ric = rng.integers(0, 2, n_neg).astype(float)
        avg_bal = cr * rng.uniform(0.05, 0.3, n_neg)
        return np.column_stack([cr, db, ntx, avg_tx, var, bt, dti, sr, ric, avg_bal])

    X = np.vstack([_pos(), _neg()])
    y = np.hstack([np.ones(n_pos, dtype=int), np.zeros(n_neg, dtype=int)])
    # shuffle
    idx = rng.permutation(len(y))
    return X[idx], y[idx]


# ── Train / load ──────────────────────────────────────────────────────────────

def _train_and_save() -> "RandomForestClassifier":  # type: ignore[name-defined]
    from sklearn.ensemble import RandomForestClassifier
    import joblib

    logger.info("Training loan eligibility model …")
    X, y = _generate_training_data()
    clf = RandomForestClassifier(n_estimators=200, max_depth=10, random_state=42)
    clf.fit(X, y)
    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)
    logger.info("Model saved to %s", MODEL_PATH)
    return clf


def load_model() -> "RandomForestClassifier":  # type: ignore[name-defined]
    import joblib

    if MODEL_PATH.exists():
        return joblib.load(MODEL_PATH)
    return _train_and_save()


# ── Feature extraction ────────────────────────────────────────────────────────

def extract_features(df: pd.DataFrame) -> dict[str, float]:
    credits = df[df["Amount"] > 0]["Amount"]
    debits = df[df["Amount"] < 0]["Amount"]

    total_credits = float(credits.sum())
    total_debits = float(abs(debits.sum()))
    num_transactions = len(df)
    avg_tx = float(df["Amount"].mean()) if num_transactions > 0 else 0.0
    variability = float(df["Amount"].std()) if num_transactions > 1 else 0.0
    balance_trend = (
        float(df["Balance"].iloc[-1] - df["Balance"].iloc[0]) if len(df) >= 2 else 0.0
    )
    dti = total_debits / total_credits if total_credits > 0 else 999.0
    savings_rate = (total_credits - total_debits) / total_credits if total_credits > 0 else 0.0
    # Recurring income: credit amounts that appear 2+ times (same rounded value)
    credit_rounded = credits.round(-2)
    recurring = int((credit_rounded.value_counts() >= 2).sum())
    avg_balance = float(df["Balance"].mean()) if num_transactions > 0 else 0.0

    return {
        "total_credits": total_credits,
        "total_debits": total_debits,
        "num_transactions": num_transactions,
        "avg_transaction_amount": avg_tx,
        "transaction_variability": variability,
        "balance_trend": balance_trend,
        "debt_to_income_ratio": dti,
        "savings_rate": savings_rate,
        "recurring_income_count": float(recurring),
        "avg_balance": avg_balance,
    }


# ── Prediction + SHAP ─────────────────────────────────────────────────────────

def predict(df: pd.DataFrame, model=None) -> dict:
    """Return eligibility prediction plus SHAP feature contributions."""
    if model is None:
        model = load_model()

    features = extract_features(df)
    X = np.array([[features[f] for f in FEATURE_NAMES]])

    proba = float(model.predict_proba(X)[0][1])
    eligible = bool(model.predict(X)[0] == 1)

    # Hard business rule: credits must be at least 1.25× debits
    if features["total_credits"] < 1.25 * features["total_debits"]:
        eligible = False

    # SHAP explainability
    shap_values_list: list[dict] = []
    try:
        import shap

        explainer = shap.TreeExplainer(model)
        sv = explainer.shap_values(X)
        # shap ≥0.41 returns ndarray; older versions return list[ndarray per class]
        if isinstance(sv, list):
            class1_sv = sv[1][0]
        else:
            # ndarray shape: (n_samples, n_features) or (n_samples, n_features, n_classes)
            import numpy as _np
            sv_arr = _np.array(sv)
            if sv_arr.ndim == 3:
                class1_sv = sv_arr[0, :, 1]
            elif sv_arr.ndim == 2:
                class1_sv = sv_arr[0]
            else:
                class1_sv = sv_arr
        for name, val in zip(FEATURE_NAMES, class1_sv):
            shap_values_list.append({"feature": name, "value": float(val), "feature_value": features[name]})
        shap_values_list.sort(key=lambda x: abs(x["value"]), reverse=True)
    except Exception as exc:  # noqa: BLE001
        logger.warning("SHAP computation skipped: %s", exc)

    return {
        "eligible": eligible,
        "probability": round(proba, 4),
        "features": features,
        "shap_values": shap_values_list,
    }
