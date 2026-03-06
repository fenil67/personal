import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# Hub Security Check
if "hub_authenticated" not in st.session_state or not st.session_state.hub_authenticated:
    st.error("⛔ Access Denied. Unlock the Excellence Hub to view this page.")
    if st.button("Return to Login"):
        st.switch_page("main.py")
    st.stop()

# Sidebar Lock Button (Always visible once logged in)
if st.session_state.hub_authenticated:
    if st.sidebar.button("🔒 Lock Entire Hub", use_container_width=True):
        st.session_state.hub_authenticated = False
        st.session_state.asset_authenticated = False # Lock Asset too
        st.rerun()

st.set_page_config(page_title="Fitness Tracker", layout="wide")

# Database Connection
# Pulls the Supabase URL securely from your Streamlit Secrets
conn = st.connection("postgresql", type="sql", url=st.secrets["DATABASE_URL"])
# Ensure the fitness table exists with the right columns
# conn.execute('''CREATE TABLE IF NOT EXISTS fitness 
#              (date DATE PRIMARY KEY, water INTEGER, steps INTEGER, gym INTEGER, sleep INTEGER)''')
# conn.commit()

# --- DATA HELPERS ---
def get_fitness_data():
    df = pd.read_sql_query("SELECT * FROM fitness", conn)
    if not df.empty:
        df['date'] = pd.to_datetime(df['date'])
    return df

today_str = datetime.now().strftime('%Y-%m-%d')
df_fit = get_fitness_data()

# --- SIDEBAR LOGIC (AUTO-UPDATING) ---
st.sidebar.title("🏆 Consistency Hub")
if not df_fit.empty:
    recent_7 = df_fit[df_fit['date'] > (datetime.now() - timedelta(days=7))]
    if not recent_7.empty:
        avg_score = recent_7[['water', 'steps', 'gym', 'sleep']].sum(axis=1).mean()
        if avg_score >= 3.5: grade, color = "S (Elite)", "#00FF00"
        elif avg_score >= 2.5: grade, color = "B (Solid)", "#FFFF00"
        else: grade, color = "D (Weak)", "#FF4B4B"
        
        st.sidebar.markdown(f"### Grade: <span style='color:{color}'>{grade}</span>", unsafe_allow_html=True)
        st.sidebar.progress(avg_score / 4.0)
        st.sidebar.write(f"Weekly Power: {int((avg_score/4)*100)}%")

# --- MAIN INTERFACE ---
st.title("🏋️‍♂️ Elite Consistency Tracker")

# 1. THE DAILY LOG SECTION
with st.container(border=True):
    st.subheader(f"Log for {today_str}")
    
    # Check if data for today already exists to pre-fill checkboxes
    cursor = conn.cursor()
    cursor.execute("SELECT water, steps, gym, sleep FROM fitness WHERE date = ?", (today_str,))
    today_data = cursor.fetchone()
    
    # Default values (0 if no entry, else use DB value)
    v_water, v_steps, v_gym, v_sleep = (0, 0, 0, 0) if not today_data else today_data

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        water_check = st.checkbox("💧 3L Water", value=bool(v_water), key="w_check")
    with col2:
        steps_check = st.checkbox("👟 10k Steps", value=bool(v_steps), key="s_check")
    with col3:
        gym_check = st.checkbox("💪 Gym Day", value=bool(v_gym), key="g_check")
    with col4:
        sleep_check = st.checkbox("😴 7h+ Sleep", value=bool(v_sleep), key="sl_check")

    if st.button("🔥 Log Progress", use_container_width=True):
        conn.execute('''INSERT OR REPLACE INTO fitness (date, water, steps, gym, sleep) 
                     VALUES (?, ?, ?, ?, ?)''', 
                     (today_str, int(water_check), int(steps_check), int(gym_check), int(sleep_check)))
        conn.commit()
        st.balloons()
        st.success("Entry Saved!")
        st.rerun()

# 2. THE ANALYTICS SECTION
st.divider()
if not df_fit.empty:
    t1, t2 = st.tabs(["📊 Performance Graphs", "📋 Full History"])
    
    with t1:
        c_left, c_right = st.columns(2)
        
        with c_left:
            st.write("### Habit Balance")
            # Create data for the pie chart
            totals = df_fit[['water', 'steps', 'gym', 'sleep']].sum()
            fig_pie = px.pie(values=totals.values, names=totals.index, 
                             title="Habit Distribution (All Time)", hole=0.4)
            st.plotly_chart(fig_pie, use_container_width=True)
            

        with c_right:
            st.write("### Consistency Score")
            df_fit['DailyScore'] = df_fit[['water', 'steps', 'gym', 'sleep']].sum(axis=1)
            fig_line = px.line(df_fit, x='date', y='DailyScore', title="Score Trend", markers=True)
            fig_line.update_yaxes(range=[0, 4.5])
            st.plotly_chart(fig_line, use_container_width=True)
            

    with t2:
        st.write("### All Logged Days")
        # Format the table for readability
        display_df = df_fit.copy()
        for col in ['water', 'steps', 'gym', 'sleep']:
            display_df[col] = display_df[col].apply(lambda x: "✅" if x == 1 else "❌")
        st.dataframe(display_df.sort_values('date', ascending=False), use_container_width=True)

else:
    st.info("No data yet. Check the boxes above and hit 'Log Progress' to start!")
