import streamlit as st
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

st.set_page_config(page_title="Fenil's Excellence Hub", layout="wide")

# Pulls the Supabase URL securely from your Streamlit Secrets
conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])

# --- CLOUD-SAFE AUTHENTICATION ---
# Tries Streamlit Cloud Secrets first, falls back to local .env
load_dotenv()
try:
    MASTER_PW = st.secrets["MASTER_PASSWORD"]
except KeyError:
    MASTER_PW = os.getenv("MASTER_PASSWORD")

if "hub_authenticated" not in st.session_state:
    st.session_state.hub_authenticated = False

if not st.session_state.hub_authenticated:
    st.title("🔐 Excellence Hub Login")
    user_input = st.text_input("Master Password", type="password")
    if st.button("Unlock"):
        if user_input == MASTER_PW:
            st.session_state.hub_authenticated = True
            st.rerun()
        else:
            st.error("Access Denied")
    st.stop()

st.title("🚀 The Excellence Hub")
st.write(f"Today's Date: {datetime.now().strftime('%B %d, %Y')}")

# --- MASTER OVERVIEW ---
with st.container(border=True):
    st.subheader("📊 Life Scorecard")
    c1, c2, c3, c4 = st.columns(4)
    
    # 1. Asset Value
    try:
        df_assets = conn.query("SELECT SUM(value) as total FROM assets", ttl=0)
        total_assets = df_assets['total'][0] if not df_assets.empty and pd.notna(df_assets['total'][0]) else 0
        c1.metric("Net Worth", f"${total_assets:,.2f}")
    except: 
        c1.metric("Net Worth", "$0.00")
    
    # 2. Today's Productivity
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        df_prod = conn.query(f"SELECT SUM(duration_mins) as total FROM time_logs WHERE date = '{today}' AND activity = 'Productivity'", ttl=0)
        prod_mins = df_prod['total'][0] if not df_prod.empty and pd.notna(df_prod['total'][0]) else 0
        c2.metric("Productivity Today", f"{int(prod_mins)} min")
    except: 
        c2.metric("Productivity Today", "0 min")

    # 3. Weekly Gym (Using PostgreSQL Syntax)
    try:
        df_gym = conn.query("SELECT SUM(gym) as total FROM fitness WHERE date >= CURRENT_DATE - INTERVAL '7 days'", ttl=0)
        gym_count = df_gym['total'][0] if not df_gym.empty and pd.notna(df_gym['total'][0]) else 0
        c3.metric("Gym (Last 7 Days)", f"{int(gym_count)} sessions")
    except: 
        c3.metric("Gym (Last 7 Days)", "0 sessions")

    # 4. Total Shifts
    try:
        df_shifts = conn.query("SELECT COUNT(*) as total FROM shifts", ttl=0)
        total_shifts = df_shifts['total'][0] if not df_shifts.empty and pd.notna(df_shifts['total'][0]) else 0
        c4.metric("Total Shifts Logged", int(total_shifts))
    except: 
        c4.metric("Total Shifts Logged", "0")

st.divider()

# --- NAVIGATION BUTTONS ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("💰 Finance", use_container_width=True): st.switch_page("pages/1_💰_Finance.py")
with col2:
    if st.button("🏋️‍♂️ Fitness", use_container_width=True): st.switch_page("pages/2_🏋️‍♂️_Fitness.py")
with col3:
    if st.button("⏱️ Time Audit", use_container_width=True): st.switch_page("pages/3_⏱️_Time_Audit.py")
with col4:
    if st.button("🏦 Assets", use_container_width=True): st.switch_page("pages/4_💰_Assets.py")

st.divider()
st.info("Remember Fenil: Small, consistent daily wins lead to the $1,000,000 goal.")
