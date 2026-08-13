import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_DIR = os.path.join(DATA_DIR, "dataset")
TRAINER_DIR = os.path.join(DATA_DIR, "trainer")
DB_PATH = os.path.join(DATA_DIR, "attendance.db")
MODEL_PATH = os.path.join(TRAINER_DIR, "trainer.yml")
HAAR_CASCADE_PATH = os.path.join(BASE_DIR, "models", "haarcascade_frontalface_default.xml")

# Face Engine Configurations
CAMERA_INDEX = 0
FRAME_WIDTH = 640
FRAME_HEIGHT = 480
CONFIDENCE_THRESHOLD = 75  # Lower distance metric means higher match confidence in LBPH
COOLDOWN_SECONDS = 300     # 5 minutes cooldown before re-marking attendance for same user

# Server Configurations
HOST = "0.0.0.0"
PORT = 5000
DEBUG = True

# Ensure essential directories exist
for folder in [DATA_DIR, DATASET_DIR, TRAINER_DIR, os.path.dirname(HAAR_CASCADE_PATH)]:
    os.makedirs(folder, exist_ok=True)
