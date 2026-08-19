import logging
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import config

logger = logging.getLogger("VisionAttendance.Database")


def get_connection():
    """Create a database connection with dictionary cursor row factory and Foreign Keys enabled."""
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    """Initialize database tables if they do not exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Users & Authentication Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'admin',
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Departments Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dept_name TEXT UNIQUE NOT NULL,
            dept_code TEXT UNIQUE NOT NULL
        );
    """)

    # Classes Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE NOT NULL,
            department TEXT NOT NULL
        );
    """)

    # Subjects Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT NOT NULL,
            subject_code TEXT UNIQUE NOT NULL
        );
    """)

    # Faculty Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS faculty (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );
    """)

    # Students Table with Soft-Deletion Support
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            class_name TEXT DEFAULT 'General',
            email TEXT,
            is_active INTEGER DEFAULT 1,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Attendance Sessions Table (Department -> Class/Subject -> Faculty -> Session)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_name TEXT NOT NULL,
            department TEXT NOT NULL,
            subject TEXT DEFAULT 'General',
            faculty TEXT DEFAULT 'Administrator',
            date TEXT NOT NULL,
            is_active INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Attendance Log Table with Unique Session Constraint
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            session_id INTEGER,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students (student_id),
            FOREIGN KEY (session_id) REFERENCES attendance_sessions (id)
        );
    """)

    # Create Unique Index to prevent duplicate student attendance per session per date
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_uniq_attendance_session 
        ON attendance(student_id, session_id, date);
    """)

    # Audit Logs Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            action TEXT NOT NULL,
            status TEXT NOT NULL,
            details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Schema Migrations
    try:
        cursor.execute("ALTER TABLE students ADD COLUMN is_active INTEGER DEFAULT 1;")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE students ADD COLUMN class_name TEXT DEFAULT 'General';")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN subject TEXT DEFAULT 'General';")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN faculty TEXT DEFAULT 'Administrator';")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE attendance_sessions ADD COLUMN is_active INTEGER DEFAULT 0;")
    except Exception:
        pass

    try:
        cursor.execute("ALTER TABLE attendance ADD COLUMN session_id INTEGER;")
    except Exception:
        pass
    
    conn.commit()
    conn.close()

    # Seed default admin if no users exist
    seed_default_admin()



def log_audit_event(username, action, status="SUCCESS", details=""):
    """Record administrative or security audit log entry."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO audit_logs (username, action, status, details)
            VALUES (?, ?, ?, ?);
        """, (username, action, status, details))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Audit log error: {e}")


def seed_default_admin():
    """Create default super admin account if none exists using config credentials."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users;")
    if cursor.fetchone()["count"] == 0:
        username = config.ADMIN_USERNAME
        password = config.ADMIN_PASSWORD
        if not password:
            password = "admin123"
            logger.warning("ADMIN_PASSWORD not set in environment. Defaulting initial password. Please update immediately!")
        
        hashed = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, name)
            VALUES (?, ?, ?, ?);
        """, (username, hashed, "admin", "System Administrator"))
        conn.commit()
    conn.close()



def create_user(username, password, name, role="admin"):
    """Register a new user with hashed password."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        hashed = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, name)
            VALUES (?, ?, ?, ?);
        """, (username, hashed, role, name))
        conn.commit()
        return True, "User created successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def verify_user(username, password):
    """Verify user credentials and return user object if valid."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?;", (username,))
    row = cursor.fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        user_dict = dict(row)
        user_dict.pop("password_hash", None)
        return user_dict
    return None

def get_user_by_username(username):
    """Fetch user dict by username."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, name, created_at FROM users WHERE username = ?;", (username,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def add_student(student_id, name, department, email=""):
    """Register or update a student."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (student_id, name, department, email)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(student_id) DO UPDATE SET
                name=excluded.name,
                department=excluded.department,
                email=excluded.email
        """, (student_id, name, department, email))
        conn.commit()
        return True, "Student registered successfully."
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()

def get_all_students():
    """Fetch all active registered students."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE is_active = 1 ORDER BY registered_at DESC;")
    rows = cursor.fetchall()
    students = [dict(row) for row in rows]
    conn.close()
    return students

def get_student_by_id(student_id):
    """Fetch student by custom ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students WHERE student_id = ? AND is_active = 1;", (student_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_student(student_id):
    """Soft-delete a student by marking active = 0, preserving attendance audit history."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE students SET is_active = 0 WHERE student_id = ?;", (student_id,))
    conn.commit()
    conn.close()
    return True


def create_attendance_session(session_name, department, subject="General", faculty="Administrator"):
    """Create a new attendance session and set it as active."""
    conn = get_connection()
    cursor = conn.cursor()
    today_date = datetime.now().strftime("%Y-%m-%d")
    
    # Deactivate all current sessions first
    cursor.execute("UPDATE attendance_sessions SET is_active = 0;")
    
    cursor.execute("""
        INSERT INTO attendance_sessions (session_name, department, subject, faculty, date, is_active)
        VALUES (?, ?, ?, ?, ?, 1);
    """, (session_name, department, subject, faculty, today_date))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def get_active_session():
    """Retrieve currently active attendance session if any."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance_sessions WHERE is_active = 1 ORDER BY id DESC LIMIT 1;")
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def get_all_sessions():
    """Fetch all recorded attendance sessions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM attendance_sessions ORDER BY id DESC;")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def set_active_session(session_id):
    """Set a specific session as active (or 0 to deactivate all)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE attendance_sessions SET is_active = 0;")
    if session_id and session_id > 0:
        cursor.execute("UPDATE attendance_sessions SET is_active = 1 WHERE id = ?;", (session_id,))
    conn.commit()
    conn.close()
    return True

def mark_attendance(student_id, session_id=None):
    """
    Mark student attendance if not already marked for the current session and date.
    Prevents duplicate attendance entries per session at both query and DB constraint levels.
    Returns (success: bool, status_message: str, student_info: dict)
    """
    student = get_student_by_id(student_id)
    if not student:
        return False, "Student not found in database.", None

    now = datetime.now()
    today_date = now.strftime("%Y-%m-%d")
    current_time = now.strftime("%H:%M:%S")

    conn = get_connection()
    cursor = conn.cursor()

    # Determine active session if session_id is not passed
    if not session_id:
        cursor.execute("SELECT id FROM attendance_sessions WHERE is_active = 1 LIMIT 1;")
        sess_row = cursor.fetchone()
        if sess_row:
            session_id = sess_row["id"]

    # 1. Attendance Session Duplicate Prevention Check
    if session_id:
        cursor.execute("""
            SELECT id FROM attendance 
            WHERE student_id = ? AND session_id = ? AND date = ?;
        """, (student_id, session_id, today_date))
        if cursor.fetchone():
            conn.close()
            return False, f"Attendance already marked for {student['name']} in current session.", student
    else:
        # Fallback check for same date if no active session
        cursor.execute("""
            SELECT id FROM attendance 
            WHERE student_id = ? AND date = ? AND session_id IS NULL;
        """, (student_id, today_date))
        if cursor.fetchone():
            conn.close()
            return False, f"Attendance already marked for {student['name']} today.", student

    # 2. Check last attendance timestamp for cooldown check
    cursor.execute("""
        SELECT timestamp FROM attendance 
        WHERE student_id = ? 
        ORDER BY timestamp DESC LIMIT 1;
    """, (student_id,))
    last_entry = cursor.fetchone()

    if last_entry and last_entry["timestamp"]:
        try:
            last_time = datetime.strptime(last_entry["timestamp"], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            last_time = datetime.fromisoformat(str(last_entry["timestamp"]))

        seconds_since = (now - last_time).total_seconds()
        if seconds_since < config.COOLDOWN_SECONDS:
            conn.close()
            return False, f"Attendance already marked recently ({int(seconds_since)}s ago).", student

    # 3. Insert attendance record with IntegrityError catch for UNIQUE constraints
    try:
        cursor.execute("""
            INSERT INTO attendance (student_id, name, department, session_id, date, time, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?);
        """, (student_id, student["name"], student["department"], session_id, today_date, current_time, now.strftime("%Y-%m-%d %H:%M:%S")))

        conn.commit()
        conn.close()
        return True, f"Attendance marked for {student['name']}.", student
    except sqlite3.IntegrityError:
        conn.close()
        return False, f"Attendance record already exists for {student['name']} in this session.", student
    except Exception as e:
        conn.close()
        return False, f"Database error: {str(e)}", student


def get_attendance_logs(date_filter=None, department_filter=None, search_query=None):
    """Fetch attendance logs with optional filters."""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM attendance WHERE 1=1"
    params = []

    if date_filter:
        query += " AND date = ?"
        params.append(date_filter)

    if department_filter and department_filter != "All":
        query += " AND department = ?"
        params.append(department_filter)

    if search_query:
        query += " AND (name LIKE ? OR student_id LIKE ?)"
        params.append(f"%{search_query}%")
        params.append(f"%{search_query}%")

    query += " ORDER BY id DESC;"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    logs = [dict(row) for row in rows]
    conn.close()
    return logs

def get_stats():
    """Get dashboard stats summary."""
    conn = get_connection()
    cursor = conn.cursor()

    today_date = datetime.now().strftime("%Y-%m-%d")

    cursor.execute("SELECT COUNT(*) as count FROM students;")
    total_students = cursor.fetchone()["count"]

    cursor.execute("SELECT COUNT(DISTINCT student_id) as count FROM attendance WHERE date = ?;", (today_date,))
    present_today = cursor.fetchone()["count"]

    absent_today = max(0, total_students - present_today)

    cursor.execute("SELECT COUNT(*) as count FROM attendance;")
    total_logs = cursor.fetchone()["count"]

    conn.close()

    return {
        "total_students": total_students,
        "present_today": present_today,
        "absent_today": absent_today,
        "total_logs": total_logs,
        "today_date": today_date
    }

def get_department_breakdown(date_filter=None):
    """Get total student count and present student count per department."""
    conn = get_connection()
    cursor = conn.cursor()
    today_date = date_filter or datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT department, COUNT(*) as total_students 
        FROM students 
        GROUP BY department;
    """)
    dept_totals = {row["department"]: row["total_students"] for row in cursor.fetchall()}

    cursor.execute("""
        SELECT department, COUNT(DISTINCT student_id) as present_count 
        FROM attendance 
        WHERE date = ? 
        GROUP BY department;
    """, (today_date,))
    dept_presents = {row["department"]: row["present_count"] for row in cursor.fetchall()}

    conn.close()

    all_depts = set(dept_totals.keys()).union(set(dept_presents.keys()))
    result = []
    for dept in sorted(all_depts):
        tot = dept_totals.get(dept, 0)
        pres = dept_presents.get(dept, 0)
        absent = max(0, tot - pres)
        rate = round((pres / tot * 100), 1) if tot > 0 else 0.0
        result.append({
            "department": dept,
            "total": tot,
            "present": pres,
            "absent": absent,
            "rate_pct": rate
        })
    return result

def get_daily_attendance_trend(days=7):
    """Get attendance record count for the past N days."""
    conn = get_connection()
    cursor = conn.cursor()
    start_date = (datetime.now() - timedelta(days=days - 1)).strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT date, COUNT(DISTINCT student_id) as count 
        FROM attendance 
        WHERE date >= ? 
        GROUP BY date 
        ORDER BY date ASC;
    """, (start_date,))
    
    rows = cursor.fetchall()
    conn.close()

    trend_map = {row["date"]: row["count"] for row in rows}
    
    # Fill in date sequence
    date_list = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days - 1, -1, -1)]
    return [{"date": d, "count": trend_map.get(d, 0)} for d in date_list]

def get_absent_students(date_filter=None):
    """Get list of registered students who are absent for given date."""
    conn = get_connection()
    cursor = conn.cursor()
    target_date = date_filter or datetime.now().strftime("%Y-%m-%d")

    cursor.execute("""
        SELECT * FROM students 
        WHERE student_id NOT IN (
            SELECT DISTINCT student_id FROM attendance WHERE date = ?
        )
        ORDER BY name ASC;
    """, (target_date,))

    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_analytics_summary():
    """Detailed analytics summary for AI Assistant insights."""
    stats = get_stats()
    dept_breakdown = get_department_breakdown()
    recent_trend = get_daily_attendance_trend(7)
    absent_students = get_absent_students()
    
    total = stats["total_students"]
    present = stats["present_today"]
    attendance_rate = round((present / total * 100), 1) if total > 0 else 0.0

    return {
        "stats": stats,
        "attendance_rate": attendance_rate,
        "department_breakdown": dept_breakdown,
        "recent_trend": recent_trend,
        "absent_students": absent_students
    }

def get_audit_logs(limit=50):
    """Fetch recent system audit log entries."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT ?;", (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]



