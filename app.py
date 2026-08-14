import os
import cv2
import base64
import numpy as np
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, session
from functools import wraps
import io
import pandas as pd
import config
import database
from face_engine import engine
import analytics_engine

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            if request.is_json or request.path.startswith('/api/'):
                return jsonify({"status": "error", "message": "Authentication required. Please log in."}), 401
            return redirect(url_for('login_view', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login', methods=['GET', 'POST'])
def login_view():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = database.verify_user(username, password)
        if user:
            session['user'] = user
            next_page = request.args.get('next') or url_for('index')
            return redirect(next_page)
        return render_template('login.html', error="Invalid username or password.")
    
    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
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
def api_stats():
    stats = database.get_stats()
    stats["model_trained"] = engine.is_trained
    return jsonify(stats)

@app.route('/api/students', methods=['GET'])
def api_get_students():
    students = database.get_all_students()
    return jsonify({"status": "success", "students": students})

@app.route('/api/students', methods=['POST'])
def api_add_student():
    data = request.get_json() or {}
    student_id = data.get('student_id', '').strip()
    name = data.get('name', '').strip()
    department = data.get('department', '').strip()
    email = data.get('email', '').strip()
    photos = data.get('photos', []) # List of base64 images

    if not student_id or not name or not department:
        return jsonify({"status": "error", "message": "Student ID, Name, and Department are required."}), 400

    # Save to database
    success, msg = database.add_student(student_id, name, department, email)
    if not success:
        return jsonify({"status": "error", "message": msg}), 400

    # Save photos if provided
    saved_count = 0
    if photos:
        for idx, b64_img in enumerate(photos):
            try:
                # Remove header if present (e.g. data:image/jpeg;base64,)
                if ',' in b64_img:
                    b64_img = b64_img.split(',')[1]
                img_bytes = base64.b64decode(b64_img)
                nparr = np.frombuffer(img_bytes, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

                if img is not None:
                    ok, _ = engine.save_face_samples(student_id, img, idx + 1)
                    if ok:
                        saved_count += 1
            except Exception as e:
                print(f"Error processing base64 image: {e}")

    # Retrain engine automatically
    train_ok, train_msg = engine.train_model()

    return jsonify({
        "status": "success",
        "message": f"Student registered successfully. Saved {saved_count} face samples.",
        "training": train_msg
    })

@app.route('/api/students/capture_webcam', methods=['POST'])
def api_capture_webcam_dataset():
    """Capture sample photos directly from active server webcam for a student."""
    data = request.get_json() or {}
    student_id = data.get('student_id', '').strip()
    name = data.get('name', '').strip()
    department = data.get('department', '').strip()
    email = data.get('email', '').strip()
    num_samples = int(data.get('num_samples', 20))

    if not student_id or not name or not department:
        return jsonify({"status": "error", "message": "Student ID, Name, and Department are required."}), 400

    database.add_student(student_id, name, department, email)

    cam = get_camera()
    count = 0
    attempts = 0

    while count < num_samples and attempts < num_samples * 5:
        attempts += 1
        ret, frame = cam.read()
        if not ret:
            break

        ok, _ = engine.save_face_samples(student_id, frame, count + 1)
        if ok:
            count += 1
        cv2.waitKey(50)

    train_ok, train_msg = engine.train_model()

    return jsonify({
        "status": "success",
        "message": f"Captured {count} face samples for {name}.",
        "training": train_msg
    })

@app.route('/api/students/<student_id>', methods=['DELETE'])
def api_delete_student(student_id):
    database.delete_student(student_id)
    # Remove dataset folder
    student_dir = os.path.join(config.DATASET_DIR, student_id)
    if os.path.exists(student_dir):
        import shutil
        shutil.rmtree(student_dir)
    # Retrain model
    engine.train_model()
    return jsonify({"status": "success", "message": f"Student {student_id} deleted."})

@app.route('/api/attendance', methods=['GET'])
def api_get_attendance():
    date_filter = request.args.get('date')
    department_filter = request.args.get('department')
    search = request.args.get('search')

    logs = database.get_attendance_logs(date_filter, department_filter, search)
    return jsonify({"status": "success", "logs": logs})

@app.route('/api/attendance/export', methods=['GET'])
def api_export_attendance():
    date_filter = request.args.get('date')
    department_filter = request.args.get('department')

    logs = database.get_attendance_logs(date_filter, department_filter)
    if not logs:
        # Export empty structure
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

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Attendance')
    
    # Or fallback to CSV if openpyxl isn't available
    output.seek(0)
    csv_data = df.to_csv(index=False)
    
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename=attendance_report_{date_filter or 'all'}.csv"}
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


