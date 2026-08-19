import os
import secrets
from dotenv import load_dotenv

# Load .env file if present
load_dotenv()

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_DIR = os.path.join(DATA_DIR, "dataset")
TRAINER_DIR = os.path.join(DATA_DIR, "trainer")
DB_PATH = os.path.join(DATA_DIR, "attendance.db")
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH}")
MODEL_PATH = os.path.join(TRAINER_DIR, "trainer.yml")
LABELS_PATH = os.path.join(TRAINER_DIR, "labels.json")
METADATA_PATH = os.path.join(TRAINER_DIR, "metadata.json")
HAAR_CASCADE_PATH = os.path.join(BASE_DIR, "models", "haarcascade_frontalface_default.xml")

# Face Engine Configurations & Model Versioning
MODEL_VERSION = "1.0.0"
FACE_ALGORITHM = "LBPH"
CAMERA_INDEX = int(os.getenv("CAMERA_INDEX", 0))
FRAME_WIDTH = int(os.getenv("FRAME_WIDTH", 640))
FRAME_HEIGHT = int(os.getenv("FRAME_HEIGHT", 480))
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", 75)) # Lower distance metric means higher match confidence in LBPH
COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", 300))     # Cooldown before re-marking attendance for same student

# Admin Authentication Config
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") # Must be provided in .env or setup

# Security & Server Configurations
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 5000))
# Default to False in production for security, unless FLASK_DEBUG is explicitly enabled
DEBUG = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "yes")

# Ensure essential directories exist
for folder in [DATA_DIR, DATASET_DIR, TRAINER_DIR, os.path.dirname(HAAR_CASCADE_PATH)]:
    os.makedirs(folder, exist_ok=True)



