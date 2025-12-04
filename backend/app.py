"""
Aplicación principal Flask para el Sistema de Seguridad del Hogar
Sprint 2: Integración de reconocimiento facial
"""
# IMPORTANTE: Monkey patch de eventlet debe ir primero
import eventlet
eventlet.monkey_patch()

import cv2
import base64
from flask import Flask, render_template, Response, jsonify, request
from flask_socketio import SocketIO, emit

from config import (
    FLASK_HOST,
    FLASK_PORT,
    FLASK_DEBUG,
    SECRET_KEY
)
from modules.video_capture import video_capture, encode_frame_jpeg
from modules.yolo_detector import yolo_detector
from modules.face_recognizer import face_recognizer
from modules.face_matcher import face_matcher
from modules.db_handler import db_handler, initialize_database

# Crear aplicación Flask
app = Flask(
    __name__,
    template_folder='../frontend/templates',
    static_folder='../frontend/static'
)
app.config['SECRET_KEY'] = SECRET_KEY

# Inicializar SocketIO con async_mode correcto
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Estado actual de detección
current_detection = {
    "face": None,
    "match": None,
    "event_id": None
}


def load_known_faces():
    """Carga todas las caras conocidas en el matcher."""
    embeddings = db_handler.get_all_embeddings()
    for person_id, data in embeddings.items():
        face_matcher.add_known_face(
            person_id=person_id,
            name=data["name"],
            embedding=data["embedding"],
            category=data["category"]
        )
    print(f"Cargadas {len(embeddings)} caras conocidas")


def generate_video_stream():
    """Genera stream de video con detecciones de personas y caras."""
    if not video_capture.is_running():
        video_capture.start()
    
    # Pre-cargar modelo YOLO
    yolo_detector.load_model()
    
    while True:
        ret, frame = video_capture.read()
        
        if not ret:
            continue
        
        # Detectar personas con YOLO
        annotated_frame, person_detections = yolo_detector.detect_and_draw(frame)
        
        # Si hay personas, detectar caras
        if person_detections:
            faces = face_recognizer.detect_faces(frame)
            
            # Dibujar caras detectadas
            annotated_frame = face_recognizer.draw_faces(annotated_frame, faces)
            
            # Intentar reconocer cada cara
            for face in faces:
                if face.embedding is not None:
                    match = face_matcher.find_match(face.embedding)
                    
                    if match:
                        # Persona conocida
                        label = f"{match.person_name}: {match.confidence_percent:.0f}%"
                        color = (0, 255, 0)  # Verde
                    else:
                        # Persona desconocida
                        label = "Desconocido"
                        color = (0, 0, 255)  # Rojo
                    
                    # Dibujar etiqueta
                    cv2.putText(
                        annotated_frame,
                        label,
                        (face.x, face.y + face.height + 20),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2,
                        cv2.LINE_AA
                    )
                    
                    # Enviar alerta por WebSocket
                    face_b64 = None
                    if face.image is not None:
                        _, buffer = cv2.imencode('.jpg', face.image)
                        face_b64 = base64.b64encode(buffer).decode('utf-8')
                    
                    alert_data = {
                        "person_name": match.person_name if match else "Desconocido",
                        "confidence": match.similarity if match else 0,
                        "category": match.category if match else "unknown",
                        "is_known": match is not None,
                        "face_image": f"data:image/jpeg;base64,{face_b64}" if face_b64 else None,
                        "bbox": face.bbox
                    }
                    
                    # Guardar detección actual
                    current_detection["face"] = face
                    current_detection["match"] = match
                    
                    socketio.emit('face_detected', alert_data)
        
        # Codificar frame a JPEG
        jpeg = encode_frame_jpeg(annotated_frame)
        
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n'
        )


# ==================== RUTAS ====================

@app.route('/')
def index():
    """Página principal - Dashboard."""
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    """Endpoint de streaming de video."""
    return Response(
        generate_video_stream(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )


@app.route('/api/status')
def get_status():
    """Retorna el estado del sistema."""
    return jsonify({
        "camera": {
            "running": video_capture.is_running(),
            "properties": video_capture.get_properties() if video_capture.is_running() else {}
        },
        "detector": yolo_detector.get_model_info(),
        "face_matcher": face_matcher.get_stats(),
        "daily_stats": db_handler.get_daily_stats()
    })


@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Inicia la captura de cámara."""
    success = video_capture.start()
    return jsonify({"success": success})


@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Detiene la captura de cámara."""
    video_capture.stop()
    return jsonify({"success": True})


# ==================== API DE PERSONAS ====================

@app.route('/api/persons', methods=['GET'])
def get_persons():
    """Obtiene lista de todas las personas."""
    category = request.args.get('category')
    persons = db_handler.get_all_persons(category)
    return jsonify([p.to_dict() for p in persons])


@app.route('/api/persons', methods=['POST'])
def create_person():
    """Crea una nueva persona."""
    data = request.json
    
    person = db_handler.create_person(
        name=data.get('name'),
        category=data.get('category', 'known'),
        notes=data.get('notes')
    )
    
    return jsonify(person.to_dict()), 201


@app.route('/api/persons/<int:person_id>', methods=['GET'])
def get_person(person_id):
    """Obtiene una persona por ID."""
    person = db_handler.get_person(person_id)
    if not person:
        return jsonify({"error": "Persona no encontrada"}), 404
    return jsonify(person.to_dict())


@app.route('/api/persons/<int:person_id>', methods=['PUT'])
def update_person(person_id):
    """Actualiza una persona."""
    data = request.json
    person = db_handler.update_person(
        person_id,
        name=data.get('name'),
        category=data.get('category'),
        notes=data.get('notes')
    )
    if not person:
        return jsonify({"error": "Persona no encontrada"}), 404
    return jsonify(person.to_dict())


@app.route('/api/persons/<int:person_id>', methods=['DELETE'])
def delete_person(person_id):
    """Elimina una persona."""
    success = db_handler.delete_person(person_id)
    if not success:
        return jsonify({"error": "Persona no encontrada"}), 404
    
    # Eliminar del matcher
    face_matcher.remove_known_face(person_id)
    
    return jsonify({"success": True})


@app.route('/api/persons/<int:person_id>/register-face', methods=['POST'])
def register_face(person_id):
    """Registra la cara actual para una persona."""
    person = db_handler.get_person(person_id)
    if not person:
        return jsonify({"error": "Persona no encontrada"}), 404
    
    face = current_detection.get("face")
    if face is None or face.embedding is None:
        return jsonify({"error": "No hay cara detectada actualmente"}), 400
    
    # Guardar imagen de la cara
    photo_path = face_recognizer.save_face(face, person.name)
    
    # Actualizar persona con embedding
    db_handler.update_person(
        person_id,
        embedding=face.embedding,
        photo_path=str(photo_path) if photo_path else None
    )
    
    # Añadir al matcher
    face_matcher.add_known_face(
        person_id=person_id,
        name=person.name,
        embedding=face.embedding,
        category=person.category
    )
    
    return jsonify({
        "success": True,
        "message": f"Cara registrada para {person.name}",
        "photo_path": str(photo_path) if photo_path else None
    })


# ==================== API DE EVENTOS ====================

@app.route('/api/events', methods=['GET'])
def get_events():
    """Obtiene eventos recientes."""
    limit = request.args.get('limit', 50, type=int)
    events = db_handler.get_recent_events(limit)
    return jsonify([e.to_dict() for e in events])


# ==================== WEBSOCKET EVENTS ====================

@socketio.on('connect')
def handle_connect():
    """Cliente conectado."""
    print('Cliente conectado')
    emit('status', {'message': 'Conectado al servidor de seguridad'})


@socketio.on('disconnect')
def handle_disconnect():
    """Cliente desconectado."""
    print('Cliente desconectado')


@socketio.on('user_response')
def handle_user_response(data):
    """Maneja la respuesta del usuario (permitir/denegar)."""
    action = data.get('action')
    save_to_db = data.get('save_to_db', False)
    
    face = current_detection.get("face")
    match = current_detection.get("match")
    
    # Crear evento de detección
    event = db_handler.create_detection_event(
        person_id=match.person_id if match else None,
        confidence=match.similarity if match else None,
        action_taken=action
    )
    
    # Si es permitir y quiere guardar nueva persona
    if action == 'allow' and save_to_db and not match and face:
        # Crear nueva persona
        new_person = db_handler.create_person(
            name=data.get('person_name', 'Nuevo Visitante'),
            embedding=face.embedding,
            category='known'
        )
        
        # Añadir al matcher
        face_matcher.add_known_face(
            person_id=new_person.id,
            name=new_person.name,
            embedding=face.embedding,
            category='known'
        )
        
        emit('person_saved', {
            'person_id': new_person.id,
            'name': new_person.name
        })
    
    emit('response_confirmed', {
        'action': action,
        'event_id': event.id
    })


@socketio.on('request_frame')
def handle_request_frame():
    """Solicitud de frame individual."""
    ret, frame = video_capture.read()
    if ret:
        annotated_frame, detections = yolo_detector.detect_and_draw(frame)
        jpeg = encode_frame_jpeg(annotated_frame)
        emit('frame', {'data': jpeg})


# ==================== MAIN ====================

if __name__ == '__main__':
    print("=" * 50)
    print("Sistema de Seguridad del Hogar con IA Multimodal")
    print("=" * 50)
    
    # Inicializar base de datos
    try:
        initialize_database()
        load_known_faces()
    except Exception as e:
        print(f"Error inicializando BD: {e}")
    
    print(f"Servidor: http://{FLASK_HOST}:{FLASK_PORT}")
    print()
    
    # Iniciar servidor
    socketio.run(
        app,
        host=FLASK_HOST,
        port=FLASK_PORT,
        debug=FLASK_DEBUG
    )

