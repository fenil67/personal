import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

st.set_page_config(page_title="Fenil's Excellence Hub", layout="wide")
conn = sqlite3.connect('work_data.db', check_same_thread=False)


# Load the .env file
load_dotenv()
MASTER_PW = os.getenv("MASTER_PASSWORD")

if "hub_authenticated" not in st.session_state:
    st.session_state.hub_authenticated = False

if not st.session_state.hub_authenticated:
    st.title("🔐 Excellence Hub Login")
    user_input = st.text_input("Master Password", type="password")
    if st.button("Unlock"):
        if user_input == MASTER_PW: # Checks against .env
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
        total_assets = pd.read_sql_query("SELECT SUM(value) as total FROM assets", conn)['total'][0] or 0
        c1.metric("Net Worth", f"${total_assets:,.2f}")
    except: c1.metric("Net Worth", "$0.00")
    
    # 2. Today's Productivity
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        prod_mins = pd.read_sql_query(f"SELECT SUM(duration_mins) as total FROM time_logs WHERE date = '{today}' AND activity = 'Productivity'", conn)['total'][0] or 0
        c2.metric("Productivity Today", f"{int(prod_mins)} min")
    except: c2.metric("Productivity Today", "0 min")

    # 3. Weekly Gym
    try:
        gym_count = pd.read_sql_query("SELECT SUM(gym) as total FROM fitness WHERE date >= date('now', '-7 days')", conn)['total'][0] or 0
        c3.metric("Gym (Last 7 Days)", f"{int(gym_count)} sessions")
    except: c3.metric("Gym (Last 7 Days)", "0")

    # 4. Total Shifts
    try:
        total_shifts = pd.read_sql_query("SELECT COUNT(*) as total FROM shifts", conn)['total'][0] or 0
        c4.metric("Total Shifts Logged", total_shifts)
    except: c4.metric("Total Shifts Logged", "0")

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