"""
Módulo de matching de caras
Compara embeddings usando similitud coseno
"""
import numpy as np
from typing import Optional
from dataclasses import dataclass

from config import FACE_RECOGNITION_THRESHOLD


@dataclass
class MatchResult:
    """Resultado de una comparación de caras."""
    person_id: int
    person_name: str
    similarity: float
    category: str
    is_match: bool
    
    @property
    def confidence_percent(self) -> float:
        """Retorna la similitud como porcentaje."""
        return self.similarity * 100


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Calcula la similitud coseno entre dos vectores.
    
    Args:
        a: Primer vector
        b: Segundo vector
        
    Returns:
        Similitud coseno (0-1)
    """
    # Asegurar que son arrays numpy
    a = np.asarray(a).flatten()
    b = np.asarray(b).flatten()
    
    # Calcular producto punto
    dot_product = np.dot(a, b)
    
    # Calcular normas
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    # Evitar división por cero
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    # Calcular similitud
    similarity = dot_product / (norm_a * norm_b)
    
    # Normalizar a rango [0, 1]
    return float((similarity + 1) / 2)


class FaceMatcher:
    """Compara embeddings de caras con una base de datos."""
    
    def __init__(self, threshold: float = FACE_RECOGNITION_THRESHOLD):
        """
        Inicializa el matcher de caras.
        
        Args:
            threshold: Umbral de similitud para considerar match (0-1)
        """
        self.threshold = threshold
        self._known_faces: dict[int, dict] = {}  # Cache en memoria
    
    def add_known_face(
        self,
        person_id: int,
        name: str,
        embedding: np.ndarray,
        category: str = "known"
    ):
        """
        Añade una cara conocida al cache.
        
        Args:
            person_id: ID de la persona en la BD
            name: Nombre de la persona
            embedding: Vector de embedding
            category: Categoría (known, delivery, unknown)
        """
        self._known_faces[person_id] = {
            "name": name,
            "embedding": np.asarray(embedding),
            "category": category
        }
    
    def remove_known_face(self, person_id: int):
        """Elimina una cara del cache."""
        if person_id in self._known_faces:
            del self._known_faces[person_id]
    
    def clear_cache(self):
        """Limpia el cache de caras conocidas."""
        self._known_faces.clear()
    
    def find_match(
        self,
        embedding: np.ndarray,
        threshold: Optional[float] = None
    ) -> Optional[MatchResult]:
        """
        Busca la cara más similar en el cache.
        
        Args:
            embedding: Embedding de la cara a buscar
            threshold: Umbral de similitud (usa el default si no se especifica)
            
        Returns:
            MatchResult si encuentra una coincidencia, None si no
        """
        if not self._known_faces:
            return None
        
        threshold = threshold or self.threshold
        embedding = np.asarray(embedding)
        
        best_match = None
        best_similarity = 0.0
        
        for person_id, data in self._known_faces.items():
            similarity = cosine_similarity(embedding, data["embedding"])
            
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = MatchResult(
                    person_id=person_id,
                    person_name=data["name"],
                    similarity=similarity,
                    category=data["category"],
                    is_match=similarity >= threshold
                )
        
        # Solo retornar si supera el umbral
        if best_match and best_match.is_match:
            return best_match
        
        return None
    
    def find_all_matches(
        self,
        embedding: np.ndarray,
        top_k: int = 5
    ) -> list[MatchResult]:
        """
        Encuentra las top-k caras más similares.
        
        Args:
            embedding: Embedding de la cara a buscar
            top_k: Número máximo de resultados
            
        Returns:
            Lista de MatchResult ordenados por similitud
        """
        if not self._known_faces:
            return []
        
        embedding = np.asarray(embedding)
        results = []
        
        for person_id, data in self._known_faces.items():
            similarity = cosine_similarity(embedding, data["embedding"])
            
            results.append(MatchResult(
                person_id=person_id,
                person_name=data["name"],
                similarity=similarity,
                category=data["category"],
                is_match=similarity >= self.threshold
            ))
        
        # Ordenar por similitud descendente
        results.sort(key=lambda x: x.similarity, reverse=True)
        
        return results[:top_k]
    
    def compare_faces(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray
    ) -> float:
        """
        Compara dos embeddings directamente.
        
        Args:
            embedding1: Primer embedding
            embedding2: Segundo embedding
            
        Returns:
            Similitud (0-1)
        """
        return cosine_similarity(embedding1, embedding2)
    
    def get_stats(self) -> dict:
        """Retorna estadísticas del cache."""
        categories = {}
        for data in self._known_faces.values():
            cat = data["category"]
            categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "total_faces": len(self._known_faces),
            "categories": categories,
            "threshold": self.threshold
        }


# Instancia global
face_matcher = FaceMatcher()
