import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime
from mb_core import (
    get_transactions_df, add_transaction, delete_transaction,
    get_budgets_df, add_budget, delete_budget,
    get_goals_df, add_goal, update_goal_progress, delete_goal,
    summarize_month, month_key
)

# ---------- Page setup ----------
st.set_page_config(page_title="WealthyWays 💸", page_icon="💸", layout="wide")

# ---------- Small CSS polish ----------
st.markdown("""
<style>
.big-metric {
  font-size: 2.2rem;
  font-weight: 800;
}
.kpi-card {
  padding: 1rem 1.2rem;
  border-radius: 1rem;
  box-shadow: 0 1px 10px rgba(0,0,0,0.25);
}
.badge {
  display:inline-block;
  padding:0.2rem 0.6rem;
  border-radius:999px;
  font-size:0.8rem;
  font-weight:700;
}
.badge-red { background:#7f1d1d; color:#fecaca; }
.badge-green { background:#064e3b; color:#bbf7d0; }
.badge-amber { background:#78350f; color:#fde68a; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("💸 WealthyWays")
    st.caption("Personal Budget Tracker")
    st.write(" ")
    st.markdown("> Budgeting has only one rule: **Do not go over budget**")
    st.divider()
    st.write("📁 Download backups")
    colA, colB = st.columns(2)
    with colA:
        if st.button("Transactions CSV"):
            df = get_transactions_df()
            st.download_button("Download", df.to_csv(index=False), "transactions.csv", use_container_width=True)
    with colB:
        if st.button("Budgets CSV"):
            df = get_budgets_df()
            st.download_button("Download", df.to_csv(index=False), "budgets.csv", use_container_width=True)
    st.divider()
    st.caption("Built by Anirudha Pujari.")

# ---------- Tabs ----------
tab_dash, tab_add, tab_budgets, tab_goals, tab_tx = st.tabs(
    ["📊 Dashboard", "➕ Add Transaction", "📦 Budgets", "🎯 Savings Goals", "📜 Transactions"]
)

# ---------- Helpers ----------
DEFAULT_CATS = [
    "Salary","Side Hustle","Food & Drinks","Groceries","Transport","Bills & Utilities",
    "Shopping","Entertainment","Health","Education","Travel","Others"
]

def month_options():
    df = get_transactions_df()
    if df.empty:
        return [month_key()]
    months = sorted({d[:7] for d in df["t_date"]}, reverse=True)
    if not months:
        months = [month_key()]
    return months

# ---------- Dashboard ----------
with tab_dash:
    st.subheader("📊 Dashboard")
    sel_month = st.selectbox("Select month", month_options(), index=0)
    summary = summarize_month(sel_month)

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown('<div class="kpi-card"><div>Income</div><div class="big-metric">₹ {:,.2f}</div></div>'.format(summary["total_income"]), unsafe_allow_html=True)
    with k2:
        st.markdown('<div class="kpi-card"><div>Expense</div><div class="big-metric">₹ {:,.2f}</div></div>'.format(summary["total_expense"]), unsafe_allow_html=True)
    with k3:
        color_badge = "badge-green" if summary["net"]>=0 else "badge-red"
        st.markdown(f'<div class="kpi-card"><div>Net</div><div class="big-metric">₹ {summary["net"]:,.2f}</div><div class="badge {color_badge}">{"Surplus" if summary["net"]>=0 else "Deficit"}</div></div>', unsafe_allow_html=True)

    st.write(" ")

    # Category chart (expenses)
    if isinstance(summary["by_category"], pd.Series) and not summary["by_category"].empty:
        cat_df = summary["by_category"].reset_index()
        cat_df.columns = ["category","spent"]
        st.markdown("### 📦 Spend by Category (Expenses)")
        chart = alt.Chart(cat_df).mark_bar().encode(
            x=alt.X('spent:Q', title='₹ Spent'),
            y=alt.Y('category:N', sort='-x', title='Category'),
            tooltip=['category','spent']
        )
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No expenses for this month yet. Add some transactions!")

    # Budget utilization table + alerts
    st.markdown("### 🧭 Budget Utilization")
    util_df = summary["budget_utilization"]
    if not util_df.empty:
        st.dataframe(util_df, use_container_width=True, hide_index=True)
        # Alerts
        over = util_df[util_df["spent"] > util_df["limit"]]
        warn = util_df[(util_df["spent"] > 0.8*util_df["limit"]) & (util_df["spent"] <= util_df["limit"])]
        if not over.empty:
            st.error(f"🚨 Over budget: {', '.join(over['category'].tolist())}")
        elif not warn.empty:
            st.warning(f"⚠️ Close to limit: {', '.join(warn['category'].tolist())}")
    else:
        st.caption("No budgets set for this month.")

# ---------- Add Transaction ----------
with tab_add:
    st.subheader("➕ Add Transaction")
    col1, col2 = st.columns(2)
    with col1:
        t_date = st.date_input("Date", value=date.today())
        description = st.text_input("Description", placeholder="e.g., Coffee at Starbucks")
        category = st.selectbox("Category", DEFAULT_CATS, index=DEFAULT_CATS.index("Food & Drinks"))
    with col2:
        t_type = st.radio("Type", ["expense","income"], horizontal=True)
        amt = st.number_input("Amount (₹)", step=100.0, value=0.0)

    if st.button("Add", type="primary"):
        if amt == 0:
            st.warning("Amount cannot be zero.")
        else:
            signed_amount = abs(amt) if t_type=="income" else -abs(amt)
            add_transaction(t_date.strftime("%Y-%m-%d"), description, category, signed_amount, t_type)
            st.success("Transaction added ✅")

# ---------- Budgets ----------
with tab_budgets:
    st.subheader("📦 Monthly Budgets")
    month_sel = st.selectbox("Month", month_options(), index=0, key="budget_month")
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        cat_b = st.selectbox("Category", DEFAULT_CATS, index=DEFAULT_CATS.index("Groceries"))
    with bcol2:
        limit_amt = st.number_input("Limit (₹)", step=500.0, value=3000.0)

    if st.button("Add / Update Budget", type="primary"):
        add_budget(month_sel, cat_b, float(limit_amt))
        st.success("Budget saved ✅")

    st.markdown("#### Budgets for this month")
    bdf = get_budgets_df(month_sel)
    st.dataframe(bdf, use_container_width=True, hide_index=True)

    del_id = st.number_input("Delete budget by ID", step=1, value=0)
    if st.button("Delete Budget"):
        if del_id>0:
            delete_budget(int(del_id))
            st.success("Budget deleted ✅")
        else:
            st.warning("Enter a valid ID")

# ---------- Goals ----------
with tab_goals:
    st.subheader("🎯 Savings Goals")
    g1, g2 = st.columns(2)
    with g1:
        gname = st.text_input("Goal name", placeholder="Emergency Fund")
        gtarget = st.number_input("Target Amount (₹)", step=1000.0, value=50000.0)
    with g2:
        gcurrent = st.number_input("Current Saved (₹)", step=500.0, value=0.0)
        gdeadline = st.date_input("Deadline (optional)", value=None)
    if st.button("Add Goal", type="primary"):
        add_goal(gname, float(gtarget), float(gcurrent), gdeadline.strftime("%Y-%m-%d") if gdeadline else None)
        st.success("Goal added ✅")

    st.markdown("#### Your Goals")
    gdf = get_goals_df()
    if gdf.empty:
        st.info("No goals yet. Add one above!")
    else:
        for _, r in gdf.iterrows():
            st.write(f"**{r['name']}**")
            pct = 0 if r['target_amount']==0 else min(100, round(r['current_amount']/r['target_amount']*100,1))
            st.progress(pct/100)
            st.caption(f"₹ {r['current_amount']:,.0f} / ₹ {r['target_amount']:,.0f} ({pct}%)  |  Deadline: {r['deadline'] or '—'}")
            with st.expander("Update / Delete"):
                new_curr = st.number_input(f"Update saved amount (Goal #{int(r['id'])})", value=float(r['current_amount']), step=500.0, key=f"gupd{r['id']}")
                colu1, colu2 = st.columns(2)
                with colu1:
                    if st.button("Update", key=f"upd_btn_{r['id']}"):
                        update_goal_progress(int(r['id']), float(new_curr))
                        st.success("Updated ✅")
                with colu2:
                    if st.button("Delete", key=f"del_goal_{r['id']}"):
                        delete_goal(int(r['id']))
                        st.success("Deleted ✅")

# ---------- Transactions ----------
with tab_tx:
    st.subheader("📜 Transactions")
    msel = st.selectbox("Filter by month", ["All"] + month_options(), index=0)
    df = get_transactions_df(None if msel=="All" else msel)
    if df.empty:
        st.info("No transactions yet.")
    else:
        st.dataframe(df, use_container_width=True)
    st.markdown("#### Delete a transaction")
    rid = st.number_input("Row ID", step=1, value=0)
    if st.button("Delete Transaction"):
        if rid>0:
            delete_transaction(int(rid))
            st.success("Deleted ✅")
        else:
            st.warning("Enter a valid ID")
