import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
from dotenv import load_dotenv
from sqlalchemy import text

st.set_page_config(page_title="Asset Manager", layout="wide")
conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])

def sync_cash_from_finance():
    """Calculates live cash from Finance tables using pandas and updates Assets."""
    try:
        df_shifts = conn.query("SELECT * FROM shifts", ttl=0)
        total_income = 0.0
        if not df_shifts.empty:
            if 'pay_rate' in df_shifts.columns:
                total_income = (df_shifts['hours'] * df_shifts['pay_rate']).sum()
            else:
                total_income = (df_shifts['hours'] * 14.0).sum()

        df_exp = conn.query("SELECT amount FROM expenses", ttl=0)
        total_expenses = df_exp['amount'].sum() if not df_exp.empty else 0.0
        
        live_cash = total_income - total_expenses
        
        with conn.session as s:
            s.execute(text("DELETE FROM assets WHERE name = 'Cash (Live)'"))
            s.execute(text("INSERT INTO assets (name, category, value, last_updated) VALUES (:n, :c, :v, :d)"), 
                      {"n": "Cash (Live)", "c": "Cash", "v": live_cash, "d": datetime.now().strftime('%Y-%m-%d')})
            s.commit()
    except Exception as e:
        st.error(f"Sync Error: {e}")

sync_cash_from_finance()

load_dotenv()
ASSET_PIN = os.getenv("ASSET_PIN")

if not st.session_state.get("hub_authenticated"):
    st.warning("Please unlock the Hub first.")
    st.stop()

if "asset_authenticated" not in st.session_state:
    st.session_state.asset_authenticated = False

if not st.session_state.asset_authenticated:
    st.title("🔒 Asset Vault")
    user_pin = st.text_input("Enter Asset PIN", type="password")
    if st.button("Verify"):
        if user_pin == ASSET_PIN:
            st.session_state.asset_authenticated = True
            st.rerun()
        else:
            st.error("Incorrect PIN")
    st.stop()

if st.session_state.hub_authenticated:
    if st.sidebar.button("🔒 Lock Entire Hub", use_container_width=True):
        st.session_state.hub_authenticated = False
        st.session_state.asset_authenticated = False
        st.rerun()

st.title("🏦 Asset & Investment Portfolio")

with st.expander("➕ Add / Update Asset", expanded=False):
    with st.form("asset_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        a_name = col1.text_input("Asset Name", placeholder="e.g., BTC, Apple Stock, Savings")
        a_cat = col2.selectbox("Category", ["Crypto", "Stocks", "Cash", "Real Estate", "Gold", "Other"])
        a_val = col3.number_input("Current Value ($)", min_value=0.0, step=100.0)
        
        submit = st.form_submit_button("Save Asset")
        if submit and a_name:
            with conn.session as s:
                s.execute(text("DELETE FROM assets WHERE name = :n"), {"n": a_name})
                s.execute(text("INSERT INTO assets (name, category, value, last_updated) VALUES (:n, :c, :v, :d)"), 
                          {"n": a_name, "c": a_cat, "v": a_val, "d": datetime.now().strftime('%Y-%m-%d')})
                s.commit()
            st.success(f"Updated {a_name}!")
            st.rerun()

try:
    df_assets = conn.query("SELECT * FROM assets", ttl=0)

    if not df_assets.empty:
        total_assets = df_assets['value'].sum()
        st.sidebar.title("💳 Portfolio Stats")
        st.sidebar.metric("Total Net Worth", f"${total_assets:,.2f}")
        
        st.sidebar.write("---")
        st.sidebar.subheader("🔝 Top 3 Holdings")
        top_3 = df_assets.nlargest(3, 'value')
        for _, row in top_3.iterrows():
            st.sidebar.write(f"**{row['name']}**: ${row['value']:,.2f}")

        col_chart, col_table = st.columns([3, 2])

        with col_chart:
            st.subheader("Portfolio Distribution")
            fig = px.pie(df_assets, values='value', names='category', 
                         hole=0.5, title="Asset Allocation",
                         color_discrete_sequence=px.colors.qualitative.Bold)
            st.plotly_chart(fig, use_container_width=True)

        with col_table:
            st.subheader("Holdings Detail")
            for index, row in df_assets.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 2, 1])
                    c1.write(f"**{row['name']}** ({row['category']})")
                    c2.write(f"${row['value']:,.2f}")
                    if c3.button("🗑️", key=f"del_{row['name']}"):
                        with conn.session as s:
                            s.execute(text("DELETE FROM assets WHERE name = :n"), {"n": row['name']})
                            s.commit()
                        st.rerun()

        st.divider()
        target = 1000000
        progress = (total_assets / target)
        st.subheader(f"Progress to $1M Goal: {progress*100:.2f}%")
        st.progress(min(progress, 1.0))
        st.write(f"You need **${(target - total_assets):,.2f}** more to hit your July 2028 target.")

    else:
        st.info("Your portfolio is empty. Add your first asset (Cash, Crypto, etc.) above!")
except Exception as e:
    st.info("Loading assets table. Please wait.")
