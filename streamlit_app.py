"""
AI Business & Attendance Analytics Studio (Streamlit Version)
============================================================
A state-of-the-art Streamlit interface featuring:
- AI Analytics Chatbot Studio
- Real-Time Face Recognition & Camera Stream
- Student Directory & Dataset Collector
- Attendance Logs & Visual Analytics Dashboard
"""

import os
import cv2
import pandas as pd
import numpy as np
from PIL import Image
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

import config
import database
import analytics_engine
from face_engine import engine

# -----------------------------------------------------------------------------
# Streamlit Page Config & Custom Styling
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Business Analytics Studio",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark glassmorphism studio theme CSS
st.markdown("""
    <style>
        .stApp {
            background-color: #0b0f19;
            color: #f8fafc;
        }
        .css-1d38152, [data-testid="stSidebar"] {
            background-color: #0f172a !important;
            border-right: 1px solid #1e293b;
        }
        .stButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }
        .metric-card {
            background: rgba(30, 41, 59, 0.6);
            border: 1px solid #1e293b;
            border-radius: 12px;
            padding: 18px;
            text-align: center;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        }
        .metric-value {
            font-size: 28px;
            font-weight: 800;
            color: #38bdf8;
        }
        .metric-label {
            font-size: 13px;
            color: #94a3b8;
            font-weight: 600;
            text-transform: uppercase;
        }
        .chip-btn {
            background: rgba(99, 102, 241, 0.15) !important;
            border: 1px solid rgba(99, 102, 241, 0.3) !important;
            color: #a5b4fc !important;
            border-radius: 20px !important;
            padding: 4px 12px !important;
            font-size: 12px !important;
        }
    </style>
""", unsafe_allow_html=True)

# Initialize DB and Engine
database.init_db()
if not engine.is_trained:
    engine.load_model()

# -----------------------------------------------------------------------------
# Sidebar Navigation
# -----------------------------------------------------------------------------
st.sidebar.title("🧠 VisionAnalytics")
st.sidebar.caption("AI Face Recognition & Business Studio")

menu_option = st.sidebar.radio(
    "Navigation Menu",
    [
        "💬 AI Chat Studio",
        "📹 Live Scanner",
        "👥 Student Directory",
        "📊 Attendance Logs & Analytics"
    ],
    index=0
)

# System Status Card in Sidebar
st.sidebar.markdown("---")
stats_data = database.get_stats()
st.sidebar.markdown("### ⚡ System Status")
status_color = "🟢 Ready & Trained" if engine.is_trained else "🟠 Model Untrained"
st.sidebar.write(f"**Model Status:** {status_color}")
st.sidebar.write(f"**Enrolled Students:** `{stats_data['total_students']}`")
st.sidebar.write(f"**Present Today:** `{stats_data['present_today']}`")

# -----------------------------------------------------------------------------
# Page 1: 💬 AI Chat Studio
# -----------------------------------------------------------------------------
if menu_option == "💬 AI Chat Studio":
    st.title("💬 AI Business & Attendance Analytics Studio")
    st.caption("Ask natural language questions to analyze student attendance, department metrics, absent lists, and 7-day velocity.")

    # Top Metric Banner
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Enrolled</div><div class="metric-value">{stats_data["total_students"]}</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Present Today</div><div class="metric-value" style="color:#10b981">{stats_data["present_today"]}</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Absent Today</div><div class="metric-value" style="color:#ef4444">{stats_data["absent_today"]}</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="metric-card"><div class="metric-label">Total Scans</div><div class="metric-value" style="color:#6366f1">{stats_data["total_logs"]}</div></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Session State for Chat History
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "👋 **Hello! I'm your AI Business Analytics Assistant.** Ask me about today's attendance summary, department breakdowns, absent lists, or 7-day trends!",
                "chart": {
                    "type": "pie",
                    "title": "Today's Attendance Status",
                    "labels": ["Present Today", "Absent Today"],
                    "values": [stats_data["present_today"], stats_data["absent_today"]],
                    "colors": ["#10b981", "#ef4444"]
                }
            }
        ]

    # Quick Suggestion Prompt Chips
    st.markdown("##### ⚡ Quick Prompts:")
    chip_cols = st.columns(5)
    selected_prompt = None
    if chip_cols[0].button("⚡ Today Summary"):
        selected_prompt = "Show today summary"
    if chip_cols[1].button("📊 Dept Breakdown"):
        selected_prompt = "Department breakdown"
    if chip_cols[2].button("❌ Absent List"):
        selected_prompt = "Who is absent today?"
    if chip_cols[3].button("📈 7-Day Trend"):
        selected_prompt = "Show 7-day attendance trend"
    if chip_cols[4].button("🕒 Recent Logs"):
        selected_prompt = "Show recent attendance logs"

    # Display Chat History
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "chart" in msg and msg["chart"]:
                c_data = msg["chart"]
                if c_data["type"] == "pie":
                    fig = px.pie(
                        names=c_data["labels"],
                        values=c_data["values"],
                        title=c_data.get("title", ""),
                        color_discrete_sequence=c_data.get("colors", ["#10b981", "#ef4444"]),
                        hole=0.4
                    )
                    fig.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                elif c_data["type"] == "bar":
                    df_bar = pd.DataFrame()
                    for series in c_data.get("series", []):
                        temp_df = pd.DataFrame({
                            "Department": c_data["labels"],
                            "Count": series["values"],
                            "Status": series["name"]
                        })
                        df_bar = pd.concat([df_bar, temp_df])
                    fig = px.bar(
                        df_bar, x="Department", y="Count", color="Status",
                        barmode="group", title=c_data.get("title", ""),
                        color_discrete_map={"Present": "#10b981", "Absent": "#ef4444"}
                    )
                    fig.update_layout(template="plotly_dark", height=300, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)
                elif c_data["type"] == "line":
                    fig = px.line(
                        x=c_data["labels"], y=c_data["values"],
                        labels={"x": "Date", "y": "Recognitions"},
                        title=c_data.get("title", ""),
                        markers=True
                    )
                    fig.update_traces(line_color="#6366f1", line_width=3)
                    fig.update_layout(template="plotly_dark", height=280, margin=dict(l=20, r=20, t=40, b=20))
                    st.plotly_chart(fig, use_container_width=True)

    # User Input Chat box
    user_query = st.chat_input("Ask AI a question about your attendance database...") or selected_prompt
    if user_query:
        # Add user query to chat history
        st.session_state.messages.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.markdown(user_query)

        # Process with AI Engine
        res = analytics_engine.process_chat_query(user_query)
        st.session_state.messages.append({
            "role": "assistant",
            "content": res["answer"],
            "chart": res.get("chart")
        })
        st.rerun()

# -----------------------------------------------------------------------------
# Page 2: 📹 Live Scanner
# -----------------------------------------------------------------------------
elif menu_option == "📹 Live Scanner":
    st.title("📹 Live Face Recognition Scanner")
    st.caption("Scan student faces using webcam feed and automatically record attendance.")

    col_cam, col_logs = st.columns([1.5, 1])

    with col_cam:
        st.subheader("Webcam Scanner")
        run_cam = st.checkbox("Turn On Live Camera Stream", value=True)
        FRAME_WINDOW = st.image([])

        if run_cam:
            cap = cv2.VideoCapture(config.CAMERA_INDEX)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)

            if not cap.isOpened():
                st.warning("⚠️ Local camera feed unavailable or in use by another app.")
            else:
                ret, frame = cap.read()
                if ret:
                    processed_frame, notification = engine.process_frame(frame)
                    # Convert BGR to RGB
                    rgb_frame = cv2.cvtColor(processed_frame, cv2.COLOR_BGR2RGB)
                    FRAME_WINDOW.image(rgb_frame)
                    if notification:
                        st.toast(notification, icon="✅")
                cap.release()

    with col_logs:
        st.subheader("⚡ Live Recognition Stream")
        recent_logs = database.get_attendance_logs()[:10]
        if recent_logs:
            df_logs = pd.DataFrame(recent_logs)[["student_id", "name", "department", "time"]]
            st.dataframe(df_logs, use_container_width=True)
        else:
            st.info("No attendance logs recorded yet today.")

# -----------------------------------------------------------------------------
# Page 3: 👥 Student Directory
# -----------------------------------------------------------------------------
elif menu_option == "👥 Student Directory":
    st.title("👥 Enrolled Students Directory & Registration")

    tab_reg, tab_view = st.tabs(["➕ Register Student", "📋 Student Directory"])

    with tab_reg:
        st.subheader("Register New Student Profile")
        with st.form("student_reg_form"):
            s_id = st.text_input("Student ID*", placeholder="e.g. CS101")
            s_name = st.text_input("Full Name*", placeholder="e.g. Alex Mercer")
            s_dept = st.selectbox("Department*", ["Computer Science", "Information Technology", "Electrical", "Mechanical", "Civil", "Management"])
            s_email = st.text_input("Email", placeholder="alex@university.edu")

            st.write("📸 Upload Sample Face Photos (Minimum 3 images recommended):")
            uploaded_files = st.file_uploader("Choose face images", type=["jpg", "jpeg", "png"], accept_multiple_files=True)

            submitted = st.form_submit_button("Register & Train Model")

            if submitted:
                if not s_id or not s_name:
                    st.error("Please fill in Student ID and Full Name.")
                else:
                    success, msg = database.add_student(s_id, s_name, s_dept, s_email)
                    if success:
                        saved_count = 0
                        if uploaded_files:
                            for idx, f in enumerate(uploaded_files):
                                file_bytes = np.asarray(bytearray(f.read()), dtype=np.uint8)
                                img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
                                ok, _ = engine.save_face_samples(s_id, img, idx + 1)
                                if ok:
                                    saved_count += 1
                        
                        # Retrain model
                        t_ok, t_msg = engine.train_model()
                        st.success(f"Student {s_name} registered! Saved {saved_count} face samples. Model training status: {t_msg}")
                        st.rerun()
                    else:
                        st.error(f"Error registering student: {msg}")

    with tab_view:
        st.subheader("Registered Student Directory")
        students = database.get_all_students()
        if students:
            df_students = pd.DataFrame(students)[["student_id", "name", "department", "email", "registered_at"]]
            st.dataframe(df_students, use_container_width=True)

            st.markdown("---")
            st.markdown("#### Delete Student Profile")
            del_id = st.selectbox("Select Student to Delete", [s["student_id"] for s in students])
            if st.button("Delete Selected Student", type="secondary"):
                database.delete_student(del_id)
                # Retrain model
                engine.train_model()
                st.success(f"Student `{del_id}` deleted successfully.")
                st.rerun()
        else:
            st.info("No students registered yet.")

# -----------------------------------------------------------------------------
# Page 4: 📊 Attendance Logs & Analytics
# -----------------------------------------------------------------------------
elif menu_option == "📊 Attendance Logs & Analytics":
    st.title("📊 Attendance Logs & Data Analytics")

    analytics = database.get_analytics_summary()
    depts = analytics["department_breakdown"]
    trend = analytics["recent_trend"]

    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Department Attendance Breakdown")
        if depts:
            df_dept = pd.DataFrame(depts)
            fig_dept = px.bar(
                df_dept, x="department", y=["present", "absent"],
                title="Present vs Absent per Department",
                barmode="group",
                color_discrete_sequence=["#10b981", "#ef4444"]
            )
            fig_dept.update_layout(template="plotly_dark", height=320)
            st.plotly_chart(fig_dept, use_container_width=True)
        else:
            st.info("No department metrics available.")

    with col_chart2:
        st.subheader("7-Day Attendance Trend")
        if trend:
            df_trend = pd.DataFrame(trend)
            fig_trend = px.line(
                df_trend, x="date", y="count",
                title="Daily Attendance Count Velocity",
                markers=True
            )
            fig_trend.update_traces(line_color="#6366f1", line_width=3)
            fig_trend.update_layout(template="plotly_dark", height=320)
            st.plotly_chart(fig_trend, use_container_width=True)

    st.markdown("---")
    st.subheader("Export Attendance Logs")
    logs = database.get_attendance_logs()
    if logs:
        df_logs = pd.DataFrame(logs)
        st.dataframe(df_logs, use_container_width=True)

        csv = df_logs.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Attendance CSV Report",
            data=csv,
            file_name="attendance_report.csv",
            mime="text/csv"
        )
    else:
        st.info("No attendance logs recorded yet.")
