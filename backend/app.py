"""
Aplicación Principal ULTRA-LIGERA
Optimizada para Raspberry Pi
"""
import cv2
import time
import threading
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    SECRET_KEY,
    USE_LIGHTWEIGHT_DETECTOR
)
from modules.video_capture import video_capture, encode_frame_jpeg
from modules.lightweight_detector import lightweight_detector
from modules.geometric_recognizer import geometric_recognizer

# Crear aplicación Flask
app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)
app.config['SECRET_KEY'] = SECRET_KEY

# SocketIO simple (sin eventlet para mejor compatibilidad)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Estado global con tracking inteligente
app_state = {
    "frame_count": 0,
    "current_detection": None,
    # Tracking de persona actual
    "person_in_view": False,           # ¿Hay alguien en cámara?
    "person_already_alerted": False,   # ¿Ya se alertó de esta persona?
    "frames_without_person": 0,        # Frames sin detectar nadie
    "frames_to_reset": 15              # Frames sin persona para resetear (0.5 seg a 30fps)
}


def generate_video_stream():
    """
    Genera stream de video ULTRA-LIGERO con tracking inteligente.
    Solo alerta cuando aparece una NUEVA persona.
    """
    if not video_capture.is_running():
        if not video_capture.start():
            print("ERROR: No se pudo iniciar la cámara")
            error_frame = create_error_frame()
            jpeg = encode_frame_jpeg(error_frame)
            while True:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
                time.sleep(1)
    
    print("Stream de video iniciado (modo tracking inteligente)")
    
    while True:
        ret, frame = video_capture.read()
        
        if not ret:
            time.sleep(0.01)
            continue
        
        app_state["frame_count"] += 1
        
        # Detectar caras
        annotated_frame, detections = lightweight_detector.detect_and_draw(frame)
        
        # LÓGICA DE TRACKING INTELIGENTE
        if detections:
            # Hay alguien en cámara
            app_state["frames_without_person"] = 0
            
            if not app_state["person_in_view"]:
                # NUEVA persona acaba de entrar
                app_state["person_in_view"] = True
                app_state["person_already_alerted"] = False
                print(">> Nueva persona detectada en cámara")
            
            # Solo alertar si no hemos alertado ya de esta persona
            if not app_state["person_already_alerted"]:
                process_detection(detections[0], frame)
                app_state["person_already_alerted"] = True
        else:
            # No hay nadie en cámara
            app_state["frames_without_person"] += 1
            
            # Si llevamos varios frames sin persona, resetear
            if app_state["frames_without_person"] >= app_state["frames_to_reset"]:
                if app_state["person_in_view"]:
                    print(">> Persona salió de cámara")
                    socketio.emit('person_left', {})
                
                app_state["person_in_view"] = False
                app_state["person_already_alerted"] = False
        
        # Codificar y enviar
        jpeg = encode_frame_jpeg(annotated_frame)
        
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
        )


def create_error_frame():
    """Crea un frame de error cuando no hay cámara."""
    frame = cv2.zeros((480, 640, 3), dtype="uint8")
    cv2.putText(
        frame, "Camara no disponible",
        (100, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2
    )
    return frame


def process_detection(detection, frame):
    """Procesa una detección NUEVA y envía por WebSocket."""
    landmarks = detection.landmarks
    
    # Intentar reconocimiento geométrico
    match = None
    ratios = None
    
    if landmarks:
        ratios = geometric_recognizer.extract_ratios(landmarks)
        if ratios:
            match = geometric_recognizer.find_match(ratios)
    
    # Guardar estado actual
    app_state["current_detection"] = {
        "detection": detection,
        "match": match,
        "ratios": ratios
    }
    
    # Preparar datos para WebSocket
    alert_data = {
        "person_name": match.name if match else "Desconocido",
        "confidence": 0.9 if match else 0,
        "is_known": match is not None,
        "bbox": detection.bbox,
        "has_landmarks": landmarks is not None
    }
    
    # Emitir evento
    socketio.emit('face_detected', alert_data)
    print(f"Detección: {alert_data['person_name']}")


# ==================== RUTAS ====================

@app.route('/')
def index():
    """Página principal."""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Stream de video MJPEG."""
    return Response(
        generate_video_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/status')
def get_status():
    """Estado del sistema."""
    return jsonify({
        "camera_running": video_capture.is_running(),
        "frame_count": app_state["frame_count"],
        "detector": "Haar Cascades (lightweight)",
        "recognizer": geometric_recognizer.get_stats()
    })


@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Inicia cámara."""
    success = video_capture.start()
    return jsonify({"success": success})


@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Detiene cámara."""
    video_capture.stop()
    return jsonify({"success": True})


# ==================== API DE PERSONAS ====================

@app.route('/api/persons', methods=['GET'])
def get_persons():
    """Lista perfiles geométricos."""
    profiles = [
        {"id": p.person_id, "name": p.name}
        for p in geometric_recognizer._known_profiles.values()
    ]
    return jsonify(profiles)


@app.route('/api/persons', methods=['POST'])
def register_person():
    """Registra nueva persona con la cara actual."""
    data = request.json
    name = data.get("name", "Persona")
    
    current = app_state.get("current_detection")
    if not current or not current.get("ratios"):
        return jsonify({"error": "No hay cara detectada con landmarks"}), 400
    
    # Generar ID único
    person_id = int(time.time() * 1000) % 100000
    
    # Guardar perfil geométrico
    geometric_recognizer.add_profile(
        person_id=person_id,
        name=name,
        ratios=current["ratios"]
    )
    
    return jsonify({
        "success": True,
        "person_id": person_id,
        "name": name,
        "message": f"Persona '{name}' registrada con perfil geométrico"
    })


@app.route('/api/persons/<int:person_id>', methods=['DELETE'])
def delete_person(person_id):
    """Elimina un perfil."""
    geometric_recognizer.remove_profile(person_id)
    return jsonify({"success": True})


# ==================== WEBSOCKET ====================

@socketio.on('connect')
def handle_connect():
    """Cliente conectado."""
    print('Cliente WebSocket conectado')
    emit('status', {'message': 'Conectado al servidor'})


@socketio.on('disconnect')
def handle_disconnect():
    """Cliente desconectado."""
    print('Cliente WebSocket desconectado')


@socketio.on('register_face')
def handle_register_face(data):
    """Registra la cara actual."""
    name = data.get("name", "Persona")
    
    current = app_state.get("current_detection")
    if not current or not current.get("ratios"):
        emit('error', {'message': 'No hay cara detectada'})
        return
    
    person_id = int(time.time() * 1000) % 100000
    geometric_recognizer.add_profile(person_id, name, current["ratios"])
    
    emit('person_registered', {
        'person_id': person_id,
        'name': name
    })


@socketio.on('user_response')
def handle_user_response(data):
    """Maneja respuesta del usuario (permitir/denegar)."""
    action = data.get('action')
    save_person = data.get('save_to_db', False)
    person_name = data.get('person_name', 'Visitante')
    
    if action == 'allow' and save_person:
        current = app_state.get("current_detection")
        if current and current.get("ratios"):
            person_id = int(time.time() * 1000) % 100000
            geometric_recognizer.add_profile(person_id, person_name, current["ratios"])
            emit('person_registered', {'person_id': person_id, 'name': person_name})
    
    emit('response_confirmed', {'action': action})


# ==================== MAIN ====================

if __name__ == '__main__':
    print("=" * 50)
    print("Sistema de Seguridad ULTRA-LIGERO")
    print("Optimizado para Raspberry Pi")
    print("=" * 50)
    print(f"Detector: Haar Cascades")
    print(f"Reconocimiento: Geométrico (ratios faciales)")
    print(f"Servidor: http://{FLASK_HOST}:{FLASK_PORT}")
    print()
    
    socketio.run(
        app,
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG,
        allow_unsafe_werkzeug=True
    )
