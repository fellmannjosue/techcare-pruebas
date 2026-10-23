/* prestamos.js — <--- hecho por claude code (16-oct-2026): página Préstamos de equipo · ventana "Subir solicitud firmada".
   Se carga al final del contenido; espera a que Bootstrap exista al hacer clic. Un solo global: PRESTAMOS_MANT. */
(function () {
  'use strict';
  var modalEl = document.getElementById('modalPrestamoPdf'), form = document.getElementById('form-prest-pdf');
  if (!modalEl || !form) return;
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.btn-prest-subir');
    if (!b) return;
    form.action = b.dataset.url;
    form.reset();
    document.getElementById('prest-pdf-rid').textContent = b.dataset.rid;
    document.getElementById('prest-pdf-reemplaza').classList.toggle('d-none', !b.dataset.reemplaza);
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  });
  form.addEventListener('submit', function () { var btn = form.querySelector('[type=submit]'); if (btn) btn.disabled = true; });
  window.PRESTAMOS_MANT = { modal: modalEl };
})();
