/* firma_pdf.js — <--- hecho por claude code (21-oct-2026): subir la "ficha firmada" (PDF escaneado) en cualquier página
   de Mantenimiento. Mismo patrón que prestamos.js. Un solo global: FIRMA_PDF_MANT. */
(function () {
  'use strict';
  var modalEl = document.getElementById('modalFirmaPdf'), form = document.getElementById('form-firma-pdf');
  if (!modalEl || !form) return;
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.btn-firma-subir');
    if (!b) return;
    form.action = b.dataset.url;
    form.reset();
    document.getElementById('firma-pdf-rid').textContent = b.dataset.rid;
    document.getElementById('firma-pdf-reemplaza').classList.toggle('d-none', !b.dataset.reemplaza);
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl).show();
  });
  form.addEventListener('submit', function () { var btn = form.querySelector('[type=submit]'); if (btn) btn.disabled = true; });
  window.FIRMA_PDF_MANT = { modal: modalEl };
})();
