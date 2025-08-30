import sqlite3
import pandas as pd
from datetime import datetime, date

DB_PATH = "moneybuddy.db"

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        t_date TEXT NOT NULL,           -- YYYY-MM-DD
        description TEXT,
        category TEXT NOT NULL,
        amount REAL NOT NULL,           -- positive for income, negative for expense
        t_type TEXT CHECK(t_type IN ('income','expense')) NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS budgets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        month TEXT NOT NULL,            -- YYYY-MM
        category TEXT NOT NULL,
        limit_amount REAL NOT NULL
    );
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS savings_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        target_amount REAL NOT NULL,
        current_amount REAL NOT NULL DEFAULT 0,
        deadline TEXT                   -- YYYY-MM-DD
    );
    """)
    con.commit()
    con.close()

def add_transaction(t_date, description, category, amount, t_type):
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO transactions (t_date, description, category, amount, t_type)
        VALUES (?, ?, ?, ?, ?)
    """, (t_date, description, category, amount, t_type))
    con.commit()
    con.close()

def get_transactions_df(month_filter=None):
    con = get_conn()
    q = "SELECT * FROM transactions ORDER BY date(t_date) DESC, id DESC"
    df = pd.read_sql(q, con)
    con.close()
    if month_filter:
        df = df[df["t_date"].str.startswith(month_filter)]
    return df

def delete_transaction(row_id:int):
    con = get_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM transactions WHERE id = ?", (row_id,))
    con.commit()
    con.close()

def add_budget(month, category, limit_amount):
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO budgets (month, category, limit_amount)
        VALUES (?, ?, ?)
    """, (month, category, limit_amount))
    con.commit()
    con.close()

def get_budgets_df(month=None):
    con = get_conn()
    q = "SELECT * FROM budgets ORDER BY month DESC, category ASC"
    df = pd.read_sql(q, con)
    con.close()
    if month:
        df = df[df["month"] == month]
    return df

def delete_budget(row_id:int):
    con = get_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM budgets WHERE id = ?", (row_id,))
    con.commit()
    con.close()

def add_goal(name, target, current=0.0, deadline=None):
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        INSERT INTO savings_goals (name, target_amount, current_amount, deadline)
        VALUES (?, ?, ?, ?)
    """, (name, target, current, deadline))
    con.commit()
    con.close()

def update_goal_progress(goal_id, new_current):
    con = get_conn()
    cur = con.cursor()
    cur.execute("""
        UPDATE savings_goals
        SET current_amount = ?
        WHERE id = ?
    """, (new_current, goal_id))
    con.commit()
    con.close()

def delete_goal(row_id:int):
    con = get_conn()
    cur = con.cursor()
    cur.execute("DELETE FROM savings_goals WHERE id = ?", (row_id,))
    con.commit()
    con.close()

def get_goals_df():
    con = get_conn()
    df = pd.read_sql("SELECT * FROM savings_goals ORDER BY id DESC", con)
    con.close()
    return df

def month_key(dt=None):
    dt = dt or date.today()
    return dt.strftime("%Y-%m")

def summarize_month(month=None):
    """Returns dict with totals, by-category, and budget utilization."""
    month = month or month_key()
    tx = get_transactions_df(month)
    total_income = tx.loc[tx["t_type"]=="income", "amount"].sum() if not tx.empty else 0.0
    total_expense = -tx.loc[tx["t_type"]=="expense", "amount"].sum() if not tx.empty else 0.0  # make positive
    net = total_income - total_expense

    # By category (expenses only)
    cat = tx[tx["t_type"]=="expense"].copy()
    by_cat = cat.groupby("category")["amount"].sum().abs().sort_values(ascending=False) if not cat.empty else pd.Series(dtype=float)

    # Budget utilization
    budgets = get_budgets_df(month)
    util_rows = []
    for _, b in budgets.iterrows():
        spent = by_cat.get(b["category"], 0.0)
        limit_amt = float(b["limit_amount"])
        pct = (spent/limit_amt * 100) if limit_amt>0 else 0
        util_rows.append({
            "category": b["category"],
            "limit": limit_amt,
            "spent": spent,
            "remaining": max(0.0, limit_amt - spent),
            "utilization_%": round(pct, 1)
        })
    util_df = pd.DataFrame(util_rows)

    return {
        "month": month,
        "total_income": round(float(total_income),2),
        "total_expense": round(float(total_expense),2),
        "net": round(float(net),2),
        "by_category": by_cat,
        "budget_utilization": util_df
    }

# auto-init on import
init_db()
