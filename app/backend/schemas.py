"""Pydantic schemas for request / response validation."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    popia_consent: bool

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @field_validator("popia_consent")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("You must accept the POPIA consent to register")
        return v


class LoginRequest(BaseModel):
    username: str  # email (OAuth2 form field is called username)
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    created_at: datetime
    popia_consent: bool

    model_config = {"from_attributes": True}


# ── Statements ────────────────────────────────────────────────────────────────

class StatementOut(BaseModel):
    id: int
    filename: str
    bank_name: str
    statement_month: Optional[str]
    upload_date: datetime

    model_config = {"from_attributes": True}


class AnalysisOut(BaseModel):
    statement: StatementOut
    analysis: Dict[str, Any]


# ── Budgets ───────────────────────────────────────────────────────────────────

class BudgetIn(BaseModel):
    category: str
    monthly_limit: float
    month: str  # YYYY-MM


class BudgetOut(BaseModel):
    id: int
    category: str
    monthly_limit: float
    month: str

    model_config = {"from_attributes": True}


class BudgetAlert(BaseModel):
    category: str
    limit: float
    spent: float
    over_by: float
    month: str


# ── History / Trends ─────────────────────────────────────────────────────────

class MonthlySummary(BaseModel):
    month: str
    total_credits: float
    total_debits: float
    net: float
    health_score: Optional[int]
    bank_name: str
