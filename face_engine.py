import os
import urllib.request
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

    # Try default opencv path
    try:
        cv_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if os.path.exists(cv_path) and os.path.getsize(cv_path) > 0:
            return cv_path
    except Exception:
        pass

    # Download from official OpenCV GitHub repository if not present locally
    url = "https://raw.githubusercontent.com/opencv/opencv/master/data/haarcascades/haarcascade_frontalface_default.xml"
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    try:
        print(f"Downloading Haar Cascade XML from {url}...")
        urllib.request.urlretrieve(url, local_path)
        return local_path
    except Exception as e:
        print(f"Error downloading Haar Cascade XML: {e}")
        return local_path

class FaceRecognitionEngine:
    def __init__(self):
        cascade_path = get_haar_cascade_path()
        self.face_cascade = cv2.CascadeClassifier(cascade_path)

        
        # Initialize LBPH Face Recognizer
        try:
            self.recognizer = cv2.face.LBPHFaceRecognizer_create()
        except AttributeError:
            raise RuntimeError(
                "OpenCV LBPH module not found. Please ensure opencv-contrib-python is installed."
            )
            
        self.is_trained = False
        self.label_map = {}  # Maps integer LBPH labels to student_id strings
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
        Saves model file to MODEL_PATH and updates label mappings.
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
            # Filename pattern: StudentID_sampleNum.jpg
            parts = filename.split('_')
            if len(parts) < 2:
                continue
            student_id = parts[0]

            if student_id not in self.inverse_label_map:
                self.inverse_label_map[student_id] = label_counter
                self.label_map[label_counter] = student_id
                label_counter += 1

            int_id = self.inverse_label_map[student_id]

            pil_img = Image.open(path).convert('L') # Convert to grayscale
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

        return True, f"Successfully trained on {len(face_samples)} face samples across {len(self.label_map)} students."

    def load_model(self):
        """Load trained LBPH model if file exists."""
        if os.path.exists(config.MODEL_PATH):
            try:
                self.recognizer.read(config.MODEL_PATH)
                self.is_trained = True
                
                # Build label map based on existing dataset files
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
        """Save a cropped face sample for a student dataset."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detect_faces(gray)

        if len(faces) == 0:
            return False, "No face detected in frame."

        # Take largest face
        (x, y, w, h) = max(faces, key=lambda b: b[2] * b[3])
        face_crop = gray[y:y+h, x:x+w]
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

# Create singleton engine instance
engine = FaceRecognitionEngine()
