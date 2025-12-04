# Sistema de Seguridad del Hogar con IA Multimodal

Sistema de asistente de seguridad inteligente que graba video continuamente, reconoce personas en tiempo real, y permite control remoto desde una aplicación web.

## 🚀 Inicio Rápido

### Requisitos
- Python 3.10+
- pip
- Webcam USB o cámara IP con RTSP
- (Opcional) GPU NVIDIA para aceleración

### Instalación

```bash
# Clonar repositorio
cd SegurityGuard

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r backend/requirements.txt

# Inicializar base de datos
sqlite3 database/security.db < database/init.sql
```

### Ejecución

```bash
# Iniciar servidor
cd backend
python app.py
```

Abre tu navegador en: **http://localhost:5000**

## 📁 Estructura del Proyecto

```
SegurityGuard/
├── backend/
│   ├── app.py              # Servidor Flask principal
│   ├── config.py           # Configuración
│   ├── requirements.txt    # Dependencias Python
│   └── modules/
│       ├── video_capture.py   # Captura de video
│       └── yolo_detector.py   # Detección YOLO
├── frontend/
│   ├── templates/
│   │   └── index.html      # Dashboard principal
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── socket-handler.js
│           └── ui-handler.js
├── database/
│   └── init.sql            # Esquema de BD
└── docs/
    └── plan.md             # Plan del proyecto
```

## ⚙️ Configuración

Edita `backend/config.py` o usa variables de entorno:

| Variable | Descripción | Default |
|----------|-------------|---------|
| `CAMERA_SOURCE` | Índice cámara o URL RTSP | `0` |
| `YOLO_DEVICE` | Dispositivo (`cpu` / `cuda`) | `cpu` |
| `FLASK_PORT` | Puerto del servidor | `5000` |

## 🛠️ Funcionalidades

### Sprint 1 (MVP) ✅
- [x] Captura de video con OpenCV
- [x] Detección de personas con YOLOv8
- [x] Interface web básica
- [x] Bounding boxes en tiempo real

### Sprint 2 (En progreso)
- [ ] Reconocimiento facial con FaceNet
- [ ] Base de datos de personas conocidas
- [ ] Matching con cosine similarity

### Sprint 3 (Pendiente)
- [ ] Alertas TTS con gTTS
- [ ] WebSockets para tiempo real
- [ ] Dashboard interactivo

### Sprint 4 (Pendiente)
- [ ] Docker deployment
- [ ] Control GPIO
- [ ] Alertas por email

## 📝 Licencia

MIT License
