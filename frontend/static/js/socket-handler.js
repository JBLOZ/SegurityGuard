/**
 * Socket Handler - Maneja la comunicación WebSocket con el servidor
 */

// Conexión al servidor
const socket = io();

// Estado de la aplicación
const appState = {
    connected: false,
    cameraRunning: false,
    pendingDetection: null,
    stats: {
        totalDetections: 0,
        allowed: 0,
        denied: 0
    }
};

// ==================== EVENTOS DE CONEXIÓN ====================

socket.on('connect', () => {
    console.log('✅ Conectado al servidor');
    appState.connected = true;
    updateConnectionStatus('connected', 'Conectado');
});

socket.on('disconnect', () => {
    console.log('❌ Desconectado del servidor');
    appState.connected = false;
    updateConnectionStatus('disconnected', 'Desconectado');
});

socket.on('connect_error', (error) => {
    console.error('Error de conexión:', error);
    updateConnectionStatus('disconnected', 'Error de conexión');
});

// ==================== EVENTOS DEL SERVIDOR ====================

socket.on('status', (data) => {
    console.log('📢 Estado:', data.message);
});

socket.on('detections', (data) => {
    console.log('🔍 Detecciones:', data.data);
    handleDetections(data.data);
});

socket.on('face_detected', (data) => {
    console.log('👤 Cara detectada:', data);
    handleFaceDetection(data);
});

socket.on('alert', (data) => {
    console.log('🚨 Alerta:', data);
    showAlert(data);
});

socket.on('person_saved', (data) => {
    console.log('💾 Persona guardada:', data);
    showToast(`Persona "${data.name}" guardada con ID ${data.person_id}`, 'success');
});

socket.on('response_confirmed', (data) => {
    console.log('✔️ Respuesta confirmada:', data);
    hideActionButtons();
});

// ==================== FUNCIONES DE MANEJO ====================

/**
 * Actualiza el indicador de estado de conexión
 */
function updateConnectionStatus(status, text) {
    const indicator = document.getElementById('connectionStatus');
    const statusText = indicator.querySelector('.status-text');

    indicator.className = 'status-indicator ' + status;
    statusText.textContent = text;
}

/**
 * Procesa las detecciones recibidas
 */
function handleDetections(detections) {
    if (!detections || detections.length === 0) {
        return;
    }

    // Actualizar contador
    appState.stats.totalDetections++;
    updateStatsUI();

    // Mostrar la primera detección (la más relevante)
    const detection = detections[0];

    // Actualizar panel de detección
    const panel = document.getElementById('detectionPanel');
    panel.classList.add('active');

    document.getElementById('personName').textContent = detection.class_name || 'Persona';
    document.getElementById('confidence').textContent =
        (detection.confidence * 100).toFixed(1) + '%';
    document.getElementById('detectionTime').textContent =
        new Date().toLocaleTimeString();

    // Guardar detección pendiente
    appState.pendingDetection = detection;

    // Mostrar botones de acción para personas
    if (detection.class_name === 'person') {
        showActionButtons();
    }

    // Quitar efecto activo después de 3 segundos
    setTimeout(() => {
        panel.classList.remove('active');
    }, 3000);
}

/**
 * Procesa detección de cara con reconocimiento facial
 */
function handleFaceDetection(data) {
    // Actualizar contador
    appState.stats.totalDetections++;
    updateStatsUI();

    // Actualizar panel de detección
    const panel = document.getElementById('detectionPanel');
    panel.classList.add('active');

    // Mostrar nombre y confianza
    const personName = data.person_name || 'Desconocido';
    const confidence = (data.confidence * 100).toFixed(1);

    document.getElementById('personName').textContent = personName;
    document.getElementById('confidence').textContent = confidence + '%';
    document.getElementById('detectionTime').textContent = new Date().toLocaleTimeString();

    // Mostrar imagen de cara
    if (data.face_image) {
        const faceImg = document.getElementById('faceImage');
        faceImg.src = data.face_image;
        faceImg.classList.add('visible');
        faceImg.parentElement.classList.add('has-face');
    }

    // Guardar detección pendiente
    appState.pendingDetection = data;

    // Estilo según si es conocido o no
    if (data.is_known) {
        panel.style.borderColor = '#10b981'; // Verde
    } else {
        panel.style.borderColor = '#ef4444'; // Rojo

        // Mostrar modal de alerta para DESCONOCIDO
        if (window.showAlertModal) {
            window.showAlertModal(data);
        }
    }

    // Mostrar botones de acción en panel lateral también
    showActionButtons();

    // Quitar efecto después de 5 segundos
    setTimeout(() => {
        panel.classList.remove('active');
        panel.style.borderColor = '';
    }, 5000);
}

/**
 * Muestra una alerta en la UI
 */
function showAlert(data) {
    // Reproducir sonido de alerta si está disponible
    if (data.audio_url) {
        const audio = new Audio(data.audio_url);
        audio.play().catch(e => console.log('No se pudo reproducir audio:', e));
    }

    // Actualizar panel de detección
    document.getElementById('personName').textContent = data.person_name || 'Desconocido';
    document.getElementById('confidence').textContent =
        ((data.confidence || 0) * 100).toFixed(1) + '%';

    // Actualizar imagen de cara si está disponible
    if (data.face_image) {
        const faceImg = document.getElementById('faceImage');
        faceImg.src = data.face_image;
        faceImg.classList.add('visible');
        faceImg.parentElement.classList.add('has-face');
    }

    showActionButtons();
}

/**
 * Muestra los botones de acción
 */
function showActionButtons() {
    document.getElementById('actionButtons').style.display = 'grid';
    document.getElementById('saveOption').style.display = 'block';
}

/**
 * Oculta los botones de acción
 */
function hideActionButtons() {
    document.getElementById('actionButtons').style.display = 'none';
    document.getElementById('saveOption').style.display = 'none';
    appState.pendingDetection = null;
}

// ==================== ACCIONES DEL USUARIO ====================

/**
 * Permite el acceso
 */
function allowAccess() {
    if (!appState.pendingDetection) return;

    const saveToDb = document.getElementById('saveToDb').checked;

    socket.emit('user_response', {
        action: 'allow',
        detection: appState.pendingDetection,
        save_to_db: saveToDb
    });

    appState.stats.allowed++;
    updateStatsUI();
    addEventToList('Persona', 'allowed');
    hideActionButtons();

    console.log('✅ Acceso permitido');
}

/**
 * Deniega el acceso
 */
function denyAccess() {
    if (!appState.pendingDetection) return;

    socket.emit('user_response', {
        action: 'deny',
        detection: appState.pendingDetection
    });

    appState.stats.denied++;
    updateStatsUI();
    addEventToList('Persona', 'denied');
    hideActionButtons();

    console.log('❌ Acceso denegado');
}

/**
 * Actualiza la UI de estadísticas
 */
function updateStatsUI() {
    document.getElementById('totalDetections').textContent = appState.stats.totalDetections;
    document.getElementById('allowedCount').textContent = appState.stats.allowed;
    document.getElementById('deniedCount').textContent = appState.stats.denied;
}

/**
 * Añade un evento a la lista
 */
function addEventToList(name, status) {
    const list = document.getElementById('eventsList');
    const placeholder = list.querySelector('.event-placeholder');

    if (placeholder) {
        placeholder.remove();
    }

    const eventItem = document.createElement('div');
    eventItem.className = 'event-item';
    eventItem.innerHTML = `
        <div class="event-avatar">👤</div>
        <div class="event-details">
            <div class="event-name">${name}</div>
            <div class="event-time">${new Date().toLocaleTimeString()}</div>
        </div>
        <span class="event-status ${status}">
            ${status === 'allowed' ? 'Permitido' : status === 'denied' ? 'Denegado' : 'Pendiente'}
        </span>
    `;

    // Insertar al principio
    list.insertBefore(eventItem, list.firstChild);

    // Limitar a 10 eventos
    while (list.children.length > 10) {
        list.removeChild(list.lastChild);
    }
}

// Exportar funciones para uso en otros scripts
window.socketHandler = {
    allowAccess,
    denyAccess,
    socket,
    appState
};
