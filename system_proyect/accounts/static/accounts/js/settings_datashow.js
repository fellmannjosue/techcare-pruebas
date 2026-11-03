/* <--- hecho por claude code (03-nov-2026): Configuración → Acceso a DataShow.
   Buscar usuario, marcar/quitar los visibles y contador de seleccionados. */
(function () {
  var buscar = document.getElementById('ds-buscar');
  var tabla = document.getElementById('ds-tabla');
  var contador = document.getElementById('ds-contador');
  var btnTodos = document.getElementById('ds-todos');
  var btnNinguno = document.getElementById('ds-ninguno');
  if (!tabla) return;

  function filas() { return Array.prototype.slice.call(tabla.querySelectorAll('tbody .ds-fila')); }
  function visibles() { return filas().filter(function (f) { return f.style.display !== 'none'; }); }

  function recontar() {
    if (!contador) return;
    contador.textContent = tabla.querySelectorAll('.ds-check:checked').length;
  }

  function filtrar() {
    var q = (buscar.value || '').trim().toLowerCase();
    filas().forEach(function (f) {
      var txt = f.textContent.toLowerCase();
      f.style.display = (!q || txt.indexOf(q) !== -1) ? '' : 'none';
    });
  }

  if (buscar) buscar.addEventListener('input', filtrar);
  tabla.addEventListener('change', function (e) {
    if (e.target && e.target.classList.contains('ds-check')) recontar();
  });
  if (btnTodos) btnTodos.addEventListener('click', function () {
    visibles().forEach(function (f) { var c = f.querySelector('.ds-check'); if (c) c.checked = true; });
    recontar();
  });
  if (btnNinguno) btnNinguno.addEventListener('click', function () {
    visibles().forEach(function (f) { var c = f.querySelector('.ds-check'); if (c) c.checked = false; });
    recontar();
  });

  recontar();
})();
