import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_DIR = os.path.join(DATA_DIR, "dataset")
TRAINER_DIR = os.path.join(DATA_DIR, "trainer")
DB_PATH = os.path.join(DATA_DIR, "attendance.db")
MODEL_PATH = os.path.join(TRAINER_DIR, "trainer.yml")
LABELS_PATH = os.path.join(TRAINER_DIR, "labels.json")
METADATA_PATH = os.path.join(TRAINER_DIR, "metadata.json")
HAAR_CASCADE_PATH = os.path.join(BASE_DIR, "models", "haarcascade_frontalface_default.xml")

# Face Engine Configurations
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CONFIDENCE_THRESHOLD = 75  # Lower distance metric means higher match confidence in LBPH
COOLDOWN_SECONDS = 300     # 5 minutes cooldown before re-marking attendance for same user

# Security & Server Configurations
SECRET_KEY = os.getenv("SECRET_KEY", "vision_attendance_secret_key_2026_prod_secure")
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
DEBUG = os.getenv("FLASK_DEBUG", "True").lower() in ("true", "1", "yes")

# Ensure essential directories exist
for folder in [DATA_DIR, DATASET_DIR, TRAINER_DIR, os.path.dirname(HAAR_CASCADE_PATH)]:
    os.makedirs(folder, exist_ok=True)

