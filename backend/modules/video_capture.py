"""
Módulo de captura de video
Soporta cámaras USB y streams RTSP
"""
import cv2
import threading
import queue
from typing import Optional, Generator
import time

from config import (
    CAMERA_SOURCE,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    CAMERA_FPS
)


class VideoCapture:
    """Captura de video con buffer en cola para procesamiento asíncrono."""
    
    def __init__(
        self,
        source: Optional[int | str] = None,
        width: int = CAMERA_WIDTH,
        height: int = CAMERA_HEIGHT,
        fps: int = CAMERA_FPS,
        buffer_size: int = 10
    ):
        """
        Inicializa el capturador de video.
        
        Args:
            source: Índice de cámara (0, 1, ...) o URL RTSP
            width: Ancho del frame
            height: Alto del frame
            fps: Frames por segundo objetivo
            buffer_size: Tamaño del buffer de frames
        """
        self.source = source if source is not None else CAMERA_SOURCE
        self.width = width
        self.height = height
        self.fps = fps
        self.buffer_size = buffer_size
        
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_queue: queue.Queue = queue.Queue(maxsize=buffer_size)
        self.running = False
        self.capture_thread: Optional[threading.Thread] = None
        self.last_frame: Optional[cv2.typing.MatLike] = None
        
    def start(self) -> bool:
        """Inicia la captura de video."""
        # Convertir source a int si es string numérico
        if isinstance(self.source, str) and self.source.isdigit():
            self.source = int(self.source)
            
        self.cap = cv2.VideoCapture(self.source)
        
        if not self.cap.isOpened():
            print(f"Error: No se pudo abrir la cámara {self.source}")
            return False
        
        # Configurar resolución y FPS
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
        self.cap.set(cv2.CAP_PROP_FPS, self.fps)
        
        # Iniciar thread de captura
        self.running = True
        self.capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.capture_thread.start()
        
        print(f"Captura iniciada: {self.width}x{self.height} @ {self.fps}fps")
        return True
    
    def _capture_loop(self):
        """Loop de captura en thread separado."""
        frame_interval = 1.0 / self.fps
        
        while self.running:
            start_time = time.time()
            
            ret, frame = self.cap.read()
            
            if ret:
                self.last_frame = frame
                
                # Intentar añadir al queue, descartar si está lleno
                try:
                    self.frame_queue.put_nowait(frame)
                except queue.Full:
                    # Descartar frame más antiguo
                    try:
                        self.frame_queue.get_nowait()
                        self.frame_queue.put_nowait(frame)
                    except queue.Empty:
                        pass
            else:
                print("Warning: Frame no capturado")
                time.sleep(0.1)
            
            # Mantener FPS
            elapsed = time.time() - start_time
            if elapsed < frame_interval:
                time.sleep(frame_interval - elapsed)
    
    def read(self) -> tuple[bool, Optional[cv2.typing.MatLike]]:
        """Lee el frame más reciente (no bloquea)."""
        if self.last_frame is not None:
            return True, self.last_frame.copy()
        return False, None
    
    def read_from_queue(self, timeout: float = 1.0) -> tuple[bool, Optional[cv2.typing.MatLike]]:
        """Lee un frame de la cola (bloquea hasta timeout)."""
        try:
            frame = self.frame_queue.get(timeout=timeout)
            return True, frame
        except queue.Empty:
            return False, None
    
    def get_frames(self) -> Generator[cv2.typing.MatLike, None, None]:
        """Generador de frames para streaming."""
        while self.running:
            ret, frame = self.read()
            if ret:
                yield frame
            time.sleep(1.0 / self.fps)
    
    def stop(self):
        """Detiene la captura de video."""
        self.running = False
        
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=2.0)
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        print("Captura detenida")
    
    def is_running(self) -> bool:
        """Retorna si la captura está activa."""
        return self.running and self.cap is not None and self.cap.isOpened()
    
    def get_properties(self) -> dict:
        """Retorna propiedades de la cámara."""
        if self.cap is None:
            return {}
        
        return {
            "width": int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            "height": int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            "fps": int(self.cap.get(cv2.CAP_PROP_FPS)),
            "backend": self.cap.getBackendName()
        }
    
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


# Instancia global del capturador
video_capture = VideoCapture()


def encode_frame_jpeg(frame: cv2.typing.MatLike, quality: int = 60) -> bytes:
    """Codifica un frame a JPEG (calidad reducida para velocidad)."""
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, buffer = cv2.imencode('.jpg', frame, encode_param)
    return buffer.tobytes()


def generate_mjpeg_stream() -> Generator[bytes, None, None]:
    """Genera un stream MJPEG para el navegador."""
    for frame in video_capture.get_frames():
        jpeg = encode_frame_jpeg(frame)
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
        )
