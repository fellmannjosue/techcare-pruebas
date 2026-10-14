/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(function(){});});}

/* <--- hecho por claude code (17-sep-2026): popover de detalle en la celda Modelo (.inv-pop).
   Se crea al primer hover (DataTables pagina y las filas ocultas no están en el DOM) y se
   cierra al cambiar de página/orden/búsqueda. */
(function () {
  function abrir(e) {
    var el = e.target.closest ? e.target.closest('.inv-pop') : null;
    if (!el || !window.bootstrap || !bootstrap.Popover) return;
    if (!bootstrap.Popover.getInstance(el)) bootstrap.Popover.getOrCreateInstance(el, { container: 'body', sanitize: false }).show();
  }
  document.addEventListener('mouseover', abrir);
  document.addEventListener('focusin', abrir);
  // (17-sep-2026) Solo un recuadro abierto a la vez: el popover abre con hover y con foco, y al hacer clic
  // en un Modelo ese quedaba abierto mientras se abría el de otra fila.
  document.addEventListener('show.bs.popover', function (e) {
    document.querySelectorAll('.inv-pop').forEach(function (el) {
      if (el === e.target) return;
      var i = window.bootstrap && bootstrap.Popover.getInstance(el);
      if (i) i.hide();
      if (document.activeElement === el) el.blur();
    });
  });
  document.addEventListener('DOMContentLoaded', function () {
    if (!window.jQuery) return;
    jQuery(document).on('draw.dt', function () {
      document.querySelectorAll('.inv-pop').forEach(function (el) { var i = window.bootstrap && bootstrap.Popover.getInstance(el); if (i) i.hide(); });
    });
  });
})();
