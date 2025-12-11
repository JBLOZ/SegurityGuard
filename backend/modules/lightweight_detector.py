"""
Detector Ultra-Ligero con Haar Cascades + Landmarks
Para Raspberry Pi y dispositivos de bajo consumo
"""
import cv2
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class Detection:
    """Detección de persona/cara."""
    x: int
    y: int
    width: int
    height: int
    confidence: float = 1.0
    label: str = "person"
    landmarks: Optional[dict] = None
    
    @property
    def bbox(self) -> tuple:
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> tuple:
        return (self.x + self.width // 2, self.y + self.height // 2)


class LightweightDetector:
    """
    Detector ultra-ligero usando Haar Cascades.
    Consume ~5% CPU en Raspberry Pi 4.
    """
    
    def __init__(self):
        # Cargar cascadas pre-entrenadas (incluidas en OpenCV)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        self.eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        
        # Parámetros optimizados para velocidad
        self.scale_factor = 1.2  # Más alto = más rápido
        self.min_neighbors = 4   # Más alto = menos falsos positivos
        self.min_size = (60, 60) # Tamaño mínimo de cara
        
        # Contador de frames (para procesar 1 de cada N)
        self.frame_count = 0
        self.process_every_n = 5  # Procesar 1 de cada 5 frames
        
        # Cache de última detección
        self._last_detections: list[Detection] = []
        
        print("LightweightDetector inicializado (Haar Cascades)")
    
    def detect(self, frame: np.ndarray) -> list[Detection]:
        """
        Detecta caras en el frame.
        Solo procesa 1 de cada N frames para ahorrar CPU.
        """
        self.frame_count += 1
        
        # Usar cache si no toca procesar
        if self.frame_count % self.process_every_n != 0:
            return self._last_detections
        
        # Convertir a escala de grises
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detectar caras
        faces = self.face_cascade.detectMultiScale(
            gray,
            scaleFactor=self.scale_factor,
            minNeighbors=self.min_neighbors,
            minSize=self.min_size
        )
        
        detections = []
        for (x, y, w, h) in faces:
            # Detectar ojos dentro de la cara para extraer landmarks
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 3)
            
            landmarks = None
            if len(eyes) >= 2:
                # Ordenar ojos por posición X (izquierdo primero)
                eyes = sorted(eyes, key=lambda e: e[0])
                left_eye = (x + eyes[0][0] + eyes[0][2]//2, y + eyes[0][1] + eyes[0][3]//2)
                right_eye = (x + eyes[1][0] + eyes[1][2]//2, y + eyes[1][1] + eyes[1][3]//2)
                
                # Estimar posición de boca (2/3 abajo de la cara)
                mouth_y = y + int(h * 0.75)
                mouth_center = (x + w//2, mouth_y)
                
                landmarks = {
                    "left_eye": left_eye,
                    "right_eye": right_eye,
                    "mouth": mouth_center,
                    "nose": (x + w//2, y + int(h * 0.55)),
                    "chin": (x + w//2, y + h)
                }
            
            detections.append(Detection(
                x=int(x),
                y=int(y),
                width=int(w),
                height=int(h),
                confidence=0.9,
                label="face",
                landmarks=landmarks
            ))
        
        self._last_detections = detections
        return detections
    
    def detect_and_draw(self, frame: np.ndarray) -> tuple[np.ndarray, list[Detection]]:
        """Detecta y dibuja bounding boxes."""
        detections = self.detect(frame)
        annotated = frame.copy()
        
        for det in detections:
            # Dibujar rectángulo
            cv2.rectangle(
                annotated,
                (det.x, det.y),
                (det.x + det.width, det.y + det.height),
                (0, 255, 0),  # Verde
                2
            )
            
            # Dibujar landmarks si existen
            if det.landmarks:
                for name, point in det.landmarks.items():
                    color = (255, 0, 0) if "eye" in name else (0, 0, 255)
                    cv2.circle(annotated, point, 3, color, -1)
            
            # Etiqueta
            cv2.putText(
                annotated,
                f"Face {det.confidence:.0%}",
                (det.x, det.y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )
        
        return annotated, detections


# Instancia global
lightweight_detector = LightweightDetector()
