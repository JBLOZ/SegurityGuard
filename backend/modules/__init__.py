"""
Archivo __init__ para el paquete modules
"""
from .video_capture import VideoCapture, video_capture, generate_mjpeg_stream
from .yolo_detector import YOLODetector, yolo_detector, Detection
from .face_recognizer import FaceRecognizer, face_recognizer, Face
from .face_matcher import FaceMatcher, face_matcher, MatchResult, cosine_similarity
from .db_handler import DatabaseHandler, db_handler, initialize_database

__all__ = [
    "VideoCapture",
    "video_capture", 
    "generate_mjpeg_stream",
    "YOLODetector",
    "yolo_detector",
    "Detection",
    "FaceRecognizer",
    "face_recognizer",
    "Face",
    "FaceMatcher",
    "face_matcher",
    "MatchResult",
    "cosine_similarity",
    "DatabaseHandler",
    "db_handler",
    "initialize_database"
]
