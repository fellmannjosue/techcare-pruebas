/* reparaciones.js — <--- hecho por claude code (21-oct-2026): página Reparaciones · ventana "Subir ficha firmada".
   Se carga al final del contenido; espera a que Bootstrap exista al hacer clic. Un solo global: REPARACIONES_MANT. */
(function () {
  'use strict';
  var modalEl = document.getElementById('modalReparacionPdf'), form = document.getElementById('form-rep-pdf');
  if (!modalEl || !form) return;
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.btn-rep-subir');
    if (!b) return;
    form.action = b.dataset.url;
    form.reset();
    document.getElementById('rep-pdf-rid').textContent = b.dataset.rid;
    document.getElementById('rep-pdf-reemplaza').classList.toggle('d-none', !b.dataset.reemplaza);
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  });
  form.addEventListener('submit', function () { var btn = form.querySelector('[type=submit]'); if (btn) btn.disabled = true; });
  window.REPARACIONES_MANT = { modal: modalEl };
})();
