// <--- hecho por claude code (26-oct-2026): botón "Novedades y actualización" en la cabecera (solo app .exe)
// Abre la ventana nativa del updater y refleja si hay una actualización lista.
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    var btn = document.getElementById('tc-upd-header');
    if (!btn) return;
    // Fuera de la app (navegador) no existe el puente: ocultar por seguridad.
    if (!window.tcDesktop || !window.tcDesktop.abrirNovedades) { btn.style.display = 'none'; return; }
    var label = document.getElementById('tc-upd-label');

    btn.addEventListener('click', function () { window.tcDesktop.abrirNovedades(); });

    if (window.tcDesktop.onEstado) {
      window.tcDesktop.onEstado(function (d) {
        if (!d) return;
        if (d.fase === 'listo') {
          btn.classList.add('tc-upd-ready');
          if (label) label.textContent = 'Actualización lista';
          btn.title = 'Actualización lista — reinicia para instalar';
        } else if (d.fase === 'descargando') {
          btn.classList.add('tc-upd-ready');
          if (label) label.textContent = 'Descargando…';
          btn.title = 'Descargando la actualización…';
        }
      });
    }
  });
})();
