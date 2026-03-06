import streamlit as st
import pandas as pd
import plotly.express as px
import time
from datetime import datetime, timedelta 
from streamlit_autorefresh import st_autorefresh
from sqlalchemy import text

if "hub_authenticated" not in st.session_state or not st.session_state.hub_authenticated:
    st.error("⛔ Access Denied. Unlock the Excellence Hub to view this page.")
    if st.button("Return to Login"):
        st.switch_page("main.py")
    st.stop()
    
if st.session_state.hub_authenticated:
    if st.sidebar.button("🔒 Lock Entire Hub", use_container_width=True):
        st.session_state.hub_authenticated = False
        st.session_state.asset_authenticated = False 
        st.rerun()

st.set_page_config(page_title="Time Audit", layout="wide")
st_autorefresh(interval=1000, key="timer_refresh") 

conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])    

if "start_time" not in st.session_state: st.session_state.start_time = None
if "elapsed_time" not in st.session_state: st.session_state.elapsed_time = 0
if "is_running" not in st.session_state: st.session_state.is_running = False
if "show_log_input" not in st.session_state: st.session_state.show_log_input = False

st.title("⏱️ Live Productivity & Time Audit")

col1, col2 = st.columns(2)

with col1:
    st.subheader("🚀 Productivity Stopwatch")
    
    curr_elapsed = st.session_state.elapsed_time
    if st.session_state.is_running:
        curr_elapsed += (time.time() - st.session_state.start_time)

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
                    with conn.session as s:
                        s.execute(text("INSERT INTO time_logs (date, activity, duration_mins, description) VALUES (:d, :a, :dur, :desc)"),
                                     {"d": datetime.now().strftime('%Y-%m-%d'), "a": "Productivity", "dur": final_mins, "desc": note})
                        s.commit()
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
            with conn.session as s:
                s.execute(text("INSERT INTO time_logs (date, activity, duration_mins, description) VALUES (:d, :a, :dur, :desc)"),
                             {"d": datetime.now().strftime('%Y-%m-%d'), "a": m_act, "dur": m_val * 60, "desc": m_note})
                s.commit()
            st.success("Manual log saved!")
            st.rerun()

st.divider()
try:
    df_time = conn.query("SELECT * FROM time_logs", ttl=0)

    if not df_time.empty:
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
            last_7_days = pd.to_datetime(datetime.now()) - timedelta(days=7)
            df_week = df_time[df_time['date'] >= last_7_days]
            
            if not df_week.empty:
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
            df_prod = df_time[df_time['activity'] == 'Productivity']
            
            if not df_prod.empty:
                daily_prod = df_prod.groupby(df_prod['date'].dt.date)['duration_mins'].sum().reset_index()
                fig_month = px.line(daily_prod, x='date', y='duration_mins', 
                                    title="Daily Productivity Minutes (Last 30 Days)",
                                    markers=True, line_shape="spline",
                                    color_discrete_sequence=['#00CC96'])
                
                avg_prod = daily_prod['duration_mins'].mean()
                fig_month.add_hline(y=avg_prod, line_dash="dot", line_color="white", 
                                    annotation_text=f"Avg: {int(avg_prod)}m")
                st.plotly_chart(fig_month, use_container_width=True)
                st.write(f"📈 On average, you spend **{int(avg_prod)} minutes** being productive per day.")
            else:
                st.write("Log more 'Productivity' sessions to see your long-term trend!")
except Exception as e:
    st.info("Database syncing. Check logs soon.")

st.sidebar.subheader("Danger Zone")
today_date = datetime.now().strftime('%Y-%m-%d')

if st.sidebar.button(f"🗑️ Clear Today's Logs", type="primary", use_container_width=True):
    with conn.session as s:
        s.execute(text("DELETE FROM time_logs WHERE date = :d"), {"d": today_date})
        s.commit()
    st.success(f"Logs for {today_date} cleared!")
    st.rerun()

if st.sidebar.checkbox("Show Advanced: Wipe All"):
    if st.sidebar.button("🚨 Wipe Entire History", type="primary", use_container_width=True):
        with conn.session as s:
            s.execute(text("DELETE FROM time_logs"))
            s.commit()
        st.success("Entire database wiped!")
        st.rerun()
