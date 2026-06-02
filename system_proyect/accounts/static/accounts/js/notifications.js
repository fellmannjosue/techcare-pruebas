// =======================================
// CONFIG
// =======================================
const URL_NOTIS = "/core/api/notificaciones/";
const URL_MARCAR = "/core/api/notificaciones/marcar/";

let notisPrevias = new Set();
let dropdownAbierto = false;
let audioDesbloqueado = false;

// =======================================
// Desbloquear audio en primer clic
// =======================================
function desbloquearAudio() {
    if (audioDesbloqueado) return;
    let audio = document.getElementById("notifSound");
    if (audio) {
        audio.volume = 0;
        audio.play().then(() => {
            audio.pause();
            audio.currentTime = 0;
            audio.volume = 0.5;
            audioDesbloqueado = true;
        }).catch(() => {});
    }
}

// =======================================
// Reproducir sonido
// =======================================
function playNotifSound() {
    let audio = document.getElementById("notifSound");
    if (audio && audioDesbloqueado) {
        audio.currentTime = 0;
        audio.volume = 0.5;
        audio.play().catch(() => {});
    }
}

// =======================================
// Actualiza el número del badge
// =======================================
function actualizarCampana(cantidad) {
    let badge = document.getElementById("badgeNotificaciones");
    if (!badge) return;

    if (cantidad > 0) {
        badge.classList.remove("d-none");
        badge.style.display = "inline-block";
        badge.innerText = cantidad;
    } else {
        badge.classList.add("d-none");
        badge.style.display = "none";
    }
}

// =======================================
// Renderiza notificaciones en el dropdown
// =======================================
function renderizarLista(notis) {
    let lista = document.getElementById("listaNotificaciones");
    if (!lista) return;

    lista.innerHTML = "";

    if (notis.length === 0) {
        lista.innerHTML = `
            <li class="p-3 text-center text-muted">
                <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24"
                     fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"
                     stroke-linejoin="round" class="mb-2 d-block mx-auto">
                  <path d="M10 5a2 2 0 1 1 4 0a7 7 0 0 1 4 6v3a4 4 0 0 0 2 3H4a4 4 0 0 0 2-3v-3a7 7 0 0 1 4-6"/>
                  <path d="M9 17v1a3 3 0 0 0 6 0v-1"/><path d="M3 3l18 18"/>
                </svg>
                Sin notificaciones
            </li>`;
        return;
    }

    notis.forEach(n => {
        let item = document.createElement("li");

        item.innerHTML = `
            <div class="p-2 border-bottom small">
                <div class="fw-bold text-primary">
                    ${n.modulo.toUpperCase()}
                </div>
                <div>${n.mensaje}</div>
                <div class="text-muted" style="font-size: 11px;">
                    ${n.fecha}
                </div>
            </div>
        `;

        lista.appendChild(item);
    });
}

// =======================================
// Toast de notificación
// =======================================
function mostrarToastNotif(n) {
    const container = document.getElementById('tc-notif-global');
    if (!container) return;

    const colorMap  = { alerta: 'danger',  info: 'primary', exito: 'success', error: 'danger' };
    const iconMap   = { alerta: 'ti-alert-triangle', info: 'ti-bell', exito: 'ti-check', error: 'ti-x' };
    const color = colorMap[n.tipo]  || 'primary';
    const icon  = iconMap[n.tipo]   || 'ti-bell';

    const el = document.createElement('div');
    el.className = 'toast show';
    el.setAttribute('role', 'alert');
    el.style.minWidth = '300px';
    el.innerHTML = `
      <div class="toast-header">
        <span class="me-2 text-${color}"><i class="ti ${icon}"></i></span>
        <strong class="me-auto">${(n.modulo || '').toUpperCase()}</strong>
        <small class="text-muted ms-2">${n.fecha}</small>
        <button type="button" class="btn-close ms-2" aria-label="Cerrar"></button>
      </div>
      <div class="toast-body small">${n.mensaje}</div>`;

    el.querySelector('.btn-close').addEventListener('click', () => el.remove());
    setTimeout(() => { if (el.parentNode) el.remove(); }, 7000);
    container.appendChild(el);
}

// =======================================
// Cargar notificaciones del backend
// =======================================
function cargarNotificaciones() {
    fetch(URL_NOTIS)
    .then(r => r.json())
    .then(data => {
        if (!data.ok) return;

        let notis = data.notificaciones || [];

        // IDs actuales
        let idsActuales = new Set(notis.map(n => n.id));

        // Detectar nuevas notificaciones
        let nuevas = [...idsActuales].filter(id => !notisPrevias.has(id));
        if (nuevas.length > 0 && notisPrevias.size > 0) {
            playNotifSound();
            nuevas.forEach(id => {
                const n = notis.find(x => x.id === id);
                if (n) mostrarToastNotif(n);
            });
        }

        // Actualizar set
        notisPrevias = idsActuales;

        // Actualizar campanita
        actualizarCampana(notis.length);

        // Si el dropdown está abierto → renderizar
        if (dropdownAbierto) {
            renderizarLista(notis);
        }
    })
    .catch(err => console.error("Error al cargar notificaciones:", err));
}

// =======================================
// Marcar notificaciones como leídas
// =======================================
function marcarNotificacionesLeidas() {
    fetch(URL_MARCAR, { method: "POST", headers: { "X-CSRFToken": getCSRFToken() }})
    .then(r => r.json())
    .then(() => {
        actualizarCampana(0);
        notisPrevias.clear();
    })
    .catch(err => console.error("Error al marcar leídas:", err));
}

// =======================================
// Detectar apertura del dropdown
// =======================================
document.addEventListener("DOMContentLoaded", () => {
    // Desbloquear audio en primera interacción del usuario
    ["click", "keydown", "touchstart"].forEach(evt =>
        document.addEventListener(evt, desbloquearAudio, { once: true })
    );

    let dropdown = document.getElementById("notifDropdownToggle");

    if (dropdown) {
        dropdown.addEventListener("click", () => {
            dropdownAbierto = true;
            fetch(URL_NOTIS)
            .then(r => r.json())
            .then(data => {
                if (data.ok) {
                    renderizarLista(data.notificaciones);
                    marcarNotificacionesLeidas();
                }
            });
        });

        document.addEventListener("click", (e) => {
            if (!dropdown.closest(".dropdown").contains(e.target)) {
                dropdownAbierto = false;
            }
        });
    }

    cargarNotificaciones();
});

// =======================================
// Ejecución cada 30 segundos
// =======================================
setInterval(cargarNotificaciones, 30000);

// =======================================
// Extra: obtener CSRF token
// =======================================
function getCSRFToken() {
    let cookieValue = null;
    const name = 'csrftoken';
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let c of cookies) {
            c = c.trim();
            if (c.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(c.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
