import os
import cv2
import base64
import logging
from datetime import datetime, timedelta
import numpy as np
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, session
from functools import wraps
import io
import pandas as pd
import config
import database
from face_engine import engine
import analytics_engine
import utils_validation

# Configure structured logging
logging.basicConfig(
    level=logging.INFO if not config.DEBUG else logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("VisionAttendance")

app = Flask(__name__)
app.secret_key = config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024 # 16MB Max Request Payload

# Rate limiting dictionary for failed login attempts (IP -> {attempts, lock_until})
failed_login_attempts = {}

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"success": False, "error": {"code": "UNAUTHORIZED", "message": "Authentication required. Please log in."}}), 401
            return redirect(url_for('login_view', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/health', methods=['GET'])
def health_check():
    """System health check endpoint for monitoring."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "database": "connected" if os.path.exists(config.DB_PATH) else "initializing",
        "model_trained": engine.is_trained
    }), 200

@app.route('/ready', methods=['GET'])
def readiness_check():
    """System readiness check endpoint."""
    return jsonify({"status": "ready"}), 200

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        client_ip = request.remote_addr or '127.0.0.1'
        now = datetime.now()

        # Check rate limiting lockout
        if client_ip in failed_login_attempts:
            record = failed_login_attempts[client_ip]
            if record['attempts'] >= 5 and record['lock_until'] > now:
                wait_sec = int((record['lock_until'] - now).total_seconds())
                logger.warning(f"Rate limited login attempt from IP {client_ip}")
                return render_template('login.html', error=f"Too many failed attempts. Account locked for {wait_sec} seconds."), 429

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = database.verify_user(username, password)
        if user:
            # Reset rate limiting counter on success
            if client_ip in failed_login_attempts:
                del failed_login_attempts[client_ip]
            
            session['user'] = user
            database.log_audit_event(user['username'], "LOGIN", "SUCCESS", f"User logged in from {client_ip}")
            logger.info(f"User {user['username']} logged in successfully.")

            next_page = utils_validation.safe_next_url(request.args.get('next'), default=url_for('index'))
            return redirect(next_page)

        # Track failed attempt
        if client_ip not in failed_login_attempts:
            failed_login_attempts[client_ip] = {'attempts': 1, 'lock_until': now}
        else:
            failed_login_attempts[client_ip]['attempts'] += 1
            if failed_login_attempts[client_ip]['attempts'] >= 5:
                failed_login_attempts[client_ip]['lock_until'] = now + timedelta(minutes=5)

        database.log_audit_event(username or "unknown", "LOGIN", "FAILED", f"Failed attempt from {client_ip}")
        logger.warning(f"Failed login attempt for username '{username}' from IP {client_ip}")
        return render_template('login.html', error="Invalid username or password."), 401
    
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    user = session.get('user', {})
    if user:
        database.log_audit_event(user.get('username', 'user'), "LOGOUT", "SUCCESS", "User logged out")
    session.clear()
    return redirect(url_for('login_view'))


# Global camera reference
camera = None

def get_camera():
    global camera
    if camera is None or not camera.isOpened():
        camera = cv2.VideoCapture(config.CAMERA_INDEX)
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, config.FRAME_WIDTH)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, config.FRAME_HEIGHT)
    return camera

def generate_video_frames():
    """Generator for streaming camera feed with real-time recognition overlay."""
    cam = get_camera()
    while True:
        success, frame = cam.read()
        if not success:
            blank = np.zeros((config.FRAME_HEIGHT, config.FRAME_WIDTH, 3), dtype=np.uint8)
            cv2.putText(blank, "Webcam feed unavailable", (120, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            ret, buffer = cv2.imencode('.jpg', blank)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            break
        else:
            processed_frame, _ = engine.process_frame(frame)
            ret, buffer = cv2.imencode('.jpg', processed_frame)
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
@login_required
def index():
    return render_template('index.html', current_user=session.get('user'))


@app.route('/video_feed')
def video_feed():
    return Response(generate_video_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/stats', methods=['GET'])
@login_required
def api_stats():
    stats = database.get_stats()
    stats["model_trained"] = engine.is_trained
    return jsonify(stats)

@app.route('/api/students', methods=['GET'])
@login_required
def api_get_students():
    students = database.get_all_students()
    return jsonify({"status": "success", "students": students})

@app.route('/api/students', methods=['POST'])
@login_required
def api_add_student():
    data = request.get_json() or {}
    
    # Input validation
    valid_id, id_val = utils_validation.validate_student_id(data.get('student_id'))
    if not valid_id:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": id_val}}), 422

    valid_name, name_val = utils_validation.validate_name(data.get('name'))
    if not valid_name:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": name_val}}), 422

    valid_dept, dept_val = utils_validation.validate_department(data.get('department'))
    if not valid_dept:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": dept_val}}), 422

    valid_email, email_val = utils_validation.validate_email(data.get('email', ''))
    if not valid_email:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": email_val}}), 422

    photos = data.get('photos', []) # List of base64 images
    if not isinstance(photos, list):
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": "Photos payload must be a list."}}), 422

    # Save to database
    success, msg = database.add_student(id_val, name_val, dept_val, email_val)
    if not success:
        return jsonify({"success": False, "error": {"code": "DATABASE_ERROR", "message": msg}}), 400

    # Process and save photos with quality validation
    saved_count = 0
    saved_errors = []
    if photos:
        for idx, b64_img in enumerate(photos[:30]): # Cap max 30 photos per request
            v_ok, v_err, img_mat = utils_validation.validate_base64_image(b64_img)
            if v_ok and img_mat is not None:
                ok, save_err = engine.save_face_samples(id_val, img_mat, idx + 1)
                if ok:
                    saved_count += 1
                else:
                    saved_errors.append(save_err)
            else:
                saved_errors.append(v_err)

    # Retrain engine automatically
    train_ok, train_msg = engine.train_model()

    user = session.get('user', {})
    database.log_audit_event(user.get('username', 'admin'), "ADD_STUDENT", "SUCCESS", f"Enrolled {name_val} ({id_val})")

    return jsonify({
        "success": True,
        "message": f"Student registered successfully. Saved {saved_count} face samples.",
        "data": {"student_id": id_val, "saved_count": saved_count, "training": train_msg, "quality_notes": saved_errors[:3]}
    }), 201

@app.route('/api/students/<student_id>', methods=['DELETE'])
@login_required
def api_delete_student(student_id):
    valid_id, id_val = utils_validation.validate_student_id(student_id)
    if not valid_id:
        return jsonify({"success": False, "error": {"code": "VALIDATION_ERROR", "message": id_val}}), 422

    database.delete_student(id_val)
    
    # Remove dataset folder
    student_dir = os.path.join(config.DATASET_DIR, id_val)
    if os.path.exists(student_dir):
        import shutil
        shutil.rmtree(student_dir)
        
    # Retrain model
    engine.train_model()
    
    user = session.get('user', {})
    database.log_audit_event(user.get('username', 'admin'), "DELETE_STUDENT", "SUCCESS", f"Deleted student {id_val}")
    
    return jsonify({"success": True, "message": f"Student {id_val} deleted successfully."}), 200



@app.route('/api/attendance', methods=['GET'])
def api_get_attendance():
    date_filter = request.args.get('date')
    department_filter = request.args.get('department')
    search = request.args.get('search')

    logs = database.get_attendance_logs(date_filter, department_filter, search)
    return jsonify({"status": "success", "logs": logs})

@app.route('/api/attendance/export', methods=['GET'])
@login_required
def api_export_attendance():
    date_filter = request.args.get('date')
    department_filter = request.args.get('department')
    export_format = (request.args.get('format') or 'csv').lower()

    logs = database.get_attendance_logs(date_filter, department_filter)
    if not logs:
        df = pd.DataFrame(columns=["ID", "Student ID", "Name", "Department", "Date", "Time", "Timestamp"])
    else:
        df = pd.DataFrame(logs)
        df.rename(columns={
            "id": "ID",
            "student_id": "Student ID",
            "name": "Name",
            "department": "Department",
            "date": "Date",
            "time": "Time",
            "timestamp": "Timestamp"
        }, inplace=True)

    filename_base = f"attendance_report_{date_filter or 'all'}"

    if export_format in ('xlsx', 'excel'):
        output = io.BytesIO()
        try:
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Attendance')
            output.seek(0)
            return Response(
                output.getvalue(),
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-disposition": f"attachment; filename={filename_base}.xlsx"}
            )
        except Exception as e:
            print(f"Excel export failed, falling back to CSV: {e}")

    # Default CSV Export
    csv_data = df.to_csv(index=False)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename_base}.csv"}
    )


@app.route('/chat')
@login_required
def chat_view():
    """Render main interface opened to AI Business Studio Chat tab."""
    return render_template('index.html', default_tab='tab-chat', current_user=session.get('user'))

@app.route('/api/recognition/frame', methods=['POST'])
def api_recognition_frame():
    """Process base64 webcam frame captured by client browser."""
    data = request.get_json() or {}
    image_b64 = data.get('image', '')
    if not image_b64:
        return jsonify({"status": "error", "message": "Image frame is required."}), 400

    annotated_b64, notifications, err = engine.process_base64_frame(image_b64)
    if err:
        return jsonify({"status": "error", "message": err}), 400

    return jsonify({
        "status": "success",
        "image": annotated_b64,
        "notifications": notifications
    })

@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    """Process natural language query for AI Business Analytics Studio."""
    data = request.get_json() or {}
    message = data.get('message', '').strip()
    if not message:
        return jsonify({"status": "error", "message": "Message is required."}), 400
    
    res = analytics_engine.process_chat_query(message)
    return jsonify(res)

@app.route('/api/analytics', methods=['GET'])
@login_required
def api_analytics():
    """Get rich analytics summary for dashboard and chart rendering."""
    summary = database.get_analytics_summary()
    return jsonify({"status": "success", "analytics": summary})

@app.route('/api/train', methods=['POST'])
@login_required
def api_train_model():
    ok, msg = engine.train_model()
    return jsonify({"status": "success" if ok else "error", "message": msg})

if __name__ == '__main__':
    database.init_db()
    engine.load_model()
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG)


