/* settings_offline.js — <--- hecho por claude code (13-nov-2026): Configuración → Modo sin conexión (beta).
   Pide al service worker la lista de páginas guardadas en ESTE navegador; permite quitar una o todas. Global: TC_SETTINGS_OFFLINE. */
(function () {
  'use strict';
  var tbody = document.getElementById('of-lista'), nEl = document.getElementById('of-n'), buscar = document.getElementById('of-buscar');
  var datos = [];
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function vacio(msg) { tbody.innerHTML = '<tr><td colspan="5" class="text-muted text-center py-4">' + msg + '</td></tr>'; }
  function sw(tipo, extra) {
    if (!('serviceWorker' in navigator)) return Promise.resolve(null);
    return navigator.serviceWorker.getRegistration('/').then(function (reg) {
      var w = reg && (reg.active || reg.waiting || reg.installing);
      if (!w) return null;
      return new Promise(function (ok) {
        var ch = new MessageChannel(), m = { tipo: tipo };
        for (var k in (extra || {})) m[k] = extra[k];
        ch.port1.onmessage = function (ev) { ok(ev.data); };
        w.postMessage(m, [ch.port2]);
        setTimeout(function () { ok(null); }, 8000);
      });
    });
  }
  function fecha(h) {
    if (!h) return '—';
    var d = new Date(h); if (isNaN(d)) return esc(h);
    return d.toLocaleDateString('es-HN') + ' ' + d.toLocaleTimeString('es-HN', { hour: '2-digit', minute: '2-digit' });
  }
  function pintar() {
    var q = (buscar.value || '').toLowerCase();
    var filas = datos.filter(function (p) { return !q || (p.titulo + ' ' + p.url).toLowerCase().indexOf(q) >= 0; });
    nEl.textContent = datos.length;
    if (!datos.length) { vacio('No hay páginas guardadas en este navegador.'); return; }
    if (!filas.length) { vacio('Ninguna coincide con la búsqueda.'); return; }
    tbody.innerHTML = filas.map(function (p) {
      var u = new URL(p.url), ruta = u.pathname + u.search;
      return '<tr><td class="fw-medium">' + esc(p.titulo || '(sin título)') + '</td>' +
        '<td><a href="' + esc(ruta) + '" class="text-reset small text-break">' + esc(ruta) + '</a></td>' +
        '<td class="text-nowrap small text-muted">' + fecha(p.fecha) + '</td>' +
        '<td class="text-end small text-muted text-nowrap">' + (p.kb || 0) + ' KB</td>' +
        '<td><button type="button" class="btn btn-sm btn-ghost-danger btn-icon of-quitar" data-url="' + esc(p.url) + '" title="Quitar esta página"><i class="ti ti-x"></i></button></td></tr>';
    }).join('');
  }
  function cargar() {
    vacio('Cargando…');
    sw('tc-beta-lista').then(function (d) {
      if (!d) { nEl.textContent = '0'; vacio('El modo sin conexión no está activo en este navegador todavía (recarga con Ctrl+F5 y abre algunas páginas).'); return; }
      datos = (d.paginas || []).sort(function (a, b) { return (Date.parse(b.fecha) || 0) - (Date.parse(a.fecha) || 0); });
      pintar();
    });
  }
  buscar.addEventListener('input', pintar);
  document.getElementById('of-recargar').addEventListener('click', cargar);
  tbody.addEventListener('click', function (e) {
    var b = e.target.closest('.of-quitar'); if (!b) return;
    sw('tc-beta-quitar', { url: b.dataset.url }).then(cargar);
  });
  document.getElementById('of-borrar').addEventListener('click', function () {
    var go = function () { sw('tc-beta-borrar').then(cargar); };
    if (window.Swal) Swal.fire({ title: 'Borrar todas las copias', text: 'Se borran las páginas guardadas en este navegador.', icon: 'warning',
      showCancelButton: true, confirmButtonText: 'Sí, borrar', cancelButtonText: 'Cancelar', confirmButtonColor: '#d63939' })
      .then(function (r) { if (r.isConfirmed) go(); });
    else if (confirm('¿Borrar todas las páginas guardadas en este navegador?')) go();
  });
  cargar();
  window.TC_SETTINGS_OFFLINE = true;
})();
