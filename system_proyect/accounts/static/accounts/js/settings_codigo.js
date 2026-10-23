/* settings_codigo.js — <--- hecho por claude code (16-oct-2026): ordenar la tabla de Código del sistema por columna.
   Un solo global: CODIGO_SISTEMA. */
(function () {
  'use strict';
  var tabla = document.getElementById('cod-tabla');
  if (!tabla) return;
  var cuerpo = tabla.tBodies[0], cabs = tabla.tHead.rows[0].cells;
  Array.prototype.forEach.call(cabs, function (th, i) {
    if (!th.dataset.tipo) return;
    th.addEventListener('click', function () {
      var asc = !th.classList.contains('cod-orden-asc');
      Array.prototype.forEach.call(cabs, function (x) { x.classList.remove('cod-orden-asc', 'cod-orden-desc'); });
      th.classList.add(asc ? 'cod-orden-asc' : 'cod-orden-desc');
      var filas = Array.prototype.slice.call(cuerpo.rows);
      filas.sort(function (a, b) {
        var x = a.cells[i].dataset.v || '', y = b.cells[i].dataset.v || '';
        var r = th.dataset.tipo === 'n' ? (parseFloat(x) || 0) - (parseFloat(y) || 0) : x.localeCompare(y, 'es');
        return asc ? r : -r;
      });
      filas.forEach(function (f) { cuerpo.appendChild(f); });
    });
  });
  window.CODIGO_SISTEMA = { tabla: tabla };
})();
