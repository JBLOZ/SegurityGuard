"""
Módulo de detección de personas con YOLOv8
"""
import cv2
import numpy as np
from typing import Optional
from dataclasses import dataclass
from ultralytics import YOLO

from config import YOLO_MODEL, YOLO_CONFIDENCE, YOLO_DEVICE, MODELS_DIR


@dataclass
class Detection:
    """Representa una detección de persona."""
    x: int  # Coordenada x del bounding box
    y: int  # Coordenada y del bounding box
    width: int  # Ancho del bounding box
    height: int  # Alto del bounding box
    confidence: float  # Confianza de la detección (0-1)
    class_id: int  # ID de clase (0 = person)
    class_name: str  # Nombre de clase
    
    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Retorna bounding box como (x, y, w, h)."""
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> tuple[int, int]:
        """Retorna el centro del bounding box."""
        return (self.x + self.width // 2, self.y + self.height // 2)
    
    @property
    def area(self) -> int:
        """Retorna el área del bounding box."""
        return self.width * self.height


class YOLODetector:
    """Detector de personas usando YOLOv8."""
    
    # ID de clase para 'person' en COCO
    PERSON_CLASS_ID = 0
    
    def __init__(
        self,
        model_name: str = YOLO_MODEL,
        confidence: float = YOLO_CONFIDENCE,
        device: str = YOLO_DEVICE
    ):
        """
        Inicializa el detector YOLO.
        
        Args:
            model_name: Nombre del modelo (yolov8n.pt, yolov8s.pt, etc.)
            confidence: Umbral de confianza mínimo
            device: Dispositivo (cpu, cuda, cuda:0)
        """
        self.model_name = model_name
        self.confidence = confidence
        self.device = device
        self.model: Optional[YOLO] = None
        
    def load_model(self) -> bool:
        """Carga el modelo YOLO."""
        try:
            # Intentar cargar desde directorio de modelos
            model_path = MODELS_DIR / self.model_name
            
            if model_path.exists():
                self.model = YOLO(str(model_path))
            else:
                # Descargar automáticamente
                print(f"Descargando modelo {self.model_name}...")
                self.model = YOLO(self.model_name)
                
            # Configurar dispositivo
            self.model.to(self.device)
            print(f"Modelo YOLO cargado: {self.model_name} en {self.device}")
            return True
            
        except Exception as e:
            print(f"Error cargando modelo YOLO: {e}")
            return False
    
    def detect(
        self,
        frame: np.ndarray,
        only_persons: bool = True
    ) -> list[Detection]:
        """
        Detecta objetos en un frame.
        
        Args:
            frame: Frame BGR de OpenCV
            only_persons: Si es True, solo retorna detecciones de personas
            
        Returns:
            Lista de detecciones
        """
        if self.model is None:
            if not self.load_model():
                return []
        
        # Ejecutar inferencia
        results = self.model(
            frame,
            conf=self.confidence,
            verbose=False
        )[0]
        
        detections = []
        
        for box in results.boxes:
            class_id = int(box.cls[0])
            
            # Filtrar solo personas si se especifica
            if only_persons and class_id != self.PERSON_CLASS_ID:
                continue
            
            # Extraer coordenadas
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            conf = float(box.conf[0])
            
            detection = Detection(
                x=x1,
                y=y1,
                width=x2 - x1,
                height=y2 - y1,
                confidence=conf,
                class_id=class_id,
                class_name=self.model.names[class_id]
            )
            
            detections.append(detection)
        
        return detections
    
    def detect_and_draw(
        self,
        frame: np.ndarray,
        color: tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
        show_label: bool = True
    ) -> tuple[np.ndarray, list[Detection]]:
        """
        Detecta personas y dibuja bounding boxes en el frame.
        
        Args:
            frame: Frame BGR de OpenCV
            color: Color del bounding box (BGR)
            thickness: Grosor de la línea
            show_label: Si muestra etiqueta con confianza
            
        Returns:
            Tuple de (frame con anotaciones, lista de detecciones)
        """
        detections = self.detect(frame)
        annotated_frame = frame.copy()
        
        for det in detections:
            # Dibujar rectángulo
            cv2.rectangle(
                annotated_frame,
                (det.x, det.y),
                (det.x + det.width, det.y + det.height),
                color,
                thickness
            )
            
            if show_label:
                # Etiqueta con nombre de clase y confianza
                label = f"{det.class_name}: {det.confidence:.2f}"
                
                # Tamaño del texto
                (text_width, text_height), baseline = cv2.getTextSize(
                    label,
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    1
                )
                
                # Fondo de la etiqueta
                cv2.rectangle(
                    annotated_frame,
                    (det.x, det.y - text_height - 10),
                    (det.x + text_width + 10, det.y),
                    color,
                    -1  # Relleno
                )
                
                # Texto
                cv2.putText(
                    annotated_frame,
                    label,
                    (det.x + 5, det.y - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 0),  # Negro para contraste
                    1,
                    cv2.LINE_AA
                )
        
        return annotated_frame, detections
    
    def get_model_info(self) -> dict:
        """Retorna información del modelo."""
        if self.model is None:
            return {"loaded": False}
        
        return {
            "loaded": True,
            "name": self.model_name,
            "device": self.device,
            "confidence_threshold": self.confidence,
            "classes": list(self.model.names.values())
        }


# Instancia global del detector
yolo_detector = YOLODetector()
