import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
import time
from datetime import datetime, timedelta # Added timedelta here
from streamlit_autorefresh import st_autorefresh

# Hub Security Check
if "hub_authenticated" not in st.session_state or not st.session_state.hub_authenticated:
    st.error("⛔ Access Denied. Unlock the Excellence Hub to view this page.")
    if st.button("Return to Login"):
        st.switch_page("main.py")
    st.stop()# Sidebar Lock Button (Always visible once logged in)
if st.session_state.hub_authenticated:
    if st.sidebar.button("🔒 Lock Entire Hub", use_container_width=True):
        st.session_state.hub_authenticated = False
        st.session_state.asset_authenticated = False # Lock Asset too
        st.rerun()

# 1. Page Config & Auto-Refresh (Updates every 1 second)
st.set_page_config(page_title="Time Audit", layout="wide")
st_autorefresh(interval=1000, key="timer_refresh") 

# --- SELF-SUSTAINING TABLE CHECK ---
def init_time_db():
    conn = sqlite3.connect('work_data.db', check_same_thread=False)
    # Automatically creates the table if it's missing from work_data.db
    conn.execute('''
        CREATE TABLE IF NOT EXISTS time_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            date DATE, 
            activity TEXT, 
            duration_mins REAL, 
            description TEXT
        )
    ''')
    conn.commit()
    return conn

# Initialize the connection
conn = init_time_db()

# --- TIMER STATE ---
if "start_time" not in st.session_state: st.session_state.start_time = None
if "elapsed_time" not in st.session_state: st.session_state.elapsed_time = 0
if "is_running" not in st.session_state: st.session_state.is_running = False
if "show_log_input" not in st.session_state: st.session_state.show_log_input = False

st.title("⏱️ Live Productivity & Time Audit")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚀 Productivity Stopwatch")
    
    # Calculate current time for display
    curr_elapsed = st.session_state.elapsed_time
    if st.session_state.is_running:
        curr_elapsed += (time.time() - st.session_state.start_time)

    # Format into HH:MM:SS
    hours, rem = divmod(int(curr_elapsed), 3600)
    mins, secs = divmod(rem, 60)
    st.code(f"{hours:02d}:{mins:02d}:{secs:02d}", language="txt")

    btn_col1, btn_col2 = st.columns(2)
    
    if not st.session_state.is_running:
        if btn_col1.button("▶️ Start Timer", use_container_width=True):
            st.session_state.start_time = time.time()
            st.session_state.is_running = True
            st.rerun()
    else:
        if btn_col1.button("⏸️ Pause Timer", use_container_width=True):
            st.session_state.elapsed_time += (time.time() - st.session_state.start_time)
            st.session_state.is_running = False
            st.rerun()

    if btn_col2.button("⏹️ Stop & Log", use_container_width=True):
        if st.session_state.is_running:
            st.session_state.elapsed_time += (time.time() - st.session_state.start_time)
        st.session_state.is_running = False
        st.session_state.show_log_input = True
        st.rerun()

    if st.session_state.show_log_input:
        with st.form("prod_log_form"):
            final_mins = round(st.session_state.elapsed_time / 60, 2)
            st.write(f"Logging: **{final_mins} mins**")
            note = st.text_input("What did you work on?")
            if st.form_submit_button("Save to Database"):
                if note:
                    conn.execute("INSERT INTO time_logs (date, activity, duration_mins, description) VALUES (?, ?, ?, ?)",
                                 (datetime.now().strftime('%Y-%m-%d'), "Productivity", final_mins, note))
                    conn.commit()
                    st.session_state.elapsed_time = 0
                    st.session_state.show_log_input = False
                    st.success("Logged!")
                    st.rerun()

with col2:
    st.subheader("📝 Manual Time Log")
    with st.form("manual_entry_form", clear_on_submit=True):
        m_act = st.selectbox("Activity", ["Sleep", "Work", "Gym", "Traveling", "Leisure", "Chores"])
        m_val = st.number_input("Hours", min_value=0.1, step=0.5)
        m_note = st.text_input("Note")
        if st.form_submit_button("Save Manual Log", use_container_width=True):
            conn.execute("INSERT INTO time_logs (date, activity, duration_mins, description) VALUES (?, ?, ?, ?)",
                         (datetime.now().strftime('%Y-%m-%d'), m_act, m_val * 60, m_note))
            conn.commit()
            st.success("Manual log saved!")
            st.rerun()

# --- ADVANCED ANALYTICS ---
st.divider()
df_time = pd.read_sql_query("SELECT * FROM time_logs", conn)

if not df_time.empty:
    # Ensure date is a datetime object for better graphing
    df_time['date'] = pd.to_datetime(df_time['date'])
    
    tab_today, tab_week, tab_month = st.tabs(["🎯 Today", "📅 Weekly Progress", "📊 Monthly Trends"])
    
    with tab_today:
        today = datetime.now().strftime('%Y-%m-%d')
        df_today = df_time[df_time['date'].dt.strftime('%Y-%m-%d') == today]
        
        if not df_today.empty:
            pie_data = df_today.groupby('activity')['duration_mins'].sum().reset_index()
            total_logged = pie_data['duration_mins'].sum()
            unaccounted = max(0, 1440 - total_logged)
            if unaccounted > 0:
                pie_data = pd.concat([pie_data, pd.DataFrame({'activity':['Unaccounted'], 'duration_mins':[unaccounted]})])

            fig = px.pie(pie_data, values='duration_mins', names='activity', 
                         title="24h Distribution", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No data for today yet.")

    with tab_week:
        st.subheader("Last 7 Days Efficiency")
        # Filter for last 7 days
        last_7_days = datetime.now() - timedelta(days=7)
        df_week = df_time[df_time['date'] >= last_7_days]
        
        if not df_week.empty:
            # Group by date and activity to show a stacked bar chart
            week_chart_data = df_week.groupby([df_week['date'].dt.date, 'activity'])['duration_mins'].sum().reset_index()
            
            fig_week = px.bar(week_chart_data, x='date', y='duration_mins', color='activity',
                              title="Daily Time Usage (Minutes)",
                              labels={'duration_mins': 'Minutes Spent', 'date': 'Day'},
                              barmode='stack')
            st.plotly_chart(fig_week, use_container_width=True)
            
            
        else:
            st.write("Not enough data for a weekly view.")

    with tab_month:
        st.subheader("Productivity Trendline")
        # Focus on "Productivity" only to see if you are getting better
        df_prod = df_time[df_time['activity'] == 'Productivity']
        
        if not df_prod.empty:
            # Daily productivity sum
            daily_prod = df_prod.groupby(df_prod['date'].dt.date)['duration_mins'].sum().reset_index()
            
            fig_month = px.line(daily_prod, x='date', y='duration_mins', 
                                title="Daily Productivity Minutes (Last 30 Days)",
                                markers=True, line_shape="spline",
                                color_discrete_sequence=['#00CC96'])
            
            # Add a trend line (average)
            avg_prod = daily_prod['duration_mins'].mean()
            fig_month.add_hline(y=avg_prod, line_dash="dot", line_color="white", 
                                annotation_text=f"Avg: {int(avg_prod)}m")
            
            st.plotly_chart(fig_month, use_container_width=True)
            
            
            
            st.write(f"📈 On average, you spend **{int(avg_prod)} minutes** being productive per day.")
        else:
            st.write("Log more 'Productivity' sessions to see your long-term trend!")


st.sidebar.subheader("Danger Zone")

# Get today's date in the same format as your database (YYYY-MM-DD)
today_date = datetime.now().strftime('%Y-%m-%d')

if st.sidebar.button(f"🗑️ Clear Today's Logs", type="primary", use_container_width=True):
    # This query only targets entries matching today
    conn.execute("DELETE FROM time_logs WHERE date = ?", (today_date,))
    conn.commit()
    st.success(f"Logs for {today_date} cleared!")
    st.rerun()

if st.sidebar.checkbox("Show Advanced: Wipe All"):
    if st.sidebar.button("🚨 Wipe Entire History", type="primary", use_container_width=True):
        conn.execute("DELETE FROM time_logs")
        conn.commit()
        st.success("Entire database wiped!")
        st.rerun()