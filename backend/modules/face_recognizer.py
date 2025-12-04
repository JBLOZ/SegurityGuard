"""
Módulo de reconocimiento facial
Usa MediaPipe para detección de caras y genera embeddings
"""
import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import Optional
from pathlib import Path

from config import FACES_DIR


@dataclass
class Face:
    """Representa una cara detectada."""
    x: int
    y: int
    width: int
    height: int
    confidence: float
    landmarks: Optional[list] = None
    embedding: Optional[np.ndarray] = None
    image: Optional[np.ndarray] = None
    
    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """Retorna bounding box como (x, y, w, h)."""
        return (self.x, self.y, self.width, self.height)
    
    @property
    def center(self) -> tuple[int, int]:
        """Retorna el centro de la cara."""
        return (self.x + self.width // 2, self.y + self.height // 2)


class FaceRecognizer:
    """Detector y reconocedor de caras usando MediaPipe."""
    
    def __init__(self, min_detection_confidence: float = 0.5):
        """
        Inicializa el reconocedor de caras.
        
        Args:
            min_detection_confidence: Confianza mínima para detección
        """
        self.min_detection_confidence = min_detection_confidence
        
        # Inicializar MediaPipe Face Detection
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_drawing = mp.solutions.drawing_utils
        
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # 0 para corta distancia, 1 para larga distancia
            min_detection_confidence=min_detection_confidence
        )
        
        # Para embeddings usaremos una versión simplificada
        # En producción se usaría FaceNet o similar
        self._embedding_size = 128
        
        print("FaceRecognizer inicializado con MediaPipe")
    
    def detect_faces(
        self,
        frame: np.ndarray,
        extract_images: bool = True
    ) -> list[Face]:
        """
        Detecta caras en un frame.
        
        Args:
            frame: Frame BGR de OpenCV
            extract_images: Si extrae las imágenes de las caras
            
        Returns:
            Lista de caras detectadas
        """
        # Convertir a RGB para MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        height, width = frame.shape[:2]
        
        # Detectar caras
        results = self.face_detection.process(rgb_frame)
        
        faces = []
        
        if results.detections:
            for detection in results.detections:
                # Obtener bounding box
                bbox = detection.location_data.relative_bounding_box
                
                # Convertir coordenadas relativas a absolutas
                x = int(bbox.xmin * width)
                y = int(bbox.ymin * height)
                w = int(bbox.width * width)
                h = int(bbox.height * height)
                
                # Asegurar que está dentro del frame
                x = max(0, x)
                y = max(0, y)
                w = min(w, width - x)
                h = min(h, height - y)
                
                # Obtener landmarks
                landmarks = []
                for keypoint in detection.location_data.relative_keypoints:
                    landmarks.append((
                        int(keypoint.x * width),
                        int(keypoint.y * height)
                    ))
                
                face = Face(
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=detection.score[0],
                    landmarks=landmarks
                )
                
                # Extraer imagen de la cara
                if extract_images and w > 0 and h > 0:
                    face.image = frame[y:y+h, x:x+w].copy()
                    # Generar embedding
                    face.embedding = self._generate_embedding(face.image)
                
                faces.append(face)
        
        return faces
    
    def _generate_embedding(self, face_image: np.ndarray) -> np.ndarray:
        """
        Genera un embedding para una imagen de cara.
        
        Nota: Esta es una implementación simplificada.
        En producción se usaría FaceNet, ArcFace o similar.
        
        Args:
            face_image: Imagen de la cara (BGR)
            
        Returns:
            Vector de embedding normalizado
        """
        # Redimensionar a tamaño estándar
        target_size = (160, 160)
        resized = cv2.resize(face_image, target_size)
        
        # Convertir a escala de grises y normalizar
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        normalized = gray.astype(np.float32) / 255.0
        
        # Generar embedding usando características básicas
        # En producción, aquí iría FaceNet o similar
        
        # Usar histograma como embedding simplificado
        hist = cv2.calcHist([gray], [0], None, [self._embedding_size], [0, 256])
        embedding = hist.flatten()
        
        # Añadir características de textura (LBP simplificado)
        # Dividir en regiones y calcular estadísticas
        regions = 4
        region_h = target_size[0] // regions
        region_w = target_size[1] // regions
        
        texture_features = []
        for i in range(regions):
            for j in range(regions):
                region = normalized[i*region_h:(i+1)*region_h, 
                                   j*region_w:(j+1)*region_w]
                texture_features.extend([
                    np.mean(region),
                    np.std(region)
                ])
        
        # Combinar histograma con características de textura
        full_embedding = np.concatenate([
            embedding[:self._embedding_size - len(texture_features)],
            np.array(texture_features)
        ])
        
        # Normalizar el vector
        norm = np.linalg.norm(full_embedding)
        if norm > 0:
            full_embedding = full_embedding / norm
        
        return full_embedding
    
    def draw_faces(
        self,
        frame: np.ndarray,
        faces: list[Face],
        color: tuple[int, int, int] = (0, 255, 255),
        thickness: int = 2,
        show_landmarks: bool = True
    ) -> np.ndarray:
        """
        Dibuja las caras detectadas en el frame.
        
        Args:
            frame: Frame BGR de OpenCV
            faces: Lista de caras a dibujar
            color: Color del rectángulo (BGR)
            thickness: Grosor de la línea
            show_landmarks: Si muestra los puntos faciales
            
        Returns:
            Frame con las caras dibujadas
        """
        annotated = frame.copy()
        
        for face in faces:
            # Dibujar rectángulo
            cv2.rectangle(
                annotated,
                (face.x, face.y),
                (face.x + face.width, face.y + face.height),
                color,
                thickness
            )
            
            # Etiqueta
            label = f"Face: {face.confidence:.2f}"
            cv2.putText(
                annotated,
                label,
                (face.x, face.y - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
                cv2.LINE_AA
            )
            
            # Dibujar landmarks
            if show_landmarks and face.landmarks:
                for lm in face.landmarks:
                    cv2.circle(annotated, lm, 3, (255, 0, 255), -1)
        
        return annotated
    
    def save_face(
        self,
        face: Face,
        person_name: str,
        face_id: Optional[str] = None
    ) -> Optional[Path]:
        """
        Guarda la imagen de una cara en disco.
        
        Args:
            face: Objeto Face con la imagen
            person_name: Nombre de la persona
            face_id: ID único (opcional, se genera si no se proporciona)
            
        Returns:
            Ruta al archivo guardado o None si falla
        """
        if face.image is None:
            return None
        
        # Crear directorio para la persona
        person_dir = FACES_DIR / person_name.lower().replace(" ", "_")
        person_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre de archivo
        if face_id is None:
            import time
            face_id = str(int(time.time() * 1000))
        
        file_path = person_dir / f"{face_id}.jpg"
        
        # Guardar imagen
        cv2.imwrite(str(file_path), face.image)
        
        return file_path
    
    def close(self):
        """Libera recursos."""
        self.face_detection.close()


# Instancia global
face_recognizer = FaceRecognizer()
