import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
from tabulate import tabulate
import os
from dotenv import load_dotenv

# Database Connection
conn = sqlite3.connect('work_data.db', check_same_thread=False)

# Ensure Expense Table exists
conn.execute('''CREATE TABLE IF NOT EXISTS expenses 
             (id INTEGER PRIMARY KEY AUTOINCREMENT, date DATE, description TEXT, amount REAL, category TEXT)''')
conn.commit()

def get_data():
    df_s = pd.read_sql_query("SELECT * FROM shifts", conn)
    df_e = pd.read_sql_query("SELECT * FROM expenses", conn)
    df_s['date'] = pd.to_datetime(df_s['date'])
    df_e['date'] = pd.to_datetime(df_e['date'])
    df_s['earnings'] = df_s['hours'] * df_s['pay_rate']
    return df_s, df_e

st.set_page_config(page_title="Finance Tracker Pro", layout="wide")
df_shifts, df_expenses = get_data()

load_dotenv()
ASSET_PIN = os.getenv("ASSET_PIN")

# Hub Check (Ensures main lock is open)
if not st.session_state.get("hub_authenticated"):
    st.warning("Please unlock the Hub first.")
    st.stop()

if "asset_authenticated" not in st.session_state:
    st.session_state.asset_authenticated = False

if not st.session_state.asset_authenticated:
    st.title("🔒 Asset Vault")
    user_pin = st.text_input("Enter Asset PIN", type="password")
    if st.button("Verify"):
        if user_pin == ASSET_PIN: # Checks against .env
            st.session_state.asset_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect PIN")
    st.stop()

# Sidebar Lock Button (Always visible once logged in)
if st.session_state.hub_authenticated:
    if st.sidebar.button("🔒 Lock Entire Hub", use_container_width=True):
        st.session_state.hub_authenticated = False
        st.session_state.asset_authenticated = False # Lock Asset too
        st.rerun()

# --- SIDEBAR METRICS ---
st.sidebar.title("📊 Quick Stats")
if not df_shifts.empty:
    total_earned = df_shifts['earnings'].sum()
    total_spent = df_expenses['amount'].sum() if not df_expenses.empty else 0
    total_hours = df_shifts['hours'].sum()
    st.sidebar.metric("Total Earned", f"${total_earned:,.2f}")
    st.sidebar.metric("Total Spent", f"${total_spent:,.2f}", delta=f"-${total_spent:,.2f}", delta_color="inverse")
    st.sidebar.metric("Net Cash", f"${(total_earned - total_spent):,.2f}")
    st.sidebar.metric("Hours Worked", f"{total_hours:,.2f}")

# --- TABS ---
tab1, tab2, tab3, tab4, tab5= st.tabs(["💰 Shifts", "💸 Expenses", "📈 Analytics", "📊 Data", "📅 Custom Future Month Planner"])

with tab1:
    st.subheader("Log Your Work")
    col1, col2, col3 = st.columns(3)
    d = col1.date_input("Shift Date", datetime.now(), key="shift_d")
    h = col2.number_input("Hours Worked", min_value=0.0, step=0.5)
    r = col3.number_input("Pay Rate", value=14.0)
    if st.button("Save Shift"):
        conn.execute("INSERT INTO shifts (date, hours, pay_rate) VALUES (?,?,?)", (d, h, r))
        conn.commit()
        st.rerun()

with tab2:
    st.subheader("Log an Expense")
    col_e1, col_e2, col_e3 = st.columns(3)
    ed = col_e1.date_input("Expense Date", datetime.now(), key="exp_d")
    desc = col_e2.text_input("What was it for?")
    amt = col_e3.number_input("Amount ($)", min_value=0.0, step=1.0)
    cat = st.selectbox("Category", ["Food", "Rent", "Crypto", "Entertainment", "Transport", "Other"])
    if st.button("Save Expense"):
        conn.execute("INSERT INTO expenses (date, description, amount, category) VALUES (?,?,?,?)", (ed, desc, amt, cat))
        conn.commit()
        st.rerun()

with tab3:
    st.subheader("Financial Breakdown")
    if not df_shifts.empty:
        m_inc = df_shifts.set_index('date').resample('M')['earnings'].sum().reset_index()
        fig_inc = px.bar(m_inc, x='date', y='earnings', title="Monthly Income", color_discrete_sequence=['#00CC96'])
        st.plotly_chart(fig_inc, use_container_width=True)
    
    if not df_expenses.empty:
        fig_exp = px.pie(df_expenses, values='amount', names='category', title="Spending by Category")
        st.plotly_chart(fig_exp, use_container_width=True)
        
with tab4:
    st.header("Income & Expense Ledger")
    
    col_left, col_right = st.columns(2)
    
    with col_left:
        st.subheader("Shift History")
        if not df_shifts.empty:
            # Create a copy and add a total row
            display_shifts = df_shifts[['date', 'hours', 'pay_rate', 'earnings']].copy()
            display_shifts['date'] = display_shifts['date'].dt.strftime('%Y-%m-%d')
            
            # Calculate Total
            total_earnings = display_shifts['earnings'].sum()
            total_hours = display_shifts['hours'].sum()
            
            st.dataframe(display_shifts, use_container_width=True)
            st.info(f"**Total Hours:** {total_hours:.2f} | **Total Income:** ${total_earnings:,.2f}")
        else:
            st.write("No shifts found.")

    with col_right:
        st.subheader("Expense History")
        if not df_expenses.empty:
            # Create a copy and add a total row
            display_exp = df_expenses[['date', 'description', 'amount', 'category']].copy()
            display_exp['date'] = display_exp['date'].dt.strftime('%Y-%m-%d')
            
            # Calculate Total
            total_spent = display_exp['amount'].sum()
            
            st.dataframe(display_exp, use_container_width=True)
            st.error(f"**Total Expenses:** ${total_spent:,.2f}")
        else:
            st.write("No expenses found.")

    # Final Net Calculation
    if not df_shifts.empty and not df_expenses.empty:
        net_total = total_earnings - total_spent
        color = "green" if net_total > 0 else "red"
        st.markdown(f"### Cumulative Net: <span style='color:{color}'>${net_total:,.2f}</span>", unsafe_allow_html=True)

with tab5:
    st.subheader("Manual Growth Projection (Saved to DB)")
    
    # 1. UI for Inputs
    col_p1, col_p2, col_p3, col_p4 = st.columns([2, 2, 2, 1])
    sel_month = col_p1.selectbox("Month", ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], key="sel_m")
    sel_year = col_p2.selectbox("Year", [2025, 2026, 2027, 2028], key="sel_y")
    plan_h = col_p3.number_input("Planned Hours", min_value=0.0, value=160.0, step=10.0, key="plan_h")
    
    if col_p4.button("➕ Save"):
        month_label = f"{sel_month} {sel_year}"
        # Create a sort key (e.g., 202602 for Feb 2026) to keep the graph chronological
        m_num = datetime.strptime(sel_month, "%b").month
        sort_val = (sel_year * 100) + m_num
        
        # Check for duplicates before inserting
        existing = pd.read_sql_query(f"SELECT * FROM projections WHERE month_year = '{month_label}'", conn)
        if existing.empty:
            conn.execute("INSERT INTO projections (month_year, hours, earning, sort_key) VALUES (?, ?, ?, ?)",
                         (month_label, plan_h, plan_h * 14.0, sort_val))
            conn.commit()
            st.rerun()
        else:
            st.warning(f"{month_label} already exists. Delete it below to change it.")

    # 2. Fetch and Display Data
    df_proj_db = pd.read_sql_query("SELECT * FROM projections ORDER BY sort_key ASC", conn)

    if not df_proj_db.empty:
        # Calculate Cumulative Balance
        current_net = (df_shifts['earnings'].sum() if not df_shifts.empty else 0) - \
                      (df_expenses['amount'].sum() if not df_expenses.empty else 0)
        
        df_proj_db['Cumulative Balance'] = df_proj_db['earning'].cumsum() + current_net
        
        # Display Table with Delete Buttons
        st.write("### Your Roadmap")
        for index, row in df_proj_db.iterrows():
            r_col1, r_col2, r_col3, r_col4 = st.columns([2, 2, 2, 1])
            r_col1.write(row['month_year'])
            r_col2.write(f"{row['hours']} hrs")
            r_col3.write(f"${row['earning']:,.2f}")
            if r_col4.button("🗑️", key=f"del_{row['id']}"):
                conn.execute(f"DELETE FROM projections WHERE id = {row['id']}")
                conn.commit()
                st.rerun()

        total_plan_income = df_proj_db['earning'].sum() + current_net
        st.success(f"**Total Planned Income for selected months:** ${total_plan_income:,.2f}")

        # 4. Bulk Actions
        if st.button("🚨 Clear Entire Plan", type="primary"):
            conn.execute("DELETE FROM projections")
            conn.commit()
            st.rerun()
    else:
        st.info("Your plan is empty. Add a month above to start your roadmap.")