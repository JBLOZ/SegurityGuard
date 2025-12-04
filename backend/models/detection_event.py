"""
Modelo de Evento de Detección
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from .base import Base


class DetectionEvent(Base):
    """Modelo de evento de detección en la base de datos."""
    
    __tablename__ = "detection_events"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    person_id = Column(Integer, ForeignKey("persons.id", ondelete="SET NULL"), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    video_frame_path = Column(String(255), nullable=True)
    face_crop_path = Column(String(255), nullable=True)
    confidence = Column(Float, nullable=True)
    allowed = Column(Boolean, nullable=True)
    saved_to_db = Column(Boolean, default=False)
    action_taken = Column(String(20), default="pending")  # allowed, denied, pending, timeout
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relación con persona
    person = relationship("Person", back_populates="detection_events")
    
    def __repr__(self):
        return f"<DetectionEvent(id={self.id}, person_id={self.person_id}, action='{self.action_taken}')>"
    
    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "person_id": self.person_id,
            "person_name": self.person.name if self.person else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "confidence": self.confidence,
            "allowed": self.allowed,
            "action_taken": self.action_taken,
            "face_crop_path": self.face_crop_path
        }
