"""
Configuración del Sistema de Seguridad del Hogar
"""
import os
from pathlib import Path

# Rutas base
BASE_DIR = Path(__file__).parent
PROJECT_ROOT = BASE_DIR.parent
DATA_DIR = PROJECT_ROOT / "data"
MODELS_DIR = DATA_DIR / "models"
FACES_DIR = DATA_DIR / "faces"
EVENTS_DIR = DATA_DIR / "events"

# Crear directorios si no existen
for dir_path in [DATA_DIR, MODELS_DIR, FACES_DIR, EVENTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# Configuración de cámara
CAMERA_SOURCE = os.getenv("CAMERA_SOURCE", 0)  # 0 = webcam USB, o URL RTSP
CAMERA_WIDTH = int(os.getenv("CAMERA_WIDTH", 1280))
CAMERA_HEIGHT = int(os.getenv("CAMERA_HEIGHT", 720))
CAMERA_FPS = int(os.getenv("CAMERA_FPS", 30))

# Configuración de YOLO
YOLO_MODEL = os.getenv("YOLO_MODEL", "yolov8n.pt")  # Modelo nano para velocidad
YOLO_CONFIDENCE = float(os.getenv("YOLO_CONFIDENCE", 0.5))
YOLO_DEVICE = os.getenv("YOLO_DEVICE", "cuda")  # Usar GPU RTXi hay GPU

# Configuración de reconocimiento facial
FACE_RECOGNITION_THRESHOLD = float(os.getenv("FACE_RECOGNITION_THRESHOLD", 0.6))
FACE_EMBEDDING_SIZE = 512

# Configuración de base de datos
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"sqlite:///{PROJECT_ROOT / 'database' / 'security.db'}"
)

# Configuración de Flask
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", 5001))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Configuración de alertas
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "es")  # Español
ALERT_SOUND_ENABLED = os.getenv("ALERT_SOUND_ENABLED", "True").lower() == "true"

# Categorías de personas
PERSON_CATEGORIES = ["known", "delivery", "unknown"]
