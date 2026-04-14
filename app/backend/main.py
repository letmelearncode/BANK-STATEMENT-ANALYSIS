"""FastAPI application — unified B2C bank statement analysis platform."""
from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import pdfplumber
from fastapi import (
    Depends, FastAPI, File, Form, HTTPException, Request,
    UploadFile, status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy.orm import Session

import auth as auth_module
import database as db_module
import schemas
from database import AuditLog, Budget, Statement, User, get_db, init_db
from ml import categorizer, health_score, loan_eligibility
from parsers import PARSERS, CsvImportParser, identify_bank
from security import audit, encryption

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
MAX_FILE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# ── App & middleware ──────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Bank Statement Analysis API",
    description="B2C platform for parsing, analysing and tracking bank statements.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()
    # Pre-load / train the ML model so first request is fast
    try:
        loan_eligibility.load_model()
        logger.info("Loan eligibility model ready.")
    except Exception as exc:  # noqa: BLE001
        logger.warning("Model pre-load failed: %s", exc)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok"}


@app.get("/categories", response_model=List[str], tags=["system"])
def list_categories():
    """Return the ordered list of expense categories recognised by the ML categoriser.

    The frontend fetches this endpoint so the category list is always in sync
    with the backend — no duplication or drift.
    """
    return [name for name, _ in categorizer.CATEGORY_RULES] + ["Others"]


# ── Auth ──────────────────────────────────────────────────────────────────────

@app.post("/auth/register", response_model=schemas.UserOut, tags=["auth"])
@limiter.limit("10/minute")
def register(request: Request, payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=auth_module.hash_password(payload.password),
        popia_consent=payload.popia_consent,
        popia_consent_at=datetime.utcnow() if payload.popia_consent else None,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    audit.log(db, "REGISTER", user_id=user.id, ip_address=request.client.host if request.client else None)
    return user


@app.post("/auth/login", response_model=schemas.TokenResponse, tags=["auth"])
@limiter.limit("20/minute")
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not auth_module.verify_password(form_data.password, user.hashed_password):
        audit.log(db, "LOGIN_FAILED", detail=form_data.username, ip_address=request.client.host if request.client else None)
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = auth_module.create_access_token({"sub": str(user.id)})
    audit.log(db, "LOGIN", user_id=user.id, ip_address=request.client.host if request.client else None)
    return {"access_token": token, "token_type": "bearer"}


@app.get("/auth/me", response_model=schemas.UserOut, tags=["auth"])
def me(current_user: User = Depends(auth_module.get_current_user)):
    return current_user


# ── Statements ────────────────────────────────────────────────────────────────

def _extract_text_from_pdf(content: bytes) -> str:
    text = ""
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text


def _run_analysis(df: pd.DataFrame) -> Dict[str, Any]:
    """Run categorisation, metrics, loan eligibility and health score."""
    if df.empty:
        return {"error": "No transactions found"}

    df = df.copy()
    df["Category"] = df["Description"].apply(categorizer.categorize)

    # Override categories provided by the user are applied in the update endpoint.

    # Metrics
    features = loan_eligibility.extract_features(df)
    # Category totals
    cat_totals = (
        df.groupby("Category")["Amount"].sum().round(2).to_dict()
    )
    # Loan eligibility + SHAP
    model = loan_eligibility.load_model()
    eligibility = loan_eligibility.predict(df, model)
    # Health score
    hs = health_score.compute(df, features)

    # Transactions as records (dates serialised as strings)
    df["Date"] = pd.to_datetime(df["Date"])
    tx_records = json.loads(
        df.assign(Date=df["Date"].dt.strftime("%Y-%m-%d")).to_json(orient="records")
    )

    return {
        "transactions": tx_records,
        "metrics": {
            "total_credits": round(features["total_credits"], 2),
            "total_debits": round(features["total_debits"], 2),
            "net": round(features["total_credits"] - features["total_debits"], 2),
            "num_transactions": features["num_transactions"],
            "avg_transaction_amount": round(features["avg_transaction_amount"], 2),
            "transaction_variability": round(features["transaction_variability"], 2),
            "balance_trend": round(features["balance_trend"], 2),
            "debt_to_income_ratio": round(features["debt_to_income_ratio"], 4),
            "savings_rate": round(features["savings_rate"], 4),
            "avg_balance": round(features["avg_balance"], 2),
        },
        "category_totals": cat_totals,
        "loan_eligibility": eligibility,
        "health_score": hs,
    }


@app.post("/statements/upload", response_model=schemas.AnalysisOut, tags=["statements"])
@limiter.limit("30/minute")
async def upload_statement(
    request: Request,
    file: UploadFile = File(...),
    budget_thresholds: Optional[str] = Form(None),  # JSON-encoded eligibility config override
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    # File size validation
    content = await file.read()
    if len(content) > MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_FILE_SIZE_MB} MB limit")

    filename = file.filename or "upload"
    ext = filename.rsplit(".", 1)[-1].lower()

    # Parse to DataFrame
    if ext == "pdf":
        text = _extract_text_from_pdf(content)
        bank_name = identify_bank(text)
        if bank_name == "Unknown":
            bank_name = "Unknown"
        parser_cls = PARSERS.get(bank_name)
        if parser_cls is None:
            raise HTTPException(status_code=422, detail=f"Unsupported bank: {bank_name}. Supported: {list(PARSERS.keys())}")
        df = parser_cls().parse(text)
    elif ext in ("csv", "ofx", "qfx", "qif"):
        bank_name = "CSV/OFX/QIF Import"
        df = CsvImportParser().parse_bytes(content, filename)
    else:
        raise HTTPException(status_code=415, detail="Unsupported file type. Upload a PDF, CSV, OFX, QFX or QIF file.")

    if df.empty:
        raise HTTPException(status_code=422, detail="No transactions could be extracted from the uploaded file.")

    # Derive statement month
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    df = df.dropna(subset=["Date"])
    statement_month = df["Date"].dt.to_period("M").mode()[0].strftime("%Y-%m") if not df.empty else None

    # Run analysis
    analysis = _run_analysis(df)

    # Encrypt and persist (raw file is NOT stored)
    encrypted = encryption.encrypt(json.dumps(analysis))
    stmt = Statement(
        user_id=current_user.id,
        filename=filename,
        bank_name=bank_name,
        statement_month=statement_month,
        analysis_json=encrypted,
    )
    db.add(stmt)
    db.commit()
    db.refresh(stmt)

    audit.log(
        db,
        "STATEMENT_UPLOAD",
        user_id=current_user.id,
        resource=f"statement:{stmt.id}",
        detail=f"{bank_name} {statement_month}",
        ip_address=request.client.host if request.client else None,
    )

    return {"statement": stmt, "analysis": analysis}


@app.get("/statements", response_model=List[schemas.StatementOut], tags=["statements"])
def list_statements(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    stmts = (
        db.query(Statement)
        .filter(Statement.user_id == current_user.id)
        .order_by(Statement.upload_date.desc())
        .all()
    )
    audit.log(db, "LIST_STATEMENTS", user_id=current_user.id)
    return stmts


@app.get("/statements/{statement_id}", response_model=schemas.AnalysisOut, tags=["statements"])
def get_statement(
    statement_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    stmt = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id,
    ).first()
    if stmt is None:
        raise HTTPException(status_code=404, detail="Statement not found")

    analysis = json.loads(encryption.decrypt(stmt.analysis_json))
    audit.log(
        db, "VIEW_STATEMENT", user_id=current_user.id,
        resource=f"statement:{stmt.id}",
        ip_address=request.client.host if request.client else None,
    )
    return {"statement": stmt, "analysis": analysis}


@app.delete("/statements/{statement_id}", tags=["statements"])
def delete_statement(
    statement_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    stmt = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id,
    ).first()
    if stmt is None:
        raise HTTPException(status_code=404, detail="Statement not found")
    db.delete(stmt)
    db.commit()
    audit.log(db, "DELETE_STATEMENT", user_id=current_user.id, resource=f"statement:{statement_id}")
    return {"detail": "Deleted"}


# ── Category override ─────────────────────────────────────────────────────────

@app.patch("/statements/{statement_id}/transactions/{tx_index}", tags=["statements"])
def update_category(
    statement_id: int,
    tx_index: int,
    new_category: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    """Allow users to manually re-categorise a transaction."""
    stmt = db.query(Statement).filter(
        Statement.id == statement_id,
        Statement.user_id == current_user.id,
    ).first()
    if stmt is None:
        raise HTTPException(status_code=404, detail="Statement not found")

    analysis = json.loads(encryption.decrypt(stmt.analysis_json))
    txs = analysis.get("transactions", [])
    if tx_index < 0 or tx_index >= len(txs):
        raise HTTPException(status_code=400, detail="Invalid transaction index")

    old_cat = txs[tx_index].get("Category")
    txs[tx_index]["Category"] = new_category
    analysis["transactions"] = txs

    # Recompute category_totals
    df = pd.DataFrame(txs)
    analysis["category_totals"] = df.groupby("Category")["Amount"].sum().round(2).to_dict()

    stmt.analysis_json = encryption.encrypt(json.dumps(analysis))
    db.commit()
    audit.log(
        db, "RECATEGORISE", user_id=current_user.id,
        resource=f"statement:{statement_id}/tx:{tx_index}",
        detail=f"{old_cat} -> {new_category}",
    )
    return {"detail": "Category updated", "old": old_cat, "new": new_category}


# ── History / Trends ──────────────────────────────────────────────────────────

@app.get("/analyses/history", response_model=List[schemas.MonthlySummary], tags=["analyses"])
def history(
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    stmts = (
        db.query(Statement)
        .filter(Statement.user_id == current_user.id)
        .order_by(Statement.statement_month)
        .all()
    )
    summaries: list[schemas.MonthlySummary] = []
    for stmt in stmts:
        if not stmt.analysis_json:
            continue
        try:
            analysis = json.loads(encryption.decrypt(stmt.analysis_json))
        except Exception:  # noqa: BLE001
            continue
        metrics = analysis.get("metrics", {})
        hs = analysis.get("health_score", {})
        summaries.append(
            schemas.MonthlySummary(
                month=stmt.statement_month or "Unknown",
                total_credits=metrics.get("total_credits", 0),
                total_debits=metrics.get("total_debits", 0),
                net=metrics.get("net", 0),
                health_score=hs.get("score"),
                bank_name=stmt.bank_name,
            )
        )
    audit.log(db, "VIEW_HISTORY", user_id=current_user.id)
    return summaries


# ── Budgets ───────────────────────────────────────────────────────────────────

@app.post("/budgets", response_model=schemas.BudgetOut, tags=["budgets"])
def upsert_budget(
    payload: schemas.BudgetIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    existing = db.query(Budget).filter(
        Budget.user_id == current_user.id,
        Budget.category == payload.category,
        Budget.month == payload.month,
    ).first()
    if existing:
        existing.monthly_limit = payload.monthly_limit
        db.commit()
        db.refresh(existing)
        return existing

    budget = Budget(
        user_id=current_user.id,
        category=payload.category,
        monthly_limit=payload.monthly_limit,
        month=payload.month,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@app.get("/budgets", response_model=List[schemas.BudgetOut], tags=["budgets"])
def list_budgets(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    query = db.query(Budget).filter(Budget.user_id == current_user.id)
    if month:
        query = query.filter(Budget.month == month)
    return query.order_by(Budget.month, Budget.category).all()


@app.get("/budgets/alerts", response_model=List[schemas.BudgetAlert], tags=["budgets"])
def budget_alerts(
    month: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(auth_module.get_current_user),
):
    """Return categories where spending has exceeded the set budget."""
    target_month = month or datetime.utcnow().strftime("%Y-%m")

    budgets = (
        db.query(Budget)
        .filter(Budget.user_id == current_user.id, Budget.month == target_month)
        .all()
    )
    if not budgets:
        return []

    # Find statement for that month
    stmt = (
        db.query(Statement)
        .filter(Statement.user_id == current_user.id, Statement.statement_month == target_month)
        .order_by(Statement.upload_date.desc())
        .first()
    )
    if not stmt or not stmt.analysis_json:
        return []

    analysis = json.loads(encryption.decrypt(stmt.analysis_json))
    cat_totals = analysis.get("category_totals", {})

    alerts: list[schemas.BudgetAlert] = []
    for b in budgets:
        spent = abs(cat_totals.get(b.category, 0.0))
        if spent > b.monthly_limit:
            alerts.append(
                schemas.BudgetAlert(
                    category=b.category,
                    limit=b.monthly_limit,
                    spent=spent,
                    over_by=round(spent - b.monthly_limit, 2),
                    month=target_month,
                )
            )
    return alerts
