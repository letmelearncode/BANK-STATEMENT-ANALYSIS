# Bank Statement Analysis — Feature Catalogue

This document lists every feature that is **currently implemented** in the unified
`app/` B2C platform, and then describes additional features that would make the
product more competitive in the consumer (B2C) market.

---

## Table of Contents

1. [Implemented Features](#1-implemented-features)
   - 1.1 [Bank Statement Parsing](#11-bank-statement-parsing)
   - 1.2 [User Authentication & Accounts](#12-user-authentication--accounts)
   - 1.3 [Expense Categorisation](#13-expense-categorisation)
   - 1.4 [Key Financial Metrics](#14-key-financial-metrics)
   - 1.5 [Loan Eligibility (ML + SHAP)](#15-loan-eligibility-ml--shap)
   - 1.6 [Financial Health Score](#16-financial-health-score)
   - 1.7 [Multi-Statement History & Trends](#17-multi-statement-history--trends)
   - 1.8 [Budgeting Module](#18-budgeting-module)
   - 1.9 [Visualisations](#19-visualisations)
   - 1.10 [Security & Compliance](#110-security--compliance)
   - 1.11 [Infrastructure & Deployment](#111-infrastructure--deployment)
2. [Proposed B2C Features](#2-proposed-b2c-features)
   - 2.1 [Personalisation & Onboarding](#21-personalisation--onboarding)
   - 2.2 [Advanced Analytics & Forecasting](#22-advanced-analytics--forecasting)
   - 2.3 [Savings Goals & Gamification](#23-savings-goals--gamification)
   - 2.4 [Debt & Loan Management](#24-debt--loan-management)
   - 2.5 [Notifications & Alerts](#25-notifications--alerts)
   - 2.6 [Open Banking / Data Connectors](#26-open-banking--data-connectors)
   - 2.7 [Financial Marketplace](#27-financial-marketplace)
   - 2.8 [Multi-Currency & Multi-Country](#28-multi-currency--multi-country)
   - 2.9 [Collaboration & Shared Finances](#29-collaboration--shared-finances)
   - 2.10 [Mobile & Accessibility](#210-mobile--accessibility)
   - 2.11 [AI-Powered Features](#211-ai-powered-features)
   - 2.12 [Tax & Compliance Tools](#212-tax--compliance-tools)
   - 2.13 [Integrations](#213-integrations)
   - 2.14 [Admin & Business Operations](#214-admin--business-operations)

---

## 1. Implemented Features

### 1.1 Bank Statement Parsing

| Feature | Detail | Code Location |
|---|---|---|
| **Automatic bank detection** | Identifies the bank from PDF text before routing to the correct parser | `app/backend/parsers/bank_identifier.py` |
| **ABSA parser** | Regex-based extraction for ABSA date/description/amount/balance format | `app/backend/parsers/absa.py` |
| **FNB parser** | Handles FNB-specific date and Cr/Dr formatting | `app/backend/parsers/fnb.py` |
| **Nedbank parser** | Tracks debit/credit split with running balance | `app/backend/parsers/nedbank.py` |
| **Standard Bank parser** | Parses Standard Bank short-date format | `app/backend/parsers/standard_bank.py` |
| **Capitec parser** | Handles separate "money in" / "money out" columns | `app/backend/parsers/capitec.py` |
| **CSV import** | Generic CSV with flexible column mapping | `app/backend/parsers/csv_import.py` |
| **OFX / QFX import** | Open Financial Exchange format (used by most online banking exports) | `app/backend/parsers/csv_import.py` |
| **QIF import** | Quicken Interchange Format | `app/backend/parsers/csv_import.py` |
| **File size validation** | Rejects uploads above the configured `MAX_FILE_SIZE_MB` limit | `app/backend/main.py` |

---

### 1.2 User Authentication & Accounts

| Feature | Detail | Code Location |
|---|---|---|
| **User registration** | Email + password + full name; enforces minimum 8-char password | `app/backend/main.py`, `app/backend/schemas.py` |
| **JWT authentication** | Stateless bearer tokens with configurable expiry | `app/backend/auth.py` |
| **bcrypt password hashing** | Industry-standard one-way hashing with salt | `app/backend/auth.py` |
| **POPIA consent** | Explicit opt-in checkbox at registration; timestamp recorded in the database | `app/backend/database.py`, `app/backend/schemas.py` |
| **Token-protected endpoints** | All statement/budget/history endpoints require a valid JWT | `app/backend/main.py` |
| **Current user info endpoint** | `GET /auth/me` returns profile details without exposing the password hash | `app/backend/main.py` |

---

### 1.3 Expense Categorisation

| Feature | Detail | Code Location |
|---|---|---|
| **18 built-in categories** | Salary, Credits, Rent & Utilities, Groceries, Transport, Insurance, Medical, Entertainment, Shopping, Cellular Expenses, Bank Charges, Payments, Cash Deposits/Withdrawals, Interest and Fees, Unsuccessful Transactions, Education, Savings & Investments, Others | `app/backend/ml/categorizer.py` |
| **Keyword-rule engine** | Priority-ordered keyword matching; first-match wins for speed | `app/backend/ml/categorizer.py` |
| **Manual re-categorisation** | Users can override the auto-assigned category for any single transaction via `PATCH /statements/{id}/transactions/{idx}` | `app/backend/main.py` |
| **Category totals recalculation** | After any override, category totals are recomputed and stored | `app/backend/main.py` |
| **Single source of truth** | `GET /categories` endpoint exposes the live category list so the frontend never has a hard-coded copy | `app/backend/main.py`, `app/backend/ml/categorizer.py` |

---

### 1.4 Key Financial Metrics

The following metrics are computed for every uploaded statement:

| Metric | Description |
|---|---|
| `total_credits` | Sum of all positive (incoming) transactions |
| `total_debits` | Sum of all negative (outgoing) transactions (absolute value) |
| `net` | `total_credits − total_debits` |
| `num_transactions` | Total number of rows parsed |
| `avg_transaction_amount` | Mean transaction amount |
| `transaction_variability` | Standard deviation of transaction amounts |
| `balance_trend` | Closing balance minus opening balance |
| `debt_to_income_ratio` | `total_debits / total_credits` |
| `savings_rate` | `(total_credits − total_debits) / total_credits` |
| `avg_balance` | Mean running balance over the statement period |
| `recurring_income_count` | Number of distinct credit amounts that appear ≥ 2 times (income stability proxy) |

Code: `app/backend/ml/loan_eligibility.py` (`extract_features`)

---

### 1.5 Loan Eligibility (ML + SHAP)

| Feature | Detail | Code Location |
|---|---|---|
| **Random Forest classifier** | 200-estimator model, trained on synthetic but statistically realistic data | `app/backend/ml/loan_eligibility.py` |
| **10-feature model** | Trained on all metrics listed in §1.4 | `app/backend/ml/loan_eligibility.py` |
| **Joblib persistence** | Model serialised to disk; reloaded on startup so first request is fast | `app/backend/ml/loan_eligibility.py` |
| **Hard business rule** | Credits must be ≥ 1.25× debits regardless of model output | `app/backend/ml/loan_eligibility.py` |
| **Eligibility probability** | Returns a confidence score (0–1) in addition to the binary decision | `app/backend/ml/loan_eligibility.py` |
| **SHAP explainability** | TreeExplainer produces per-feature contribution values so users understand *why* they are or aren't eligible | `app/backend/ml/loan_eligibility.py` |

---

### 1.6 Financial Health Score

| Feature | Detail | Code Location |
|---|---|---|
| **Composite 0–100 score** | Weighted across four dimensions | `app/backend/ml/health_score.py` |
| **Savings Rate (30 pts)** | ≥30 % → A; proportional bands below | `app/backend/ml/health_score.py` |
| **Debt-to-Income (25 pts)** | ≤40 % DTI → full points | `app/backend/ml/health_score.py` |
| **Income Stability (25 pts)** | Based on `recurring_income_count` | `app/backend/ml/health_score.py` |
| **Expense Consistency (20 pts)** | Coefficient of variation of transaction amounts | `app/backend/ml/health_score.py` |
| **Letter grade (A–F)** | 80+ → A, 65+ → B, 50+ → C, 35+ → D, <35 → F | `app/backend/ml/health_score.py` |
| **Detailed breakdown** | Each dimension returns its points, max, raw value and a plain-English label | `app/backend/ml/health_score.py` |

---

### 1.7 Multi-Statement History & Trends

| Feature | Detail | Code Location |
|---|---|---|
| **Multiple uploads** | Users can upload statements from any number of months; each is stored separately | `app/backend/database.py` (Statement model) |
| **Statement list** | `GET /statements` returns all statements in reverse-chronological order | `app/backend/main.py` |
| **Month-over-month summary** | `GET /analyses/history` returns credits, debits, net and health score per month | `app/backend/main.py` |
| **Statement deletion** | `DELETE /statements/{id}` removes a statement and all its encrypted analysis data | `app/backend/main.py` |

---

### 1.8 Budgeting Module

| Feature | Detail | Code Location |
|---|---|---|
| **Per-category monthly budget** | `POST /budgets` creates or updates a spending limit for a category/month pair | `app/backend/main.py` |
| **Budget list** | `GET /budgets?month=YYYY-MM` retrieves all limits for the user, optionally filtered by month | `app/backend/main.py` |
| **Overspend alerts** | `GET /budgets/alerts` compares actual category spending against limits and returns every breached category | `app/backend/main.py` |
| **Upsert semantics** | Setting a budget that already exists updates it in place without duplicating rows | `app/backend/main.py` |

---

### 1.9 Visualisations

Rendered in the Streamlit frontend using Plotly:

| Chart | Description |
|---|---|
| **Expenses per date (bar)** | Stacked bar chart coloured by category |
| **Expense distribution by category (pie)** | Share of spend per category |
| **Expense distribution by description (pie)** | Share of spend per merchant/description |
| **Daily expense trend (line)** | Running amount over time |
| **Month-over-month line charts** | Credits, debits and net across all uploaded statements |
| **Budget status bars** | Per-category actual vs. limit |
| **Health score gauge + breakdown table** | Visual 0–100 gauge with dimension drill-down |

Code: `app/frontend/app.py`

---

### 1.10 Security & Compliance

| Feature | Detail | Code Location |
|---|---|---|
| **Fernet at-rest encryption** | Analysis JSON is encrypted with AES-128-CBC (via `cryptography.fernet`) before being stored; raw PDFs are never persisted | `app/backend/security/encryption.py` |
| **Strong key enforcement** | Application refuses to start if `SECRET_KEY` is missing or < 32 characters | `app/backend/security/encryption.py` |
| **Audit log** | Every significant action (register, login, upload, view, delete, re-categorise) is written to the `audit_logs` table with user ID, IP address and timestamp | `app/backend/security/audit.py` |
| **Rate limiting** | Login endpoint: 20 req/min; Register: 10 req/min; Upload: 30 req/min (via slowapi) | `app/backend/main.py` |
| **POPIA compliance** | Consent recorded at registration; no raw financial document stored | `app/backend/database.py` |
| **Password validation** | Minimum 8-character password enforced at the schema layer | `app/backend/schemas.py` |
| **JWT expiry** | Configurable token lifetime via `ACCESS_TOKEN_EXPIRE_MINUTES` | `app/backend/auth.py` |
| **Docker secrets via env var** | `docker-compose.yml` uses `${SECRET_KEY:?...}` — compose startup fails if the variable is missing | `app/docker-compose.yml` |

---

### 1.11 Infrastructure & Deployment

| Feature | Detail | Code Location |
|---|---|---|
| **FastAPI backend** | Fully decoupled REST API; enables mobile and third-party integrations | `app/backend/main.py` |
| **Streamlit frontend** | Multi-page consumer UI with login, dashboard, upload, analysis, history and budgeting pages | `app/frontend/app.py` |
| **Docker images** | Separate `Dockerfile.backend` and `Dockerfile.frontend` | `app/Dockerfile.backend`, `app/Dockerfile.frontend` |
| **Docker Compose** | Single `docker-compose up --build` starts both services with a health check | `app/docker-compose.yml` |
| **SQLite default / Postgres-ready** | `DATABASE_URL` env var; SQLite for local dev, swap to Postgres for production | `app/backend/database.py` |
| **Health check endpoint** | `GET /health` returns `{"status": "ok"}` for container orchestration | `app/backend/main.py` |
| **Startup model pre-load** | ML model is loaded/trained at startup to avoid cold-start latency on first upload | `app/backend/main.py` |
| **CORS middleware** | Configurable allowed origins for API consumers | `app/backend/main.py` |
| **OpenAPI docs** | Interactive Swagger UI at `http://localhost:8000/docs` | FastAPI built-in |

---

## 2. Proposed B2C Features

The following features are **not yet implemented** and represent natural extensions
for a competitive consumer finance product.

---

### 2.1 Personalisation & Onboarding

| Feature | Value to User | Notes |
|---|---|---|
| **Guided onboarding wizard** | Reduces drop-off for first-time users | Collect financial goals (save for car, pay off debt, etc.) and pre-configure budgets |
| **User profile & preferences** | Lets users set currency, locale and preferred bank | Store in `users` table; expose `PATCH /auth/me` |
| **Custom expense categories** | Power users can add/rename/merge categories | Requires a `user_categories` table and override logic in the categoriser |
| **Dark / light theme toggle** | Accessibility and personal preference | Streamlit theme config |
| **Multi-language support (i18n)** | South Africa has 11 official languages | `gettext` or a translation JSON for UI strings |

---

### 2.2 Advanced Analytics & Forecasting

| Feature | Value to User | Notes |
|---|---|---|
| **Spending forecast** | "Based on your history, you will spend ~R X on groceries next month" | Prophet or linear regression on monthly category totals |
| **Income forecast** | Predicted salary credit date and amount | Detect recurring credits and project forward |
| **Cashflow calendar** | Visual calendar showing expected debits and credits | Combine recurring detection with a calendar widget |
| **Merchant-level analytics** | Drill into every transaction for a specific merchant (e.g. all Uber trips) | Filter on description substring |
| **Spending anomaly detection** | Alert when a transaction is unusually large for its category | Z-score or Isolation Forest on historical amounts |
| **Comparative benchmarks** | "You spend 20 % more on food than users in your income bracket" | Requires anonymised population statistics |

---

### 2.3 Savings Goals & Gamification

| Feature | Value to User | Notes |
|---|---|---|
| **Savings goals** | "Save R10 000 for a holiday by December" | New `goals` table: target amount, deadline, linked category |
| **Goal progress tracker** | Visual progress bar and projected completion date | Inferred from monthly net savings |
| **Streaks & badges** | "You've been under budget for 3 months — Gold Saver badge" | Gamification drives engagement and retention |
| **Round-up savings** | Automatically round transactions up and log the difference as a saving | Virtual; no real money movement required |
| **Challenge mode** | "No takeaway spending for 30 days" | User-defined or curated challenges with progress tracking |

---

### 2.4 Debt & Loan Management

| Feature | Value to User | Notes |
|---|---|---|
| **Debt tracker** | Log outstanding loans, credit cards and store accounts with balances and interest rates | New `debts` table |
| **Debt avalanche / snowball calculator** | Optimal payoff order and timeline | Pure calculation, no external data needed |
| **Loan eligibility history** | Show how eligibility score has changed over time | Already stored per statement, just needs a trend view |
| **Personalised improvement tips** | "Pay down your credit card to improve your DTI from 85 % to below 60 %" | Derived from current SHAP values and health score breakdown |
| **Pre-qualification check** | Soft credit assessment before a formal application | Extend the existing ML model with more features |

---

### 2.5 Notifications & Alerts

| Feature | Value to User | Notes |
|---|---|---|
| **Email notifications** | Budget breach alerts, monthly summary, health score change | FastAPI-Mail or SendGrid |
| **Push notifications** | Mobile/browser push for real-time alerts | Web Push API or Firebase Cloud Messaging |
| **Weekly / monthly digest** | Auto-generated spending summary email | Scheduled task (APScheduler or Celery beat) |
| **Salary received alert** | Notify user when a salary-tagged credit appears | Event hook in the upload pipeline |
| **Unusual transaction alert** | Potential fraud or error flag | Combine anomaly detection (§2.2) with email/push |

---

### 2.6 Open Banking / Data Connectors

| Feature | Value to User | Notes |
|---|---|---|
| **Direct bank feed (Open Banking)** | Automatic statement refresh without manual PDF upload | South Africa: TymeBank and Capitec have early open-banking APIs; SARS eFiling supports data sharing |
| **Stitch Money integration** | SA-specific account aggregation API | REST webhook; requires OAuth2 consent flow |
| **Pleo / Dext integration** | Business expense receipt capture | Out of scope for pure B2C but useful for sole traders |
| **Google Sheets / Excel export** | Power users want raw data | `pandas.to_excel` / Google Sheets API |

---

### 2.7 Financial Marketplace

| Feature | Value to User | Notes |
|---|---|---|
| **Product recommendations** | "Based on your spending, these credit cards have lower fees" | Affiliate / comparison engine |
| **Insurance comparison** | Compare life, car and home insurance based on spending profile | Integration with a comparison API |
| **Investment suggestions** | ETF or unit trust options matched to savings rate and risk appetite | Requires a risk-profiling questionnaire |
| **Referral / rewards programme** | Users earn points for uploading statements or referring friends | Drives organic growth |

---

### 2.8 Multi-Currency & Multi-Country

| Feature | Value to User | Notes |
|---|---|---|
| **Multi-currency support** | Display amounts in USD, EUR, GBP alongside ZAR | Fixer.io or Open Exchange Rates API for FX rates |
| **African bank expansion** | Add parsers for Kenyan (KCB, Equity), Nigerian (GTB, Zenith) and Ghanaian banks | New parser files following the existing `base.py` interface |
| **VAT / tax-aware categorisation** | Separate VAT-reclaimable business expenses | Requires a business-mode flag per user |

---

### 2.9 Collaboration & Shared Finances

| Feature | Value to User | Notes |
|---|---|---|
| **Household / family accounts** | Aggregate spending across multiple linked users | New `household` relationship table |
| **Shared budget** | Two partners co-manage a joint monthly budget | Budgets linked to household rather than individual user |
| **Financial advisor sharing** | User shares a read-only view with their accountant or advisor | Scoped JWT with `role=viewer` claim |
| **Statement sharing link** | One-time encrypted link to share a single analysis | Signed URL with expiry |

---

### 2.10 Mobile & Accessibility

| Feature | Value to User | Notes |
|---|---|---|
| **Progressive Web App (PWA)** | Installable on Android / iOS home screen | Streamlit does not natively support this; would need a React/Vue frontend |
| **Native mobile app** | Better UX, offline support, biometric login | React Native or Flutter consuming the FastAPI backend |
| **Screen-reader accessibility** | WCAG 2.1 compliance for visually impaired users | ARIA labels, semantic HTML, high-contrast mode |
| **Responsive layout** | Usable on small screens without horizontal scrolling | Streamlit column configuration, CSS overrides |

---

### 2.11 AI-Powered Features

| Feature | Value to User | Notes |
|---|---|---|
| **Natural-language Q&A** | "How much did I spend at Checkers last quarter?" | RAG over transaction history; LLM (OpenAI API or local model) |
| **AI-written financial summary** | Plain-English monthly report generated by an LLM | GPT-4o / Gemini with a structured prompt |
| **Smart category suggestions** | LLM-based fallback for transactions the keyword rules miss | Low-confidence rule results escalated to an LLM classifier |
| **Personalised financial coaching** | Contextual tips based on the user's own spending patterns | LLM prompt injected with health score breakdown and SHAP values |

---

### 2.12 Tax & Compliance Tools

| Feature | Value to User | Notes |
|---|---|---|
| **SARS tax year summary** | Total income, deductible medical expenses, UIF contributions per tax year | Filter by tax year (March–February in South Africa) |
| **Section 18A donation tracking** | Identify qualifying charitable donations from transaction history | Keyword rules for recognised NGOs |
| **ITR12 pre-fill export** | CSV or PDF with prefilled SARS fields | Significant effort; requires knowledge of current ITR12 schema |
| **VAT calculation** | Separate VAT from transaction amounts for freelancers/small businesses | 15 % VAT back-calculation |

---

### 2.13 Integrations

| Feature | Value to User | Notes |
|---|---|---|
| **22seven / Mint-style sync** | Aggregate multiple bank accounts in one view | Requires open-banking or screen-scraping partnerships |
| **Slack / Teams bot** | Daily spending digest or alert in a workspace channel | Webhook + slash command |
| **IFTTT / Zapier** | Let users build their own automation workflows | Webhook endpoint + OAuth app registration |
| **Accounting software export** | QuickBooks, Xero, Sage CSV format | Useful for freelancers/sole traders |

---

### 2.14 Admin & Business Operations

| Feature | Value to User | Notes |
|---|---|---|
| **Admin dashboard** | View aggregate usage stats, flag suspicious accounts | Separate admin role; `is_admin` column on User |
| **User management** | Suspend, delete or anonymise a user account (POPIA erasure right) | `DELETE /admin/users/{id}` |
| **Data export (GDPR/POPIA)** | Download all personal data in a machine-readable format | `GET /auth/export` returns JSON with all statements and budgets |
| **SLA / uptime monitoring** | Track API response times and error rates | Integrate with Prometheus + Grafana or Sentry |
| **Model retraining pipeline** | Retrain the loan eligibility model on real anonymised data | Airflow or GitHub Actions scheduled workflow |
| **A/B testing framework** | Experiment with different ML thresholds or UI flows | Feature flags via LaunchDarkly or a simple `feature_flags` table |

---

*Document generated: 2026-04-14*
