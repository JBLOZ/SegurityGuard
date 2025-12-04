"""
Modelos de base de datos
"""
from .base import Base, engine, SessionLocal, get_db, init_db
from .person import Person, PersonCategory
from .detection_event import DetectionEvent

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "get_db",
    "init_db",
    "Person",
    "PersonCategory",
    "DetectionEvent"
]
