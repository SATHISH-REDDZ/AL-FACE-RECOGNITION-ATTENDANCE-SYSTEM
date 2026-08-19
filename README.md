# 💻 AI Face Recognition Attendance System

[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![OpenCV](https://img.shields.io/badge/OpenCV-Haar%20%2B%20LBPH-red.svg)](https://opencv.org/)
[![Database](https://img.shields.io/badge/SQLite-Relational%20Schema-lightgrey.svg)](https://www.sqlite.org/)
[![Security](https://img.shields.io/badge/Security-CSRF%20%7C%20RBAC%20%7C%20Audit%20Logs-orange.svg)](#14-security-features)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

An AI-powered web-based attendance management system that uses computer vision and face recognition to identify registered students and automatically record attendance through a browser camera.

---
## 🌐 Web Application Links

- 🚀 **Live Web Application (Local):** [http://127.0.0.1:5000](http://127.0.0.1:5000)
- 💬 **AI Chat Studio:** [http://127.0.0.1:5000/chat](http://127.0.0.1:5000/chat)
- 🐙 **GitHub Repository:** [https://github.com/SATHISH-REDDZ/AL-FACE-RECOGNITION-ATTENDANCE-SYSTEM](https://github.com/SATHISH-REDDZ/AL-FACE-RECOGNITION-ATTENDANCE-SYSTEM)


## 📌 1. Project Introduction

The **AI Face Recognition Attendance System** is a full-stack web application developed to automate the traditional student attendance process using Artificial Intelligence, Computer Vision, Face Detection, Face Recognition, Database Management, and Web Technologies.

The system allows authorized users to register students, collect facial images through a browser camera, train a facial recognition model, recognize registered students in real time, and automatically record their attendance.

The current recognition pipeline uses **OpenCV Haar Cascade** for face detection and **LBPH (Local Binary Patterns Histograms)** for face recognition.

The application is built around a **Flask backend**, browser-based **HTML/CSS/JavaScript frontend**, and **SQLite database**. It also includes attendance analytics, report export, authentication, validation, audit logging, health checks, and automated tests.

The architecture is designed so that the browser camera belongs to the user while the Flask backend performs the recognition and attendance processing. This makes the application suitable for eventual cloud deployment.

---

## 🎯 2. Project Objectives

- **Automate Student Attendance**: Replaces roll calls with instant biometric recognition.
- **Reduce Manual Effort**: Eliminates manual sign-in sheets and manual register data entry.
- **Biometric Student Identification**: Identifies students using facial feature extraction.
- **Automatic Attendance Logging**: Automatically inserts date, time, and session metadata into database.
- **Minimize Entry Errors**: Reduces human mistakes, illegible signatures, and transcript errors.
- **Block Unknown Faces**: Prevents unregistered faces from being marked as valid students.
- **Maintain Centralized Records**: Stores all records in a structured relational database.
- **Provide Student Management**: Supports student registration, directory search, and soft deletion.
- **Deliver Attendance Analytics**: Offers instant statistical summaries and interactive charts.
- **Generate Downloadable Reports**: Supports CSV and Excel (`.xlsx`) export functionality.
- **Ensure Security & Privacy**: Implements password hashing, CSRF validation, rate limiting, and RBAC.
- **Expose REST APIs**: Connects frontend UI to backend logic via standardized REST endpoints.
- **Provide Health & Readiness Probes**: Offers `/health` and `/ready` endpoints for monitoring.
- **Include Automated Unit Tests**: Includes comprehensive automated test suites.
- **Prepare for Cloud Deployment**: Supports browser camera streaming via `getUserMedia()`.
- **Provide Foundation for Future AI**: Serves as a solid architecture for advanced deep-learning upgrades.

---

## ❗ 3. Problem Statement vs 💡 Proposed Solution

### Traditional Attendance Problems
- ⏱️ **Time Consuming**: Manual registers and name calling waste 10–15 minutes per lecture.
- ⚠️ **Human Errors**: Miscounts, lost papers, or manual entry mistakes.
- 🎭 **Proxy Attendance**: Students signing or scanning for absent peers.
- 📁 **Maintainability**: Hard to archive, search historical logs, or generate institutional reports.

### Proposed Automated Solution

```
Student ➔ Browser Camera ➔ Face Detection ➔ Quality Validation ➔ Face Recognition ➔ Student Identification ➔ Attendance Verification ➔ Database ➔ Dashboard ➔ Analytics & Reports
```

---

## ⭐ 5. Major Features

### 👤 Student Management
- **Registration & Validation**: Student ID regex validation, name validation, email validation, and department assignment.
- **Student Listing & Search**: Instant searching and filtering across registered students.
- **Profile & Soft Deletion**: Delete students safely without corrupting historical logs (`is_active = 0`).
- **Face Enrollment**: Automated frame capture and dataset generation.

### 📷 Face Detection
Uses OpenCV's Haar Cascade Classifier (`haarcascade_frontalface_default.xml`).
```
Camera Frame ➔ Image Decode ➔ Grayscale ➔ Haar Cascade ➔ Face Bounding Box
```

### 🧠 Face Recognition
Uses **LBPH (Local Binary Patterns Histograms)** matching algorithm.
```
Training Images ➔ Preprocessing ➔ LBPH Training ➔ Recognition Model ➔ Prediction ➔ Confidence/Distance ➔ Student Identity
```
Model artifacts persisted in `data/trainer/`:
- `trainer.yml` — Serialized LBPH model weights
- `labels.json` — Mapping between integer labels and Student ID strings
- `metadata.json` — Model version, sample counts, algorithm name, and timestamp

### 📸 Face Quality & Enrollment Validation
Enforces image quality checks before adding frames to training datasets:
- **Face Presence**: Verifies a face exists in the frame.
- **Single Face Guard**: Rejects frames with 0 or >1 faces during enrollment.
- **Face Size**: Ensures face region is at least 90x90 pixels.
- **Brightness Range**: Checks mean gray intensity (must be between 30 and 230).
- **Blur/Sharpness**: Evaluates Laplacian variance (must exceed sharpness threshold of 35.0).

### 🎥 Browser Camera Architecture
Uses client-side `getUserMedia()` API to stream frames over base64 HTTP requests.
```
User Device ➔ Browser (getUserMedia) ➔ Camera Stream ➔ JavaScript ➔ Captured Frame ➔ Flask API ➔ OpenCV ➔ Face Recognition
```
*Allows cloud hosting (Render, AWS, Railway) where the host server lacks a physical webcam.*

---

## 📝 8. Attendance Workflow

```
               Start Recognition
                       │
                       ▼
                 Capture Frame
                       │
                       ▼
                  Detect Face
                       │
                       ▼
                 Validate Face
                       │
                       ▼
                Recognize Face
                       │
             ┌─────────┴─────────┐
            NO                   YES
             │                   │
             ▼                   ▼
          Reject             Identify
                                 │
                                 ▼
                          Attendance Check
                                 │
                       ┌─────────┴─────────┐
                      YES                  NO
                       │                   │
                       ▼                   ▼
                    Ignore              Present
                                           │
                                           ▼
                                        Database
```

---

## 🔐 14. Security Features

- **Authentication**: Session-based login with Werkzeug password hashing.
- **CSRF Protection**: Token validation on all state-changing requests (`POST`, `DELETE`, `PUT`).
- **Role-Based Access Control (RBAC)**: `@role_required('admin')` for administrative actions.
- **Input Validation**: Strict regex rules for Student IDs (`^[a-zA-Z0-9_-]{3,30}$`), names, and emails.
- **Path Traversal Safety**: Explicitly blocks `..`, `/`, `\`, `:`, and `~` in file paths.
- **Login Rate Limiting**: IP-based lockout after 5 consecutive failed login attempts (5-minute cooldown).
- **Audit Logging**: Comprehensive logging of user logins, registrations, student deletions, and model training.
- **Environment Configuration**: Key settings loaded safely via `.env` file.
- **Probes**: `/health` and `/ready` endpoints for system readiness checking.

---

## 🏗️ 19. Complete System Architecture

```
                         ┌───────────────┐
                         │     USER      │
                         └───────┬───────┘
                                 │
                                 ▼
                       ┌──────────────────┐
                       │   Web Browser    │
                       │ HTML/CSS/JS      │
                       └────────┬─────────┘
                                │
                         Camera / HTTPS
                                │
                                ▼
                       ┌──────────────────┐
                       │      Flask       │
                       │   Web Server     │
                       │    REST APIs     │
                       └────────┬─────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
              ▼                 ▼                 ▼
       ┌────────────┐    ┌────────────┐    ┌─────────────┐
       │ Face Engine│    │  Database  │    │  Analytics  │
       │ OpenCV/LBPH│    │   SQLite   │    │    Engine   │
       └──────┬─────┘    └────────────┘    └─────────────┘
              │
              ▼
       ┌─────────────┐
       │ Haar Cascade│
       │    + LBPH   │
       └──────┬──────┘
              │
              ▼
       Student Identity
              │
              ▼
          Attendance
```

---

## 🗂️ 23. Project Structure

```
AL-FACE-RECOGNITION-ATTENDANCE-SYSTEM/
│
├── app.py                   # Main Flask application & REST API routes
├── config.py                # Central application configuration & environment settings
├── database.py              # SQLite database schema, initialization & queries
├── face_engine.py          # OpenCV Haar Cascade detection, LBPH recognizer & liveness engine
├── analytics_engine.py     # AI Business Analytics Assistant query processor
├── streamlit_app.py        # Streamlit analytics studio interface
├── utils_validation.py     # Input validation, security guard & path traversal checks
├── run.py                  # Application startup & unified launcher script
│
├── templates/
│   ├── index.html          # Main web dashboard interface
│   └── login.html          # Authentication login template
│
├── static/
│   ├── css/
│   │   └── style.css       # Glassmorphism dark-theme CSS styles
│   └── js/
│       └── app.js          # Client-side SPA controller & camera handler
│
├── models/
│   └── haarcascade_frontalface_default.xml # Haar Cascade model file
│
├── data/
│   ├── dataset/            # Face dataset storage (grouped by student_id)
│   ├── trainer/            # Model outputs (trainer.yml, labels.json, metadata.json)
│   └── attendance.db       # SQLite database file
│
├── tests/
│   └── test_suite.py       # Automated engineering test suite
│
├── screenshots/            # System screenshots directory
│   └── README.md
│
├── requirements.txt        # Python dependency requirements
├── Procfile                # Heroku / Render deployment process file
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Docker compose stack file
├── .dockerignore           # Docker build exclusions
├── .env.example            # Environment variables example template
├── .gitignore              # Git ignored files list
├── LICENSE                 # MIT License file
└── README.md               # Master documentation
```

---

## 📡 30. API Structure

| Endpoint | Method | Role | Description |
| :--- | :--- | :--- | :--- |
| `/login` | `POST`, `GET` | Public | User authentication & login view |
| `/logout` | `GET` | User | Session destruction & logout |
| `/api/stats` | `GET` | User | Real-time dashboard statistics |
| `/api/students` | `GET` | User | Retrieve list of registered active students |
| `/api/students` | `POST` | Admin | Register new student & save face samples |
| `/api/students/<id>` | `DELETE` | Admin | Soft-delete student & retrain model |
| `/api/attendance` | `GET` | User | Query attendance logs with date/dept filters |
| `/api/attendance/export` | `GET` | User | Export attendance logs to CSV or Excel (`.xlsx`) |
| `/api/recognition/frame` | `POST` | User | Process base64 browser camera frame |
| `/api/analytics` | `GET` | User | Fetch department breakdowns and 7-day trends |
| `/api/chat` | `POST` | User | Natural language query for AI Analytics Assistant |
| `/api/train` | `POST` | Admin | Explicitly retrain LBPH recognition model |
| `/api/sessions` | `GET`, `POST` | User | Manage department/class attendance sessions |
| `/api/sessions/active` | `GET`, `POST` | User | Get or update currently active attendance session |
| `/api/audit` | `GET` | Admin | Retrieve security & administrative audit logs |
| `/health` | `GET` | Public | Application health status probe |
| `/ready` | `GET` | Public | Dependency readiness verification probe |

---

## 📊 31. Reports and Export

Supports instant report generation in two formats:
- **CSV Export**: `/api/attendance/export?format=csv`
- **Excel Export**: `/api/attendance/export?format=xlsx` (formatted spreadsheet via `openpyxl`)

---

## 🧪 29. Running Tests

Run the automated engineering test suite:

```bash
python -m unittest discover -s tests -v
```

Tests cover:
- Authentication & password verification
- Regex input validation & path traversal prevention
- Session management & active session toggling
- Soft-deletion student logic
- Duplicate attendance prevention
- Anti-spoofing liveness evaluation
- Health and readiness endpoints

---

## 🚀 35–37. Future Enhancements & Roadmap

### Future AI Upgrades
- Deep Learning face embeddings (FaceNet / ArcFace / ResNet)
- Modern face detection (RetinaFace / MediaPipe)
- Deep neural network anti-spoofing & liveness detection

### Future Infrastructure
- PostgreSQL / AWS RDS cloud database migration
- Persistent cloud object storage for face datasets (AWS S3)
- Kubernetes orchestration & automated CI/CD pipeline

---

## 📄 License

This project is open-source software licensed under the [MIT License](LICENSE).
