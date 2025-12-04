"""
Manejador de base de datos
CRUD operations para personas y eventos de detección
"""
import json
import numpy as np
from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session

from models import SessionLocal, Person, DetectionEvent, init_db


class DatabaseHandler:
    """Manejador de operaciones de base de datos."""
    
    def __init__(self):
        """Inicializa el manejador."""
        self._session: Optional[Session] = None
    
    def get_session(self) -> Session:
        """Obtiene una sesión de base de datos."""
        if self._session is None or not self._session.is_active:
            self._session = SessionLocal()
        return self._session
    
    def close(self):
        """Cierra la sesión."""
        if self._session:
            self._session.close()
            self._session = None
    
    # ==================== PERSONAS ====================
    
    def create_person(
        self,
        name: str,
        embedding: Optional[np.ndarray] = None,
        photo_path: Optional[str] = None,
        category: str = "unknown",
        notes: Optional[str] = None
    ) -> Person:
        """
        Crea una nueva persona.
        
        Args:
            name: Nombre de la persona
            embedding: Vector de embedding (se serializa a JSON)
            photo_path: Ruta a la foto
            category: Categoría (known, delivery, unknown)
            notes: Notas adicionales
            
        Returns:
            Objeto Person creado
        """
        session = self.get_session()
        
        # Serializar embedding a JSON si existe
        embedding_json = None
        if embedding is not None:
            embedding_json = json.dumps(embedding.tolist())
        
        person = Person(
            name=name,
            embedding=embedding_json,
            photo_path=photo_path,
            category=category,
            notes=notes
        )
        
        session.add(person)
        session.commit()
        session.refresh(person)
        
        return person
    
    def get_person(self, person_id: int) -> Optional[Person]:
        """Obtiene una persona por ID."""
        session = self.get_session()
        return session.query(Person).filter(Person.id == person_id).first()
    
    def get_person_by_name(self, name: str) -> Optional[Person]:
        """Obtiene una persona por nombre."""
        session = self.get_session()
        return session.query(Person).filter(Person.name == name).first()
    
    def get_all_persons(self, category: Optional[str] = None) -> list[Person]:
        """
        Obtiene todas las personas.
        
        Args:
            category: Filtrar por categoría (opcional)
        """
        session = self.get_session()
        query = session.query(Person)
        
        if category:
            query = query.filter(Person.category == category)
        
        return query.all()
    
    def update_person(
        self,
        person_id: int,
        name: Optional[str] = None,
        embedding: Optional[np.ndarray] = None,
        photo_path: Optional[str] = None,
        category: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Optional[Person]:
        """Actualiza una persona existente."""
        session = self.get_session()
        person = session.query(Person).filter(Person.id == person_id).first()
        
        if not person:
            return None
        
        if name is not None:
            person.name = name
        if embedding is not None:
            person.embedding = json.dumps(embedding.tolist())
        if photo_path is not None:
            person.photo_path = photo_path
        if category is not None:
            person.category = category
        if notes is not None:
            person.notes = notes
        
        person.updated_at = datetime.utcnow()
        session.commit()
        session.refresh(person)
        
        return person
    
    def delete_person(self, person_id: int) -> bool:
        """Elimina una persona."""
        session = self.get_session()
        person = session.query(Person).filter(Person.id == person_id).first()
        
        if not person:
            return False
        
        session.delete(person)
        session.commit()
        return True
    
    def get_person_embedding(self, person_id: int) -> Optional[np.ndarray]:
        """Obtiene el embedding de una persona como numpy array."""
        person = self.get_person(person_id)
        if person and person.embedding:
            return np.array(json.loads(person.embedding))
        return None
    
    def get_all_embeddings(self) -> dict[int, dict]:
        """
        Obtiene todos los embeddings para cargar en el matcher.
        
        Returns:
            Dict con {person_id: {name, embedding, category}}
        """
        persons = self.get_all_persons()
        embeddings = {}
        
        for person in persons:
            if person.embedding:
                embeddings[person.id] = {
                    "name": person.name,
                    "embedding": np.array(json.loads(person.embedding)),
                    "category": person.category
                }
        
        return embeddings
    
    # ==================== EVENTOS DE DETECCIÓN ====================
    
    def create_detection_event(
        self,
        person_id: Optional[int] = None,
        video_frame_path: Optional[str] = None,
        face_crop_path: Optional[str] = None,
        confidence: Optional[float] = None,
        action_taken: str = "pending",
        notes: Optional[str] = None
    ) -> DetectionEvent:
        """Crea un nuevo evento de detección."""
        session = self.get_session()
        
        event = DetectionEvent(
            person_id=person_id,
            video_frame_path=video_frame_path,
            face_crop_path=face_crop_path,
            confidence=confidence,
            action_taken=action_taken,
            notes=notes
        )
        
        session.add(event)
        session.commit()
        session.refresh(event)
        
        return event
    
    def update_detection_event(
        self,
        event_id: int,
        allowed: Optional[bool] = None,
        action_taken: Optional[str] = None,
        saved_to_db: Optional[bool] = None
    ) -> Optional[DetectionEvent]:
        """Actualiza un evento de detección."""
        session = self.get_session()
        event = session.query(DetectionEvent).filter(DetectionEvent.id == event_id).first()
        
        if not event:
            return None
        
        if allowed is not None:
            event.allowed = allowed
        if action_taken is not None:
            event.action_taken = action_taken
        if saved_to_db is not None:
            event.saved_to_db = saved_to_db
        
        session.commit()
        session.refresh(event)
        
        return event
    
    def get_recent_events(self, limit: int = 50) -> list[DetectionEvent]:
        """Obtiene los eventos más recientes."""
        session = self.get_session()
        return session.query(DetectionEvent)\
            .order_by(DetectionEvent.timestamp.desc())\
            .limit(limit)\
            .all()
    
    def get_events_by_person(self, person_id: int) -> list[DetectionEvent]:
        """Obtiene todos los eventos de una persona."""
        session = self.get_session()
        return session.query(DetectionEvent)\
            .filter(DetectionEvent.person_id == person_id)\
            .order_by(DetectionEvent.timestamp.desc())\
            .all()
    
    def get_daily_stats(self) -> dict:
        """Obtiene estadísticas del día actual."""
        session = self.get_session()
        today = datetime.utcnow().date()
        
        events = session.query(DetectionEvent)\
            .filter(DetectionEvent.timestamp >= today)\
            .all()
        
        stats = {
            "total": len(events),
            "allowed": sum(1 for e in events if e.action_taken == "allowed"),
            "denied": sum(1 for e in events if e.action_taken == "denied"),
            "pending": sum(1 for e in events if e.action_taken == "pending")
        }
        
        return stats


# Instancia global
db_handler = DatabaseHandler()


def initialize_database():
    """Inicializa la base de datos y crea las tablas."""
    init_db()
    print("Base de datos lista")
