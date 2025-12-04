"""
Modelo de Persona para la base de datos
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.orm import relationship
import enum

from .base import Base


class PersonCategory(enum.Enum):
    """Categorías de personas."""
    KNOWN = "known"
    DELIVERY = "delivery"
    UNKNOWN = "unknown"


class Person(Base):
    """Modelo de persona en la base de datos."""
    
    __tablename__ = "persons"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    embedding = Column(Text, nullable=True)  # JSON string del vector
    photo_path = Column(String(255), nullable=True)
    category = Column(
        String(20), 
        default=PersonCategory.UNKNOWN.value
    )
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relación con eventos de detección
    detection_events = relationship("DetectionEvent", back_populates="person")
    
    def __repr__(self):
        return f"<Person(id={self.id}, name='{self.name}', category='{self.category}')>"
    
    def to_dict(self) -> dict:
        """Convierte el modelo a diccionario."""
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "photo_path": self.photo_path,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
