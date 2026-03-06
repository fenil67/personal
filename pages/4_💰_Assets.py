import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from dotenv import load_dotenv

st.set_page_config(page_title="Asset Manager", layout="wide")

# --- SELF-SUSTAINING TABLE CHECK ---
def init_asset_db():
    conn = sqlite3.connect('work_data.db', check_same_thread=False)
    # This command checks if the table exists; if not, it creates it.
    conn.execute('''
        CREATE TABLE IF NOT EXISTS assets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            name TEXT UNIQUE, 
            category TEXT, 
            value REAL, 
            last_updated DATE
        )
    ''')
    conn.commit()
    return conn

# Initialize connection
conn = init_asset_db()


# --- AUTO-SYNC CASH BALANCE PATCH ---
def sync_cash_from_finance():
    """Calculates live cash from Finance tables and updates Assets."""
    try:
        cur = conn.cursor()
        
        # FIX 1: Calculate Income directly (Hours x Rate) instead of looking for an 'earnings' column
        # If your column is named 'rate' instead of 'pay_rate', change it below.
        try:
            cur.execute("SELECT SUM(hours * pay_rate) FROM shifts")
            total_income = cur.fetchone()[0]
        except sqlite3.OperationalError:
            # Fallback: If you don't have a 'pay_rate' column, assume your standard $14/hr
            cur.execute("SELECT SUM(hours * 14) FROM shifts")
            total_income = cur.fetchone()[0]

        if total_income is None: total_income = 0.0
        
        # 2. Get Total Expenses
        cur.execute("SELECT SUM(amount) FROM expenses")
        result = cur.fetchone()[0]
        total_expenses = result if result else 0.0
        
        # 3. Calculate Real Cash on Hand
        live_cash = total_income - total_expenses
        
        # 4. Update the 'Cash (Live)' asset automatically
        conn.execute('''INSERT OR REPLACE INTO assets (name, category, value, last_updated) 
                        VALUES (?, ?, ?, ?)''', 
                        ('Cash (Live)', 'Cash', live_cash, datetime.now().strftime('%Y-%m-%d')))
        conn.commit()
        
    except Exception as e:
        st.error(f"Sync Error: {e}")

# Run the sync every time the page loads
sync_cash_from_finance()

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

st.title("🏦 Asset & Investment Portfolio")

# --- ASSET INPUT/EDIT SECTION ---
with st.expander("➕ Add / Update Asset", expanded=False):
    with st.form("asset_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        a_name = col1.text_input("Asset Name", placeholder="e.g., BTC, Apple Stock, Savings")
        a_cat = col2.selectbox("Category", ["Crypto", "Stocks", "Cash", "Real Estate", "Gold", "Other"])
        a_val = col3.number_input("Current Value ($)", min_value=0.0, step=100.0)
        
        submit = st.form_submit_button("Save Asset")
        if submit and a_name:
            conn.execute('''INSERT OR REPLACE INTO assets (name, category, value, last_updated) 
                         VALUES (?, ?, ?, ?)''', (a_name, a_cat, a_val, datetime.now().strftime('%Y-%m-%d')))
            conn.commit()
            st.success(f"Updated {a_name}!")
            st.rerun()

# --- DATA PROCESSING ---
df_assets = pd.read_sql_query("SELECT * FROM assets", conn)

if not df_assets.empty:
    # --- SIDEBAR QUICK STATS ---
    total_assets = df_assets['value'].sum()
    st.sidebar.title("💳 Portfolio Stats")
    st.sidebar.metric("Total Net Worth", f"${total_assets:,.2f}")
    
    st.sidebar.write("---")
    st.sidebar.subheader("🔝 Top 3 Holdings")
    top_3 = df_assets.nlargest(3, 'value')
    for _, row in top_3.iterrows():
        st.sidebar.write(f"**{row['name']}**: ${row['value']:,.2f}")

    # --- MAIN DASHBOARD ---
    col_chart, col_table = st.columns([3, 2])

    with col_chart:
        st.subheader("Portfolio Distribution")
        fig = px.pie(df_assets, values='value', names='category', 
                     hole=0.5, title="Asset Allocation",
                     color_discrete_sequence=px.colors.qualitative.Bold)
        st.plotly_chart(fig, use_container_width=True)
        

    with col_table:
        st.subheader("Holdings Detail")
        # Display table with option to delete
        for index, row in df_assets.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 1])
                c1.write(f"**{row['name']}** ({row['category']})")
                c2.write(f"${row['value']:,.2f}")
                if c3.button("🗑️", key=f"del_{row['id']}"):
                    conn.execute(f"DELETE FROM assets WHERE id = {row['id']}")
                    conn.commit()
                    st.rerun()

    # --- ASSET VS GOAL ---
    st.divider()
    target = 1000000
    progress = (total_assets / target)
    st.subheader(f"Progress to $1M Goal: {progress*100:.2f}%")
    st.progress(min(progress, 1.0))
    st.write(f"You need **${(target - total_assets):,.2f}** more to hit your July 2028 target.")

else:
    st.info("Your portfolio is empty. Add your first asset (Cash, Crypto, etc.) above!")