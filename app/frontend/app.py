"""Streamlit B2C frontend — calls the FastAPI backend for all data operations.

Pages (managed via st.session_state["page"]):
  - login / register
  - dashboard
  - upload
  - analysis   (single statement detail)
  - history    (multi-statement trends)
  - budgeting  (set limits, view alerts)
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")

# Expense categories — must mirror backend ml/categorizer.py CATEGORY_RULES
EXPENSE_CATEGORIES: List[str] = [
    "Salary",
    "Credits",
    "Rent & Utilities",
    "Groceries",
    "Transport",
    "Insurance",
    "Medical",
    "Entertainment",
    "Shopping",
    "Cellular Expenses",
    "Bank Charges",
    "Payments",
    "Cash Deposits/Withdrawals",
    "Interest and Fees",
    "Unsuccessful Transactions",
    "Education",
    "Savings & Investments",
    "Others",
]

st.set_page_config(
    page_title="Bank Statement Analysis",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session helpers ────────────────────────────────────────────────────────────

def _get(path: str, **kwargs) -> requests.Response:
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.get(f"{BACKEND_URL}{path}", headers=headers, **kwargs)


def _post(path: str, **kwargs) -> requests.Response:
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.post(f"{BACKEND_URL}{path}", headers=headers, **kwargs)


def _delete(path: str, **kwargs) -> requests.Response:
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.delete(f"{BACKEND_URL}{path}", headers=headers, **kwargs)


def _patch(path: str, **kwargs) -> requests.Response:
    token = st.session_state.get("token")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return requests.patch(f"{BACKEND_URL}{path}", headers=headers, **kwargs)


def nav(page: str) -> None:
    st.session_state["page"] = page
    st.rerun()


# ── Sidebar navigation ─────────────────────────────────────────────────────────

def _sidebar() -> None:
    with st.sidebar:
        st.image("https://img.icons8.com/color/96/bank.png", width=60)
        st.markdown("## 🏦 Bank Analyser")
        if st.session_state.get("user"):
            user = st.session_state["user"]
            st.markdown(f"👤 **{user['full_name']}**")
            st.markdown(f"*{user['email']}*")
            st.divider()
            if st.button("📊 Dashboard", use_container_width=True):
                nav("dashboard")
            if st.button("⬆️  Upload Statement", use_container_width=True):
                nav("upload")
            if st.button("📈 History & Trends", use_container_width=True):
                nav("history")
            if st.button("💰 Budgeting", use_container_width=True):
                nav("budgeting")
            st.divider()
            if st.button("🚪 Logout", use_container_width=True):
                for k in ["token", "user", "page", "selected_statement_id"]:
                    st.session_state.pop(k, None)
                nav("login")
        else:
            if st.button("🔑 Login", use_container_width=True):
                nav("login")
            if st.button("📝 Register", use_container_width=True):
                nav("register")


# ── Pages ──────────────────────────────────────────────────────────────────────

def page_login() -> None:
    st.title("🔑 Login")
    col1, col2 = st.columns([1, 1])
    with col1:
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login", type="primary", use_container_width=True):
            resp = requests.post(
                f"{BACKEND_URL}/auth/login",
                data={"username": email, "password": password},
            )
            if resp.status_code == 200:
                token = resp.json()["access_token"]
                st.session_state["token"] = token
                me = _get("/auth/me").json()
                st.session_state["user"] = me
                nav("dashboard")
            else:
                st.error(resp.json().get("detail", "Login failed"))
        st.markdown("Don't have an account? [Register](#)", unsafe_allow_html=False)
        if st.button("Create account"):
            nav("register")


def page_register() -> None:
    st.title("📝 Create Account")
    col1, col2 = st.columns([1, 1])
    with col1:
        full_name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        password2 = st.text_input("Confirm Password", type="password")
        popia = st.checkbox(
            "I consent to the collection and processing of my financial data in accordance "
            "with the Protection of Personal Information Act (POPIA)."
        )
        if st.button("Register", type="primary", use_container_width=True):
            if password != password2:
                st.error("Passwords do not match")
            elif not popia:
                st.error("You must accept POPIA consent to proceed")
            else:
                resp = requests.post(
                    f"{BACKEND_URL}/auth/register",
                    json={
                        "email": email,
                        "full_name": full_name,
                        "password": password,
                        "popia_consent": popia,
                    },
                )
                if resp.status_code == 200:
                    st.success("Account created! Please log in.")
                    nav("login")
                else:
                    st.error(resp.json().get("detail", "Registration failed"))


def _health_gauge(score: int, grade: str) -> go.Figure:
    color = {"A": "#2ecc71", "B": "#27ae60", "C": "#f39c12", "D": "#e67e22", "F": "#e74c3c"}.get(grade, "#95a5a6")
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        title={"text": f"Financial Health  Grade: {grade}"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 35], "color": "#fadbd8"},
                {"range": [35, 50], "color": "#fdebd0"},
                {"range": [50, 65], "color": "#fef9e7"},
                {"range": [65, 80], "color": "#eafaf1"},
                {"range": [80, 100], "color": "#d5f5e3"},
            ],
        },
    ))
    fig.update_layout(height=250, margin=dict(t=40, b=10, l=10, r=10))
    return fig


def page_dashboard() -> None:
    st.title("📊 Dashboard")

    # Recent statements
    resp = _get("/statements")
    if resp.status_code != 200:
        st.error("Could not load statements")
        return
    statements: List[Dict] = resp.json()

    if not statements:
        st.info("No statements yet. Upload your first bank statement to get started.")
        if st.button("⬆️ Upload Statement"):
            nav("upload")
        return

    # Latest analysis
    latest = statements[0]
    detail_resp = _get(f"/statements/{latest['id']}")
    if detail_resp.status_code == 200:
        data = detail_resp.json()
        analysis = data["analysis"]
        metrics = analysis.get("metrics", {})
        hs = analysis.get("health_score", {})
        eligibility = analysis.get("loan_eligibility", {})

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Credits", f"R {metrics.get('total_credits', 0):,.2f}")
        col2.metric("Total Debits", f"R {metrics.get('total_debits', 0):,.2f}")
        col3.metric("Net", f"R {metrics.get('net', 0):,.2f}")
        col4.metric("Transactions", metrics.get("num_transactions", 0))

        st.divider()
        left, right = st.columns([1, 2])
        with left:
            score = hs.get("score", 0)
            grade = hs.get("grade", "F")
            st.plotly_chart(_health_gauge(score, grade), use_container_width=True)
            eligible = eligibility.get("eligible", False)
            proba = eligibility.get("probability", 0)
            if eligible:
                st.success(f"✅ Loan Eligible  (confidence {proba:.0%})")
            else:
                st.error(f"❌ Not Eligible for Loan  (confidence {1-proba:.0%})")

        with right:
            cat_totals = analysis.get("category_totals", {})
            if cat_totals:
                df_cat = (
                    pd.DataFrame(list(cat_totals.items()), columns=["Category", "Amount"])
                    .assign(Amount=lambda d: d["Amount"].abs())
                    .sort_values("Amount", ascending=False)
                    .head(10)
                )
                fig = px.pie(df_cat, values="Amount", names="Category", title="Top Spending Categories")
                st.plotly_chart(fig, use_container_width=True)

    # Statement list
    st.subheader("📂 Your Statements")
    for s in statements:
        c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
        c1.write(s["filename"])
        c2.write(s["bank_name"])
        c3.write(s.get("statement_month", ""))
        with c4:
            if st.button("View", key=f"view_{s['id']}"):
                st.session_state["selected_statement_id"] = s["id"]
                nav("analysis")
            if st.button("🗑", key=f"del_{s['id']}"):
                _delete(f"/statements/{s['id']}")
                st.rerun()


def page_upload() -> None:
    st.title("⬆️ Upload Bank Statement")
    st.info(
        "Supported banks: **ABSA, FNB, Nedbank, Standard Bank, Capitec**  \n"
        "Supported formats: **PDF** (bank statement), **CSV**, **OFX/QFX**, **QIF**"
    )

    uploaded = st.file_uploader(
        "Drag & drop your bank statement here",
        type=["pdf", "csv", "ofx", "qfx", "qif"],
    )

    if uploaded:
        st.write(f"📄 `{uploaded.name}` ({uploaded.size / 1024:.1f} KB)")
        if st.button("Analyse Statement", type="primary"):
            with st.spinner("Analysing your statement …"):
                resp = _post(
                    "/statements/upload",
                    files={"file": (uploaded.name, uploaded.getvalue(), uploaded.type)},
                )
            if resp.status_code == 200:
                data = resp.json()
                st.session_state["selected_statement_id"] = data["statement"]["id"]
                st.success("✅ Analysis complete!")
                nav("analysis")
            else:
                detail = resp.json().get("detail", "Upload failed")
                st.error(f"Error: {detail}")


def _shap_bar(shap_values: List[Dict]) -> Optional[go.Figure]:
    if not shap_values:
        return None
    df = pd.DataFrame(shap_values).head(8)
    df["color"] = df["value"].apply(lambda v: "#2ecc71" if v > 0 else "#e74c3c")
    fig = go.Figure(go.Bar(
        x=df["value"],
        y=df["feature"],
        orientation="h",
        marker_color=df["color"],
        text=df["feature_value"].round(2),
        textposition="outside",
    ))
    fig.update_layout(
        title="Why you are / aren't eligible (SHAP)",
        xaxis_title="Impact on eligibility score",
        height=350,
        margin=dict(l=150, r=10, t=40, b=40),
    )
    return fig


def page_analysis() -> None:
    stmt_id = st.session_state.get("selected_statement_id")
    if not stmt_id:
        st.warning("No statement selected. Please go to Dashboard and click View.")
        return

    resp = _get(f"/statements/{stmt_id}")
    if resp.status_code != 200:
        st.error("Could not load statement")
        return

    data = resp.json()
    stmt = data["statement"]
    analysis = data["analysis"]
    metrics = analysis.get("metrics", {})
    hs = analysis.get("health_score", {})
    eligibility = analysis.get("loan_eligibility", {})
    cat_totals = analysis.get("category_totals", {})
    transactions = analysis.get("transactions", [])

    st.title(f"📑 {stmt['bank_name']} — {stmt.get('statement_month', '')}")
    st.caption(f"Uploaded: {stmt['upload_date'][:10]}  |  File: {stmt['filename']}")
    st.divider()

    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Credits", f"R {metrics.get('total_credits', 0):,.2f}")
    col2.metric("Debits", f"R {metrics.get('total_debits', 0):,.2f}")
    col3.metric("Net", f"R {metrics.get('net', 0):,.2f}")
    col4.metric("Avg Balance", f"R {metrics.get('avg_balance', 0):,.2f}")
    col5.metric("Transactions", metrics.get("num_transactions", 0))

    st.divider()
    left, right = st.columns([1, 2])

    # Health score
    with left:
        st.plotly_chart(_health_gauge(hs.get("score", 0), hs.get("grade", "F")), use_container_width=True)
        breakdown = hs.get("breakdown", {})
        for k, v in breakdown.items():
            pct = v["points"] / v["max"] * 100
            st.markdown(f"**{k.replace('_', ' ').title()}**: {v['label']} — {v['points']}/{v['max']} pts")
            st.progress(int(pct))

    # Loan eligibility
    with right:
        eligible = eligibility.get("eligible", False)
        proba = eligibility.get("probability", 0)
        if eligible:
            st.success(f"✅ **Eligible for Loan**  (probability {proba:.0%})")
        else:
            st.error(f"❌ **Not Eligible for Loan**  (probability {1-proba:.0%})")

        shap_fig = _shap_bar(eligibility.get("shap_values", []))
        if shap_fig:
            st.plotly_chart(shap_fig, use_container_width=True)

    st.divider()

    # Category charts
    if cat_totals:
        df_cat = (
            pd.DataFrame(list(cat_totals.items()), columns=["Category", "Amount"])
            .assign(Amount=lambda d: d["Amount"].abs())
            .sort_values("Amount", ascending=False)
        )
        c1, c2 = st.columns(2)
        with c1:
            fig_bar = px.bar(df_cat, x="Category", y="Amount", title="Spending by Category",
                             color="Category", text_auto=".2s")
            fig_bar.update_xaxes(tickangle=45)
            st.plotly_chart(fig_bar, use_container_width=True)
        with c2:
            fig_pie = px.pie(df_cat, values="Amount", names="Category", title="Expense Distribution")
            st.plotly_chart(fig_pie, use_container_width=True)

    # Daily trend
    if transactions:
        df_tx = pd.DataFrame(transactions)
        df_tx["Date"] = pd.to_datetime(df_tx["Date"])
        fig_line = px.line(df_tx.sort_values("Date"), x="Date", y="Balance", title="Balance Over Time")
        st.plotly_chart(fig_line, use_container_width=True)

        fig_bar2 = px.bar(
            df_tx.sort_values("Date"), x="Date", y="Amount", color="Category",
            title="Transactions by Date",
        )
        st.plotly_chart(fig_bar2, use_container_width=True)

    # Transaction table with re-categorisation
    st.subheader("📋 Transactions")
    if transactions:
        df_tx = pd.DataFrame(transactions)
        df_tx["Date"] = pd.to_datetime(df_tx["Date"]).dt.date

        # Allow user to filter by category
        all_cats = sorted(df_tx["Category"].unique().tolist())
        selected_cats = st.multiselect("Filter by Category", all_cats, default=all_cats)
        df_filtered = df_tx[df_tx["Category"].isin(selected_cats)]

        st.dataframe(df_filtered[["Date", "Description", "Amount", "Balance", "Category"]],
                     use_container_width=True)

        # Re-categorise a transaction
        with st.expander("✏️ Re-categorise a Transaction"):
            category_options = EXPENSE_CATEGORIES
            tx_idx = st.number_input("Transaction Index (0-based)", min_value=0,
                                     max_value=len(transactions) - 1, step=1)
            new_cat = st.selectbox("New Category", category_options)
            if st.button("Update Category"):
                resp2 = _patch(
                    f"/statements/{stmt_id}/transactions/{int(tx_idx)}",
                    data={"new_category": new_cat},
                )
                if resp2.status_code == 200:
                    st.success("Category updated!")
                    st.rerun()
                else:
                    st.error(resp2.json().get("detail", "Update failed"))


def page_history() -> None:
    st.title("📈 History & Trends")

    resp = _get("/analyses/history")
    if resp.status_code != 200:
        st.error("Could not load history")
        return

    summaries: List[Dict] = resp.json()
    if not summaries:
        st.info("Upload multiple monthly statements to see trends.")
        return

    df = pd.DataFrame(summaries)

    # Month-over-month line charts
    fig_credits = px.line(df, x="month", y="total_credits", title="Monthly Credits", markers=True)
    fig_debits = px.line(df, x="month", y="total_debits", title="Monthly Debits", markers=True,
                         color_discrete_sequence=["#e74c3c"])
    fig_net = px.bar(df, x="month", y="net", title="Monthly Net (Credits − Debits)",
                     color="net", color_continuous_scale=["#e74c3c", "#2ecc71"])

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(fig_credits, use_container_width=True)
        st.plotly_chart(fig_debits, use_container_width=True)
    with c2:
        st.plotly_chart(fig_net, use_container_width=True)
        if "health_score" in df.columns and df["health_score"].notna().any():
            fig_hs = px.line(df.dropna(subset=["health_score"]), x="month", y="health_score",
                             title="Financial Health Score Over Time", markers=True,
                             range_y=[0, 100])
            st.plotly_chart(fig_hs, use_container_width=True)

    st.subheader("📋 Summary Table")
    st.dataframe(df.style.format({
        "total_credits": "R {:,.2f}",
        "total_debits": "R {:,.2f}",
        "net": "R {:,.2f}",
    }), use_container_width=True)


def page_budgeting() -> None:
    st.title("💰 Budgeting")

    current_month = datetime.now().strftime("%Y-%m")
    month = st.text_input("Month (YYYY-MM)", value=current_month)

    # Show current budgets
    budgets_resp = _get("/budgets", params={"month": month})
    budgets: List[Dict] = budgets_resp.json() if budgets_resp.status_code == 200 else []

    # Alerts
    alerts_resp = _get("/budgets/alerts", params={"month": month})
    alerts: List[Dict] = alerts_resp.json() if alerts_resp.status_code == 200 else []

    if alerts:
        st.subheader("⚠️ Budget Alerts")
        for a in alerts:
            st.warning(
                f"**{a['category']}** — Spent R {a['spent']:,.2f} / Limit R {a['limit']:,.2f}  "
                f"(over by R {a['over_by']:,.2f})"
            )

    # Set budget
    st.subheader("Set Monthly Limit")
    category_options = EXPENSE_CATEGORIES
    with st.form("budget_form"):
        col1, col2 = st.columns(2)
        with col1:
            cat = st.selectbox("Category", category_options)
        with col2:
            limit = st.number_input("Monthly Limit (R)", min_value=0.0, step=100.0)
        if st.form_submit_button("Save Budget"):
            resp = _post("/budgets", json={"category": cat, "monthly_limit": limit, "month": month})
            if resp.status_code == 200:
                st.success(f"Budget set: R {limit:,.2f} for {cat} in {month}")
                st.rerun()
            else:
                st.error(resp.json().get("detail", "Failed to save budget"))

    # Current budgets table
    if budgets:
        st.subheader(f"📋 Budgets for {month}")
        df_b = pd.DataFrame(budgets)[["category", "monthly_limit"]]
        df_b.columns = ["Category", "Limit (R)"]
        st.dataframe(df_b, use_container_width=True)

        # Progress bars vs actuals from latest statement
        st.subheader("Budget vs Actual")
        stmts_resp = _get("/statements")
        stmts = stmts_resp.json() if stmts_resp.status_code == 200 else []
        stmt_for_month = next((s for s in stmts if s.get("statement_month") == month), None)
        if stmt_for_month:
            detail = _get(f"/statements/{stmt_for_month['id']}").json()
            cat_totals = detail.get("analysis", {}).get("category_totals", {})
            for b in budgets:
                spent = abs(cat_totals.get(b["category"], 0.0))
                limit_val = b["monthly_limit"]
                pct = min(int(spent / limit_val * 100), 100) if limit_val > 0 else 0
                color = "🔴" if spent > limit_val else ("🟡" if pct > 75 else "🟢")
                st.markdown(f"{color} **{b['category']}** — R {spent:,.2f} / R {limit_val:,.2f}")
                st.progress(pct)
        else:
            st.info(f"No statement uploaded for {month} yet.")


# ── Router ─────────────────────────────────────────────────────────────────────

def main() -> None:
    # Defaults
    if "page" not in st.session_state:
        st.session_state["page"] = "login"

    _sidebar()

    page = st.session_state.get("page", "login")

    # Require auth for protected pages
    protected = {"dashboard", "upload", "analysis", "history", "budgeting"}
    if page in protected and not st.session_state.get("token"):
        page = "login"
        st.session_state["page"] = "login"

    pages = {
        "login": page_login,
        "register": page_register,
        "dashboard": page_dashboard,
        "upload": page_upload,
        "analysis": page_analysis,
        "history": page_history,
        "budgeting": page_budgeting,
    }
    pages.get(page, page_login)()


if __name__ == "__main__":
    main()
