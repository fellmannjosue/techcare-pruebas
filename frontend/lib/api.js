// <--- hecho por claude code: cliente de la API de Django.
// Misma sesión (mismo dominio) => solo hay que mandar el CSRF en escrituras.
const BASE = '/inventario-camaras/api';

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
    // <--- hecho por claude code: mostrar el detalle real de Django, no un "Error 400" seco.
    let detalle = '';
    try {
      const d = await res.json();
      detalle = Object.entries(d)
        .map(([campo, msgs]) => `${campo}: ${Array.isArray(msgs) ? msgs.join(' ') : msgs}`)
        .join(' · ');
    } catch (e) { /* respuesta sin JSON */ }
    throw new Error(detalle || `Error ${res.status}`);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  resumen:   ()            => pedir('/resumen/'),
  listar:    (rec, q = '') => pedir(`/${rec}/${q ? `?${q}` : ''}`),
  crear:     (rec, datos)  => pedir(`/${rec}/`, { method: 'POST', body: JSON.stringify(datos) }),
  actualizar:(rec, id, d)  => pedir(`/${rec}/${id}/`, { method: 'PATCH', body: JSON.stringify(d) }),
  eliminar:  (rec, id)     => pedir(`/${rec}/${id}/`, { method: 'DELETE' }),
};
