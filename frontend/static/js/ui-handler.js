/**
 * UI Handler - Maneja la interfaz de usuario
 */

document.addEventListener('DOMContentLoaded', () => {
    initializeUI();
    setupEventListeners();
});

/**
 * Inicializa la UI
 */
function initializeUI() {
    // Verificar que el video se está cargando
    const videoFeed = document.getElementById('videoFeed');
    const videoOverlay = document.getElementById('videoOverlay');

    videoFeed.addEventListener('load', () => {
        videoOverlay.classList.remove('visible');
        document.getElementById('btnStartCamera').disabled = true;
        document.getElementById('btnStopCamera').disabled = false;
    });

    videoFeed.addEventListener('error', () => {
        videoOverlay.classList.add('visible');
        videoOverlay.querySelector('.loading-text').textContent = 'Error cargando video';
    });

    // Actualizar FPS periódicamente
    setInterval(updateFPS, 1000);
}

/**
 * Configura los event listeners
 */
function setupEventListeners() {
    // Botones de control de cámara
    document.getElementById('btnStartCamera').addEventListener('click', startCamera);
    document.getElementById('btnStopCamera').addEventListener('click', stopCamera);

    // Botones de acción para detecciones (panel lateral)
    document.getElementById('btnAllow').addEventListener('click', () => {
        window.socketHandler.allowAccess();
        showToast('Acceso permitido', 'success');
    });

    document.getElementById('btnDeny').addEventListener('click', () => {
        window.socketHandler.denyAccess();
        showToast('Acceso denegado', 'danger');
    });

    // Modal buttons
    document.getElementById('modalBtnAllow').addEventListener('click', handleModalAllow);
    document.getElementById('modalBtnDeny').addEventListener('click', handleModalDeny);
    document.getElementById('modalBtnClose').addEventListener('click', hideAlertModal);

    // Checkbox para guardar persona
    document.getElementById('modalSaveToDb').addEventListener('change', (e) => {
        document.getElementById('modalPersonName').style.display =
            e.target.checked ? 'block' : 'none';
    });

    // Atajos de teclado
    document.addEventListener('keydown', handleKeyboard);
}

/**
 * Muestra el modal de alerta
 */
function showAlertModal(data) {
    const modal = document.getElementById('alertModal');

    // Actualizar contenido
    document.getElementById('modalFaceImage').src = data.face_image || '';
    document.getElementById('modalStatus').textContent = data.is_known ? data.person_name : 'DESCONOCIDO';
    document.getElementById('modalStatus').className = 'alert-status' + (data.is_known ? ' known' : '');
    document.getElementById('modalTime').textContent = new Date().toLocaleTimeString();
    document.getElementById('modalConfidence').textContent = ((data.confidence || 0) * 100).toFixed(1) + '%';

    // Mostrar/ocultar sección de guardar según si es conocido
    document.getElementById('savePersonSection').style.display = data.is_known ? 'none' : 'block';
    document.getElementById('modalPersonName').value = '';

    // Mostrar modal
    modal.style.display = 'flex';

    // Sonido de alerta (opcional)
    try {
        const alertSound = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEARK8AABCxAgACABAAZGF0YQoGAACBhYaChYaGhIWGhIWGhIWG');
        alertSound.volume = 0.3;
        alertSound.play().catch(() => { });
    } catch (e) { }
}

/**
 * Oculta el modal de alerta
 */
function hideAlertModal() {
    document.getElementById('alertModal').style.display = 'none';
}

/**
 * Maneja clic en PERMITIR del modal
 */
function handleModalAllow() {
    const saveToDb = document.getElementById('modalSaveToDb').checked;
    const personName = document.getElementById('modalPersonName').value.trim() || 'Visitante';

    window.socketHandler.socket.emit('user_response', {
        action: 'allow',
        save_to_db: saveToDb,
        person_name: personName
    });

    hideAlertModal();
    showToast('Acceso permitido' + (saveToDb ? ` - ${personName} guardado` : ''), 'success');

    window.socketHandler.appState.stats.allowed++;
    window.socketHandler.appState.pendingDetection = null;
    updateStatsFromHandler();
}

/**
 * Maneja clic en DENEGAR del modal
 */
function handleModalDeny() {
    window.socketHandler.socket.emit('user_response', {
        action: 'deny'
    });

    hideAlertModal();
    showToast('Acceso denegado', 'danger');

    window.socketHandler.appState.stats.denied++;
    window.socketHandler.appState.pendingDetection = null;
    updateStatsFromHandler();
}

/**
 * Actualiza stats desde el handler
 */
function updateStatsFromHandler() {
    document.getElementById('totalDetections').textContent = window.socketHandler.appState.stats.totalDetections;
    document.getElementById('allowedCount').textContent = window.socketHandler.appState.stats.allowed;
    document.getElementById('deniedCount').textContent = window.socketHandler.appState.stats.denied;
}

/**
 * Inicia la cámara
 */
async function startCamera() {
    try {
        const response = await fetch('/api/camera/start', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            const videoFeed = document.getElementById('videoFeed');
            videoFeed.src = '/video_feed?' + new Date().getTime();

            document.getElementById('btnStartCamera').disabled = true;
            document.getElementById('btnStopCamera').disabled = false;
            document.getElementById('videoOverlay').classList.remove('visible');

            showToast('Cámara iniciada', 'success');
        } else {
            showToast('Error iniciando cámara', 'danger');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error de conexión', 'danger');
    }
}

/**
 * Detiene la cámara
 */
async function stopCamera() {
    try {
        const response = await fetch('/api/camera/stop', { method: 'POST' });
        const data = await response.json();

        if (data.success) {
            document.getElementById('btnStartCamera').disabled = false;
            document.getElementById('btnStopCamera').disabled = true;
            document.getElementById('videoOverlay').classList.add('visible');
            document.getElementById('videoOverlay').querySelector('.loading-text').textContent = 'Cámara detenida';

            showToast('Cámara detenida', 'warning');
        }
    } catch (error) {
        console.error('Error:', error);
        showToast('Error de conexión', 'danger');
    }
}

/**
 * Maneja atajos de teclado
 */
function handleKeyboard(event) {
    const modal = document.getElementById('alertModal');
    const isModalVisible = modal.style.display === 'flex';

    if (isModalVisible) {
        switch (event.key.toLowerCase()) {
            case 'a':
            case 'enter':
                handleModalAllow();
                break;
            case 'd':
            case 'escape':
                handleModalDeny();
                break;
        }
    }
}

/**
 * Actualiza el contador de FPS
 */
let lastFrameTime = Date.now();

function updateFPS() {
    const fpsElement = document.getElementById('currentFps');
    const videoFeed = document.getElementById('videoFeed');
    if (videoFeed.complete && !document.getElementById('videoOverlay').classList.contains('visible')) {
        fpsElement.textContent = '30';
    } else {
        fpsElement.textContent = '--';
    }
    lastFrameTime = Date.now();
}

/**
 * Muestra un toast de notificación
 */
function showToast(message, type = 'info') {
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }

    const colors = {
        success: '#10b981',
        danger: '#ef4444',
        warning: '#f59e0b',
        info: '#6366f1'
    };

    const icons = {
        success: '✓',
        danger: '✗',
        warning: '⚠',
        info: 'ℹ'
    };

    const toast = document.createElement('div');
    toast.className = 'toast ' + type;
    toast.innerHTML = `<span>${icons[type] || icons.info}</span> ${message}`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Exponer showAlertModal globalmente
window.showAlertModal = showAlertModal;
window.hideAlertModal = hideAlertModal;

// Añadir animación slideOut
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

