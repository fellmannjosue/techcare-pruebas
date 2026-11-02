// datashow/js/datashow.js
// <--- hecho por claude code (02-nov-2026): calendario de reservas de DataShow.
// Un solo identificador global (los .js comparten ámbito).
(function () {
  'use strict';

  function $(sel, ctx) { return (ctx || document).querySelector(sel); }
  function modal(el) {
    if (!el || !window.bootstrap || !bootstrap.Modal) return null;
    return bootstrap.Modal.getOrCreateInstance(el);
  }

  document.addEventListener('DOMContentLoaded', function () {
    var modalNueva = $('#modalNuevaReserva');
    var inputFecha = modalNueva ? modalNueva.querySelector('input[name="fecha"]') : null;

    // Clic en un día del calendario -> abrir modal con la fecha puesta
    document.querySelectorAll('.ds-day[data-fecha]').forEach(function (cell) {
      if (cell.classList.contains('ds-past')) return;
      function abrir() {
        if (inputFecha) { inputFecha.value = cell.getAttribute('data-fecha'); }
        var m = modal(modalNueva);
        if (m) m.show();
      }
      cell.addEventListener('click', function (e) {
        // no abrir si se tocó un chip (solo informativo)
        if (e.target.closest('.ds-chip')) return;
        abrir();
      });
      cell.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); abrir(); }
      });
    });

    // Rechazar (Soporte): poner la URL en el formulario y abrir el modal
    var formRechazar = $('#formRechazar');
    var detalle = $('#rechazarDetalle');
    document.querySelectorAll('.ds-rechazar').forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (formRechazar) formRechazar.setAttribute('action', btn.getAttribute('data-url'));
        if (detalle) detalle.textContent = btn.getAttribute('data-detalle') || '';
        var m = modal($('#modalRechazar'));
        if (m) m.show();
      });
    });

    // Confirmar cancelación
    document.querySelectorAll('form.ds-cancelar').forEach(function (f) {
      f.addEventListener('submit', function (e) {
        if (!window.confirm('¿Cancelar esta reserva de DataShow?')) e.preventDefault();
      });
    });
  });
})();
