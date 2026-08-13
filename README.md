# AI Face Recognition Attendance & Business Analytics Studio

A modern, full-stack **AI Face Recognition Attendance & Business Analytics Studio** built with Python, OpenCV, Flask, Streamlit, Plotly, SQLite, and a Glassmorphic Web Dashboard.

## 🚀 Quick Access Links

Click below to open the live application dashboards:

- 💬 **[Flask Web Dashboard & AI Studio (http://localhost:5000/chat)](http://localhost:5000/chat)**
- ⚡ **[Streamlit AI Business Studio (http://localhost:8501)](http://localhost:8501)**

Double-click [Open_Dashboard.html](file:///c:/Users/sathi/OneDrive/Desktop/PROJECT'S/AL%20FACE%20RECOGNITION%20ATTENDANCE%20SYSTEM/Open_Dashboard.html) to choose your preferred interface.

---

## 🛠️ How to Run

1. **Install Dependencies**:
   ```bash
   python -m pip install -r requirements.txt
   ```

2. **Run Flask Web Dashboard & AI Studio**:
   ```bash
   python run.py
   ```
   Open **http://localhost:5000/chat** in your web browser.

3. **Run Streamlit AI Business Analytics Studio**:
   ```bash
   streamlit run streamlit_app.py
   ```
   Or run `python run.py --streamlit`. Access at **http://localhost:8501**.

---

## ✨ Features

- 💬 **AI Business Analytics Chatbot**: Query attendance statistics, department performance, absent lists, and 7-day velocity in natural language with interactive chart responses.
- 📹 **Real-Time Video Stream**: Live face detection and recognition using OpenCV Haar Cascades and LBPH Face Recognizer.
- ⚡ **Automated Attendance**: Auto-detects registered students and marks attendance with date/time logging and anti-spam cooldown.
- 👥 **Student Enrollment**: Register students with webcam sample dataset creation or image uploads.
- 📊 **Attendance Logs & Analytics**: Filter by date or department and export logs to **CSV/Excel**.
- 📈 **Interactive Visualizations**: Dynamic Chart.js and Plotly graphs for department breakdowns and daily trends.

