-- Esquema inicial de base de datos para Sistema de Seguridad del Hogar
-- Compatible con SQLite y PostgreSQL

-- ==================== TABLA DE PERSONAS ====================
CREATE TABLE IF NOT EXISTS persons (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    embedding TEXT,  -- Vector JSON de 512-2048 dimensiones
    photo_path VARCHAR(255),
    category VARCHAR(20) DEFAULT 'unknown' CHECK (category IN ('known', 'delivery', 'unknown')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== TABLA DE EVENTOS DE DETECCIÓN ====================
CREATE TABLE IF NOT EXISTS detection_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id INTEGER REFERENCES persons(id) ON DELETE SET NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    video_frame_path VARCHAR(255),
    face_crop_path VARCHAR(255),
    confidence REAL CHECK (confidence >= 0 AND confidence <= 1),
    allowed BOOLEAN,
    saved_to_db BOOLEAN DEFAULT FALSE,
    action_taken VARCHAR(20) DEFAULT 'pending' CHECK (action_taken IN ('allowed', 'denied', 'pending', 'timeout')),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== TABLA DE CONFIGURACIÓN DEL SISTEMA ====================
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key VARCHAR(50) UNIQUE NOT NULL,
    value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== DATOS INICIALES ====================

-- Configuración por defecto
INSERT OR IGNORE INTO system_config (key, value, description) VALUES
    ('camera_source', '0', 'Fuente de cámara (0=USB, URL para RTSP)'),
    ('confidence_threshold', '0.5', 'Umbral mínimo de confianza para detección'),
    ('recognition_threshold', '0.6', 'Umbral para identificar persona conocida'),
    ('alert_enabled', 'true', 'Activar alertas de audio'),
    ('recording_enabled', 'true', 'Activar grabación de eventos'),
    ('tts_language', 'es', 'Idioma para síntesis de voz');

-- ==================== ÍNDICES ====================

CREATE INDEX IF NOT EXISTS idx_persons_category ON persons(category);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON detection_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_person ON detection_events(person_id);
CREATE INDEX IF NOT EXISTS idx_events_action ON detection_events(action_taken);

-- ==================== VISTAS ====================

-- Vista de eventos recientes con información de persona
CREATE VIEW IF NOT EXISTS v_recent_events AS
SELECT 
    e.id,
    e.timestamp,
    p.name as person_name,
    p.category as person_category,
    e.confidence,
    e.action_taken,
    e.face_crop_path
FROM detection_events e
LEFT JOIN persons p ON e.person_id = p.id
ORDER BY e.timestamp DESC
LIMIT 100;

-- Vista de estadísticas diarias
CREATE VIEW IF NOT EXISTS v_daily_stats AS
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as total_detections,
    SUM(CASE WHEN action_taken = 'allowed' THEN 1 ELSE 0 END) as allowed_count,
    SUM(CASE WHEN action_taken = 'denied' THEN 1 ELSE 0 END) as denied_count,
    AVG(confidence) as avg_confidence
FROM detection_events
GROUP BY DATE(timestamp)
ORDER BY date DESC;
