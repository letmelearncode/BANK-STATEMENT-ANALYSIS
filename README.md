# Bank Statement Analysis App

## Overview

This repository contains **two generations** of the same idea:

| Path | Description |
|---|---|
| `ABSA Bank/`, `First National Bank/`, `NedBank/`, `Standard Bank/` | Original single-bank Streamlit apps |
| `Bank-Identifier/` | Original bank-detection prototype |
| **`app/`** | **New unified B2C platform** (FastAPI backend + Streamlit frontend) |

The new `app/` platform is a production-grade B2C system described below.

---

## B2C Platform (`app/`)

### Features

| # | Feature | Details |
|---|---|---|
| 1 | **Unified Bank Support** | Auto-detects ABSA, FNB, Nedbank, Standard Bank, Capitec from uploaded PDF; routes to the correct parser automatically |
| 2 | **User Authentication** | JWT-based register / login with bcrypt passwords and POPIA consent tracking |
| 3 | **Multi-Statement History** | Upload statements from multiple months; dashboard shows month-over-month trends |
| 4 | **Loan Eligibility (ML + SHAP)** | Random Forest model (joblib) with SHAP explainability — users see *why* they are or aren't eligible |
| 5 | **15+ Expense Categories** | Salary, Groceries, Transport, Insurance, Medical, Entertainment, Shopping, Rent & Utilities, and more |
| 6 | **Manual Re-categorisation** | Users can override the auto-assigned category for any transaction |
| 7 | **Financial Health Score** | Composite 0–100 score (grade A–F) based on savings rate, debt-to-income, income stability and expense consistency |
| 8 | **Budgeting Module** | Set monthly spending limits per category; real-time alerts when limits are exceeded |
| 9 | **Capitec Support** | New Capitec parser (separate money-in / money-out columns) |
| 10 | **CSV / OFX / QIF Import** | Import from any bank using standard export formats |
| 11 | **FastAPI Backend** | REST API decoupled from the UI; enables mobile & third-party integrations |
| 12 | **Docker Deployment** | `docker-compose up` starts both services |
| 13 | **Security & Compliance** | Fernet encryption for stored analysis data, audit logging, POPIA consent flow, raw PDFs never stored, rate limiting, file size validation |

---

### Architecture

```
app/
├── backend/                  FastAPI service (port 8000)
│   ├── main.py               API routes (auth, statements, analyses, budgets)
│   ├── auth.py               JWT tokens + bcrypt password hashing
│   ├── database.py           SQLAlchemy models (SQLite / Postgres)
│   ├── schemas.py            Pydantic request / response models
│   ├── parsers/
│   │   ├── bank_identifier.py  Auto-detect bank from PDF text
│   │   ├── absa.py
│   │   ├── fnb.py
│   │   ├── nedbank.py
│   │   ├── standard_bank.py
│   │   ├── capitec.py
│   │   └── csv_import.py       CSV / OFX / QIF
│   ├── ml/
│   │   ├── categorizer.py      15+ category keyword classifier
│   │   ├── loan_eligibility.py RF model + SHAP (joblib)
│   │   └── health_score.py     Financial health score 0-100
│   └── security/
│       ├── encryption.py       Fernet at-rest encryption
│       └── audit.py            Audit log
├── frontend/
│   └── app.py                Streamlit app (port 8501)
├── Dockerfile.backend
├── Dockerfile.frontend
├── docker-compose.yml
└── .env.example
```

### How to Run (Docker — recommended)

```bash
cd app
cp .env.example .env
# Edit .env and set a strong SECRET_KEY

docker compose up --build
```

- Frontend: http://localhost:8501
- Backend API docs: http://localhost:8000/docs

### How to Run (Local development)

**Backend:**
```bash
cd app/backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend (separate terminal):**
```bash
cd app/frontend
pip install -r requirements.txt
BACKEND_URL=http://localhost:8000 streamlit run app.py
```

### API Endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/auth/register` | Create account (requires POPIA consent) |
| POST | `/auth/login` | Get JWT token |
| GET | `/auth/me` | Current user info |
| POST | `/statements/upload` | Upload & analyse PDF / CSV / OFX / QIF |
| GET | `/statements` | List all statements |
| GET | `/statements/{id}` | Get statement + full analysis |
| DELETE | `/statements/{id}` | Delete statement |
| PATCH | `/statements/{id}/transactions/{idx}` | Re-categorise a transaction |
| GET | `/analyses/history` | Month-over-month summary |
| POST | `/budgets` | Set monthly category budget |
| GET | `/budgets` | List budgets |
| GET | `/budgets/alerts` | Categories over budget |

---

## Original Single-Bank Apps (legacy)

## How It Works

1. **PDF Upload**
   - Users upload their bank statement in PDF format using the file uploader interface.

2. **PDF Parsing**
   - The app extracts text from the PDF document using the `pdfplumber` library.

3. **Transaction Processing**
   - Extracted text is processed to identify individual transactions, capturing details such as date, description, amount, and balance.

4. **Expense Categorization**
   - Transactions are categorized based on their descriptions into predefined categories like Payments, Credits, Bank Charges, etc.

5. **Key Metrics Calculation**
   - The app calculates various financial metrics including average daily expense, total expense, maximum and minimum expense, and the number of transactions.

6. **Loan Eligibility Prediction**
   - A Random Forest model is used to predict loan eligibility based on features extracted from transaction data.

7. **Visualizations**
   - The app generates visualizations such as bar charts, pie charts, and line graphs to represent expense distribution and trends.

8. **Hiding Streamlit Components**
   - Customizes the UI by hiding default Streamlit components like the menu and footer for a cleaner look.
     
## Prerequisites

- Python 3.7 or higher
- `pip` (Python package installer)
    
## Usage

1. Launch the app in your browser.
2. Upload a PDF bank statement.
3. Review the extracted transactions and categorized expenses.
4. View key metrics and visualizations.
5. Check loan eligibility based on the analyzed data.

## Dependencies

- `streamlit`: For creating the web application interface.
- `pdfplumber`: For extracting text from PDF files.
- `fitz` (PyMuPDF): For additional PDF processing capabilities, such as extracting images or complex text layouts.
- `re`: For processing text and extracting transaction details.
- `pandas`: For data manipulation and analysis.
- `plotly`: For creating interactive visualizations.
- `sklearn`: For building and using the Random Forest model.

BLOG- https://link.medium.com/aoQxUW4gFMb
