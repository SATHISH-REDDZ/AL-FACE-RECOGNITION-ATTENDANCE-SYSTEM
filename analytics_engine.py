"""
AI Business Analytics Engine
-----------------------------
Processes natural language user queries regarding attendance records, student statistics,
department breakdowns, absent students, daily trends, and overall metrics.
"""

from datetime import datetime, timedelta
import database

def process_chat_query(user_message: str) -> dict:
    """
    Analyzes user message and returns structured response payload containing:
    - answer: str (Markdown format response)
    - chart: dict or None (Chart specification for rendering)
    - data: dict (raw context data)
    """
    msg = (user_message or "").strip().lower()
    analytics = database.get_analytics_summary()
    stats = analytics["stats"]
    depts = analytics["department_breakdown"]
    trend = analytics["recent_trend"]
    absent = analytics["absent_students"]
    
    today_str = stats["today_date"]

    # 1. Summary / Overview Queries
    if any(k in msg for k in ["summary", "overview", "status", "today", "report", "hello", "hi"]):
        answer = (
            f"### ⚡ **Today's Attendance & Analytics Overview** ({today_str})\n\n"
            f"- 🎓 **Total Enrolled Students:** `{stats['total_students']}`\n"
            f"- ✅ **Present Today:** `{stats['present_today']}` ({analytics['attendance_rate']}%)\n"
            f"- ❌ **Absent Today:** `{stats['absent_today']}`\n"
            f"- 📋 **Total Attendance Logs Recorded:** `{stats['total_logs']}`\n\n"
            f"**Quick Insight:** Department performance and daily trends are highlighted in the chart below."
        )
        chart_data = {
            "type": "pie",
            "title": "Today's Attendance Status",
            "labels": ["Present Today", "Absent Today"],
            "values": [stats["present_today"], stats["absent_today"]],
            "colors": ["#10b981", "#ef4444"]
        }
        return {"status": "success", "answer": answer, "chart": chart_data, "data": stats}

    # 2. Department Breakdown Queries
    if any(k in msg for k in ["department", "dept", "branch", "breakdown", "division"]):
        if not depts:
            answer = "ℹ️ No department data or enrolled students found in database."
            return {"status": "success", "answer": answer, "chart": None, "data": []}
        
        table_rows = []
        dept_labels = []
        present_vals = []
        absent_vals = []
        for d in depts:
            table_rows.append(f"| `{d['department']}` | `{d['total']}` | `{d['present']}` | `{d['absent']}` | `{d['rate_pct']}%` |")
            dept_labels.append(d["department"])
            present_vals.append(d["present"])
            absent_vals.append(d["absent"])

        table_md = "\n".join(table_rows)
        answer = (
            f"### 📊 **Department Attendance Breakdown**\n\n"
            f"| Department | Total Students | Present | Absent | Attendance Rate |\n"
            f"| :--- | :---: | :---: | :---: | :---: |\n"
            f"{table_md}\n\n"
            f"💡 *Tip: You can register new students or re-assign departments via the Student Directory.*"
        )
        chart_data = {
            "type": "bar",
            "title": "Department Attendance Breakdown",
            "labels": dept_labels,
            "series": [
                {"name": "Present", "values": present_vals, "color": "#10b981"},
                {"name": "Absent", "values": absent_vals, "color": "#ef4444"}
            ]
        }
        return {"status": "success", "answer": answer, "chart": chart_data, "data": depts}

    # 3. Absent Students Queries
    if any(k in msg for k in ["absent", "missing", "not present", "who is absent"]):
        if not absent:
            answer = "🎉 **Great news!** All registered students are present today, or no students are registered yet."
            return {"status": "success", "answer": answer, "chart": None, "data": []}
        
        absent_list_md = "\n".join([f"- **{s['name']}** (ID: `{s['student_id']}`) - `{s['department']}`" for s in absent])
        answer = (
            f"### ❌ **Absent Students Today ({len(absent)})**\n\n"
            f"{absent_list_md}\n\n"
            f"Total Absent Rate: `{round((len(absent)/stats['total_students']*100), 1) if stats['total_students'] else 0}%`"
        )
        return {"status": "success", "answer": answer, "chart": None, "data": absent}

    # 4. Attendance Trends / History Queries
    if any(k in msg for k in ["trend", "history", "past", "weekly", "days", "chart", "graph"]):
        trend_dates = [t["date"] for t in trend]
        trend_counts = [t["count"] for t in trend]
        
        answer = (
            f"### 📈 **7-Day Attendance Trend Analysis**\n\n"
            f"Over the last 7 days, attendance activity fluctuated between `{min(trend_counts)}` and `{max(trend_counts)}` daily recognitions.\n\n"
            f"Refer to the line graph below for detailed day-by-day velocity."
        )
        chart_data = {
            "type": "line",
            "title": "Daily Attendance Count (Past 7 Days)",
            "labels": trend_dates,
            "values": trend_counts,
            "color": "#6366f1"
        }
        return {"status": "success", "answer": answer, "chart": chart_data, "data": trend}

    # 5. Recent Logs Queries
    if any(k in msg for k in ["recent", "log", "logs", "latest", "time", "clock", "last"]):
        logs = database.get_attendance_logs()[:10]
        if not logs:
            answer = "ℹ️ No recent attendance logs found today."
            return {"status": "success", "answer": answer, "chart": None, "data": []}

        rows_md = "\n".join([f"| `{l['student_id']}` | **{l['name']}** | `{l['department']}` | `{l['date']}` | `{l['time']}` |" for l in logs])
        answer = (
            f"### 🕒 **Latest 10 Attendance Scans**\n\n"
            f"| Student ID | Name | Department | Date | Time |\n"
            f"| :--- | :--- | :--- | :--- | :--- |\n"
            f"{rows_md}"
        )
        return {"status": "success", "answer": answer, "chart": None, "data": logs}

    # 6. Student List / Search Queries
    if any(k in msg for k in ["student", "students", "registered", "directory", "list", "who"]):
        students = database.get_all_students()
        if not students:
            answer = "ℹ️ No students are registered in the system database."
            return {"status": "success", "answer": answer, "chart": None, "data": []}

        rows_md = "\n".join([f"| `{s['student_id']}` | **{s['name']}** | `{s['department']}` | `{s['email'] or 'N/A'}` |" for s in students[:15]])
        total_msg = f"Showing top 15 of {len(students)} registered students." if len(students) > 15 else f"Total registered students: {len(students)}."
        
        answer = (
            f"### 👥 **Student Directory**\n\n"
            f"| Student ID | Name | Department | Email |\n"
            f"| :--- | :--- | :--- | :--- |\n"
            f"{rows_md}\n\n"
            f"*{total_msg}*"
        )
        return {"status": "success", "answer": answer, "chart": None, "data": students}

    # Default Fallback Response
    answer = (
        f"🤖 **AI Business Analytics Assistant**\n\n"
        f"I received your question: *\"{user_message}\"*\n\n"
        f"Here are key real-time metrics from your attendance system:\n"
        f"- 🎓 Total Enrolled: `{stats['total_students']}`\n"
        f"- ✅ Present Today: `{stats['present_today']}`\n"
        f"- ❌ Absent Today: `{stats['absent_today']}`\n\n"
        f"**You can try asking me:**\n"
        f"1. *\"Show today summary\"*\n"
        f"2. *\"Department breakdown\"*\n"
        f"3. *\"Who is absent today?\"*\n"
        f"4. *\"Show 7-day attendance trend\"*\n"
        f"5. *\"Show recent attendance logs\"*"
    )
    chart_data = {
        "type": "pie",
        "title": "Attendance Distribution",
        "labels": ["Present", "Absent"],
        "values": [stats["present_today"], stats["absent_today"]],
        "colors": ["#10b981", "#ef4444"]
    }
    return {"status": "success", "answer": answer, "chart": chart_data, "data": stats}
