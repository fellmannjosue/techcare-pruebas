/* agregar_modal.js — <--- hecho por claude code (22-oct-2026): abre el modal "Agregar" del inventario
   cuando se llega desde el launcher (?nuevo=1) o cuando el formulario volvió con errores de validación
   (data-errores="1"). Un solo global: INV_AGREGAR_MODAL. */
(function () {
  'use strict';
  function abrir() {
    var el = document.getElementById('modalAgregarInv');
    if (!el || !(window.bootstrap && bootstrap.Modal)) return;
    bootstrap.Modal.getOrCreateInstance(el).show();
  }
  document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('modalAgregarInv');
    if (!el) return;
    var nuevo = new URLSearchParams(window.location.search).get('nuevo');
    if (nuevo === '1' || el.dataset.errores === '1') abrir();
  });
  window.INV_AGREGAR_MODAL = { abrir: abrir };
})();
