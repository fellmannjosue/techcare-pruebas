/* tc_responsive.js — <--- hecho por claude code (28-sep-2026): capa responsiva global.
   Envuelve toda <table class="table"> que NO esté dentro de .table-responsive en un
   <div class="tc-scroll-x"> (el CSS solo activa el scroll horizontal en < 992px, así en
   escritorio no se recortan dropdowns ni popovers). Se registra ANTES que los scripts de
   página (va junto a dt_guard.js), de modo que DataTables ya encuentra la tabla envuelta.
   Sin jQuery: vanilla. */
(function () {
  'use strict';
  function envolver(tabla) {
    if (tabla.closest('.table-responsive, .tc-scroll-x, .dataTables_scroll, .modal-body .table-responsive')) return;
    if (tabla.closest('.dataTables_wrapper') && tabla.parentElement.classList.contains('table-responsive')) return;
    var div = document.createElement('div');
    div.className = 'tc-scroll-x';
    tabla.parentNode.insertBefore(div, tabla);
    div.appendChild(tabla);
  }
  function run() {
    document.querySelectorAll('table.table').forEach(envolver);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', run);
  else run();
  // Tablas que aparecen después (AJAX, tabs cargados tarde)
  if (window.MutationObserver) {
    var pendiente = null;
    new MutationObserver(function () {
      if (pendiente) return;
      pendiente = setTimeout(function () { pendiente = null; run(); }, 150);
    }).observe(document.documentElement, { childList: true, subtree: true });
  }
})();
