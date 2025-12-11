"""
Reconocedor Facial Geométrico
Basado en ratios faciales, no en redes neuronales.
Ultra-ligero para Raspberry Pi.
"""
import numpy as np
import json
from dataclasses import dataclass
from typing import Optional
from pathlib import Path


@dataclass
class GeometricProfile:
    """Perfil geométrico de una persona."""
    person_id: int
    name: str
    ratios: list[float]  # 4 ratios geométricos
    
    def to_dict(self) -> dict:
        return {
            "person_id": self.person_id,
            "name": self.name,
            "ratios": self.ratios
        }


class GeometricRecognizer:
    """
    Reconocimiento facial basado en geometría.
    
    Usa 4 ratios simples:
    1. eye_ratio: distancia_ojos / ancho_cara
    2. face_ratio: altura_ojos_boca / altura_cara
    3. mouth_ratio: ancho_estimado_boca / distancia_ojos
    4. nose_ratio: distancia_nariz_barbilla / altura_cara
    
    Ventajas:
    - No requiere GPU
    - ~1ms por comparación
    - Funciona en Raspberry Pi
    """
    
    def __init__(self, tolerance: float = 0.15):
        """
        Args:
            tolerance: Margen de tolerancia para matching (0.15 = 15%)
        """
        self.tolerance = tolerance
        self._known_profiles: dict[int, GeometricProfile] = {}
        self._profiles_file = Path("data/geometric_profiles.json")
        
        # Cargar perfiles guardados
        self._load_profiles()
        
        print(f"GeometricRecognizer inicializado (tolerancia: {tolerance*100:.0f}%)")
    
    def extract_ratios(self, landmarks: dict) -> Optional[list[float]]:
        """
        Extrae los 4 ratios geométricos de los landmarks.
        
        Args:
            landmarks: Dict con left_eye, right_eye, mouth, nose, chin
            
        Returns:
            Lista de 4 ratios o None si landmarks incompletos
        """
        required = ["left_eye", "right_eye", "mouth", "chin"]
        if not landmarks or not all(k in landmarks for k in required):
            return None
        
        left_eye = np.array(landmarks["left_eye"])
        right_eye = np.array(landmarks["right_eye"])
        mouth = np.array(landmarks["mouth"])
        chin = np.array(landmarks["chin"])
        nose = np.array(landmarks.get("nose", (mouth + left_eye) / 2))
        
        # Calcular distancias
        eye_distance = np.linalg.norm(right_eye - left_eye)
        eyes_center = (left_eye + right_eye) / 2
        eye_to_mouth = np.linalg.norm(mouth - eyes_center)
        eye_to_chin = np.linalg.norm(chin - eyes_center)
        nose_to_chin = np.linalg.norm(chin - nose)
        
        # Evitar división por cero
        if eye_distance < 10 or eye_to_chin < 10:
            return None
        
        # Calcular ratios
        face_width = eye_distance * 2.2  # Aproximación ancho cara
        face_height = eye_to_chin
        
        ratios = [
            eye_distance / face_width,               # Ratio 1: ojos/ancho
            eye_to_mouth / face_height,              # Ratio 2: ojos-boca/altura
            (eye_distance * 0.6) / eye_distance,     # Ratio 3: boca/ojos (estimado)
            nose_to_chin / face_height               # Ratio 4: nariz-barbilla/altura
        ]
        
        return ratios
    
    def add_profile(self, person_id: int, name: str, ratios: list[float]):
        """Añade un perfil geométrico."""
        profile = GeometricProfile(
            person_id=person_id,
            name=name,
            ratios=ratios
        )
        self._known_profiles[person_id] = profile
        self._save_profiles()
        print(f"Perfil geométrico guardado: {name}")
    
    def remove_profile(self, person_id: int):
        """Elimina un perfil."""
        if person_id in self._known_profiles:
            del self._known_profiles[person_id]
            self._save_profiles()
    
    def find_match(self, ratios: list[float]) -> Optional[GeometricProfile]:
        """
        Busca un perfil que coincida con los ratios dados.
        
        Args:
            ratios: Lista de 4 ratios a comparar
            
        Returns:
            GeometricProfile si encuentra match, None si no
        """
        if not ratios or len(ratios) != 4:
            return None
        
        best_match = None
        best_distance = float('inf')
        
        for profile in self._known_profiles.values():
            # Calcular distancia euclidiana normalizada
            distance = self._compare_ratios(ratios, profile.ratios)
            
            if distance < self.tolerance and distance < best_distance:
                best_distance = distance
                best_match = profile
        
        return best_match
    
    def _compare_ratios(self, ratios1: list[float], ratios2: list[float]) -> float:
        """Calcula la diferencia promedio entre dos conjuntos de ratios."""
        if len(ratios1) != len(ratios2):
            return float('inf')
        
        differences = [abs(r1 - r2) for r1, r2 in zip(ratios1, ratios2)]
        return sum(differences) / len(differences)
    
    def _save_profiles(self):
        """Guarda perfiles en archivo JSON."""
        self._profiles_file.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            str(pid): profile.to_dict() 
            for pid, profile in self._known_profiles.items()
        }
        
        with open(self._profiles_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def _load_profiles(self):
        """Carga perfiles desde archivo JSON."""
        if not self._profiles_file.exists():
            return
        
        try:
            with open(self._profiles_file, 'r') as f:
                data = json.load(f)
            
            for pid_str, profile_data in data.items():
                profile = GeometricProfile(
                    person_id=int(pid_str),
                    name=profile_data["name"],
                    ratios=profile_data["ratios"]
                )
                self._known_profiles[int(pid_str)] = profile
            
            print(f"Cargados {len(self._known_profiles)} perfiles geométricos")
        except Exception as e:
            print(f"Error cargando perfiles: {e}")
    
    def get_stats(self) -> dict:
        """Retorna estadísticas."""
        return {
            "total_profiles": len(self._known_profiles),
            "tolerance": self.tolerance,
            "profiles": [p.name for p in self._known_profiles.values()]
        }


# Instancia global
geometric_recognizer = GeometricRecognizer()
