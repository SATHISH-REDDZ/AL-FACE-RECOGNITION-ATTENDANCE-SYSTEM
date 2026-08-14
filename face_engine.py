import os
import json
import base64
import urllib.request
from datetime import datetime
import cv2
import numpy as np
from PIL import Image
import config
import database

def get_haar_cascade_path():
    """Ensure Haar Cascade XML file exists, downloading if necessary."""
    local_path = os.path.join(config.BASE_DIR, "models", "haarcascade_frontalface_default.xml")
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return local_path

    try:
        cv_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if os.path.exists(cv_path) and os.path.getsize(cv_path) > 0:
            return cv_path
    except Exception:
        pass

    url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        urllib.request.urlretrieve(url, local_path)
        return local_path
    except Exception as e:
        print(f"Error downloading Haar Cascade XML: {e}")
        return local_path

class FaceRecognitionEngine:
    def __init__(self):
        cascade_path = get_haar_cascade_path()
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            raise RuntimeError(
                "OpenCV LBPH module not found. Please ensure opencv-contrib-python is installed."
            )
            
        self.is_trained = False
        self.label_map = {}  # Maps int LBPH labels to student_id strings
        self.inverse_label_map = {}
        self.last_recognized_notification = None
        
        self.load_model()

    def detect_faces(self, gray_frame):
        """Detect faces in a grayscale image frame."""
        faces = self.face_cascade.detectMultiScale(
            gray_frame,
            scaleFactor=1.2,
            minNeighbors=5,
            minSize=(80, 80)
        )
        return faces

    def train_model(self):
        """
        Train LBPH model using all images in DATASET_DIR.
        Saves model to MODEL_PATH, labels to LABELS_PATH, and metadata to METADATA_PATH.
        """
        image_paths = []
        for root, _, files in os.walk(config.DATASET_DIR):
            for file in files:
                if file.endswith((".jpg", ".png", ".jpeg")):
                    image_paths.append(os.path.join(root, file))

        if not image_paths:
            self.is_trained = False
            return False, "No training dataset found."

        face_samples = []
        ids = []
        label_counter = 1
        self.label_map = {}
        self.inverse_label_map = {}

        for path in image_paths:
            filename = os.path.basename(path)
            parts = filename.split('_')
            if len(parts) < 2:
                continue
            student_id = parts[0]

            if student_id not in self.inverse_label_map:
                self.inverse_label_map[student_id] = label_counter
                self.label_map[label_counter] = student_id
                label_counter += 1

            int_id = self.inverse_label_map[student_id]

            pil_img = Image.open(path).convert('L')
            img_numpy = np.array(pil_img, 'uint8')

            faces = self.detect_faces(img_numpy)
            for (x, y, w, h) in faces:
                face_samples.append(img_numpy[y:y+h, x:x+w])
                ids.append(int_id)

        if not face_samples:
            self.is_trained = False
            return False, "No valid face samples detected in dataset images."

        self.recognizer.train(face_samples, np.array(ids))
        self.recognizer.save(config.MODEL_PATH)
        self.is_trained = True

        # Persist label mapping to labels.json
        try:
            with open(config.LABELS_PATH, 'w') as f:
                json.dump(self.label_map, f, indent=2)
        except Exception as e:
            print(f"Error saving labels.json: {e}")

        # Persist metadata.json
        metadata = {
            "model": "LBPH",
            "trained_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "student_count": len(self.label_map),
            "sample_count": len(face_samples)
        }
        try:
            with open(config.METADATA_PATH, 'w') as f:
                json.dump(metadata, f, indent=2)
        except Exception as e:
            print(f"Error saving metadata.json: {e}")

        return True, f"Successfully trained on {len(face_samples)} face samples across {len(self.label_map)} students."

    def load_model(self):
        """Load trained LBPH model and persisted labels.json if present."""
        if os.path.exists(config.MODEL_PATH):
            try:
                self.recognizer.read(config.MODEL_PATH)
                self.is_trained = True
                
                # Load persisted label mapping from JSON
                if os.path.exists(config.LABELS_PATH):
                    with open(config.LABELS_PATH, 'r') as f:
                        raw_map = json.load(f)
                        self.label_map = {int(k): v for k, v in raw_map.items()}
                        self.inverse_label_map = {v: int(k) for k, v in raw_map.items()}
                else:
                    # Fallback to dataset directory reconstruction
                    label_counter = 1
                    self.label_map = {}
                    self.inverse_label_map = {}
                    for root, _, files in os.walk(config.DATASET_DIR):
                        for file in files:
                            if file.endswith((".jpg", ".png", ".jpeg")):
                                filename = os.path.basename(file)
                                parts = filename.split('_')
                                if len(parts) >= 2:
                                    student_id = parts[0]
                                    if student_id not in self.inverse_label_map:
                                        self.inverse_label_map[student_id] = label_counter
                                        self.label_map[label_counter] = student_id
                                        label_counter += 1
            except Exception as e:
                print(f"Warning: Could not load trained model: {e}")
                self.is_trained = False


    def save_face_samples(self, student_id, frame, count):
        """
        Save a cropped face sample for a student dataset with quality controls:
        - Rejects 0 faces or >1 faces in enrollment frame
        - Evaluates face blurriness via Laplacian variance
        - Evaluates lighting conditions via mean gray brightness
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detect_faces(gray)

        if len(faces) == 0:
            return False, "No face detected in frame. Position your face clearly."

        if len(faces) > 1:
            return False, "Multiple faces detected (found " + str(len(faces)) + "). Only 1 person must be in frame during enrollment."

        (x, y, w, h) = faces[0]

        if w < 90 or h < 90:
            return False, "Face is too far from camera. Please move closer."

        face_crop = gray[y:y+h, x:x+w]

        # Blur check via Laplacian variance
        laplacian_var = cv2.Laplacian(face_crop, cv2.CV_64F).var()
        if laplacian_var < 35.0:
            return False, f"Image too blurry (sharpness score {laplacian_var:.1f}). Hold steady."

        # Brightness check
        brightness = np.mean(face_crop)
        if brightness < 30:
            return False, "Lighting is too dark. Increase ambient lighting."
        if brightness > 230:
            return False, "Lighting is overexposed. Reduce direct glare."

        face_crop = cv2.resize(face_crop, (200, 200))

        student_dir = os.path.join(config.DATASET_DIR, student_id)
        os.makedirs(student_dir, exist_ok=True)
        file_path = os.path.join(student_dir, f"{student_id}_{count}.jpg")
        cv2.imwrite(file_path, face_crop)
        return True, file_path


    def process_frame(self, frame):
        """
        Process incoming video frame:
        Detect faces, recognize trained faces, draw bounding boxes & annotations,
        and trigger automatic attendance logging.
        Returns: annotated_frame, active_notifications list
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detect_faces(gray)
        notifications = []

        for (x, y, w, h) in faces:
            name_display = "Unknown"
            color = (0, 0, 255) # Red for unknown
            confidence_str = ""

            if self.is_trained:
                face_crop = gray[y:y+h, x:x+w]
                try:
                    label, confidence = self.recognizer.predict(face_crop)
                    # Note: LBPH distance score: lower score means higher match (0 = exact match)
                    if confidence < config.CONFIDENCE_THRESHOLD and label in self.label_map:
                        student_id = self.label_map[label]
                        student_info = database.get_student_by_id(student_id)
                        if student_info:
                            name_display = student_info["name"]
                            color = (0, 255, 0) # Green for match
                            match_percent = max(0, round(100 - confidence))
                            confidence_str = f"{match_percent}% match"

                            # Attempt to mark attendance
                            marked, msg, _ = database.mark_attendance(student_id)
                            if marked:
                                notif = {
                                    "status": "success",
                                    "message": f"Attendance marked for {student_info['name']} ({student_id})"
                                }
                                notifications.append(notif)
                                self.last_recognized_notification = notif
                except Exception as e:
                    print(f"Error predicting face: {e}")

            # Draw stylish rounded rectangle corners & background label
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
            # Label background box
            label_text = f"{name_display} {confidence_str}".strip()
            (text_w, text_h), _ = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(frame, (x, y - 28), (x + max(text_w + 10, w), y), color, -1)
            cv2.putText(frame, label_text, (x + 5, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        return frame, notifications

    def process_base64_frame(self, b64_string):
        """
        Process base64 image frame sent from client browser webcam:
        Decodes image, performs face recognition, marks attendance,
        and returns annotated base64 image string + notification payload.
        """
        try:
            if ',' in b64_string:
                b64_string = b64_string.split(',')[1]
            img_bytes = base64.b64decode(b64_string)
            nparr = np.frombuffer(img_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if frame is None:
                return None, [], "Invalid image format."

            annotated_frame, notifications = self.process_frame(frame)

            # Re-encode to JPEG base64
            _, buffer = cv2.imencode('.jpg', annotated_frame)
            encoded_img = base64.b64encode(buffer).decode('utf-8')
            res_b64 = f"data:image/jpeg;base64,{encoded_img}"

            return res_b64, notifications, None
        except Exception as e:
            return None, [], str(e)

# Create singleton engine instance
engine = FaceRecognitionEngine()

