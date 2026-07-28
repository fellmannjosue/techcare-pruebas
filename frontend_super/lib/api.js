// <--- hecho por claude code: cliente de la API del portal (misma sesión de Django).
const BASE = '/portal/api';

function csrf() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : '';
}

async function pedir(ruta, opciones = {}) {
  const res = await fetch(`${BASE}${ruta}`, {
    credentials: 'same-origin',
    headers: {
      'Content-Type': 'application/json',
      ...(opciones.method && opciones.method !== 'GET' ? { 'X-CSRFToken': csrf() } : {}),
    },
    ...opciones,
  });
  if (res.status === 403) throw new Error('Sin permiso o sesión expirada. Vuelve a iniciar sesión.');
  if (!res.ok) {
    let detalle = '';
    try {
      const d = await res.json();
      detalle = Object.entries(d)
        .map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(' ') : v}`).join(' · ');
    } catch (e) { /* sin JSON */ }
    throw new Error(detalle || `Error ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  resumen:  ()        => pedir('/resumen/'),
  nav:      ()        => pedir('/nav/'),
  usuarios: (q = '', nivel = '') =>
    pedir(`/usuarios/${q || nivel ? `?${new URLSearchParams({ ...(q ? { q } : {}), ...(nivel ? { nivel } : {}) })}` : ''}`),
  // volver a la interfaz clásica
  usarClasica: () => pedir('/ui-preference/', {
    method: 'POST', body: JSON.stringify({ prefer_new_ui: false }),
  }),
};
