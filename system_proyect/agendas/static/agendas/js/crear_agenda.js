/* crear_agenda.js — <--- hecho por claude code (15-oct-2026): pestaña Crear agenda (pruebas). Un solo global: CREAR_AGENDA. */
(function () {
  'use strict';
  var form = document.getElementById('ca-form');
  if (!form) return;
  var semana = document.getElementById('ca-semana'), rango = document.getElementById('ca-rango');
  var cuenta = document.getElementById('ca-cuenta'), btn = document.getElementById('ca-btn');
  var MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

  function pintarRango() {
    var v = semana.value;
    if (!v) { rango.textContent = ''; return; }
    var p = v.split('-'), d = new Date(+p[0], +p[1] - 1, +p[2]);
    var lunes = new Date(d); lunes.setDate(d.getDate() - ((d.getDay() + 6) % 7));
    var viernes = new Date(lunes); viernes.setDate(lunes.getDate() + 4);
    rango.textContent = 'Semana del lunes ' + lunes.getDate() + ' de ' + MESES[lunes.getMonth()] + ' al viernes ' +
      viernes.getDate() + ' de ' + MESES[viernes.getMonth()] + ' de ' + viernes.getFullYear();
  }
  function libres(area) { return Array.prototype.slice.call((area || form).querySelectorAll('.ca-grado-chk:not(:disabled)')); }
  function refrescar() {
    form.querySelectorAll('.ca-area').forEach(function (a) {
      var l = libres(a), n = l.filter(function (c) { return c.checked; }).length, chk = a.querySelector('.ca-area-chk');
      chk.checked = l.length > 0 && n === l.length; chk.indeterminate = n > 0 && n < l.length; chk.disabled = !l.length;
    });
    var n = libres().filter(function (c) { return c.checked; }).length;
    cuenta.textContent = n === 1 ? '1 grado marcado' : n + ' grados marcados';
    btn.disabled = !n;
    btn.innerHTML = '<i class="ti ti-calendar-plus me-1"></i>' + (n > 1 ? 'Crear ' + n + ' agendas' : 'Crear agenda');
  }
  form.addEventListener('change', function (e) {
    if (e.target.classList.contains('ca-area-chk')) {
      libres(e.target.closest('.ca-area')).forEach(function (c) { c.checked = e.target.checked; });
    }
    refrescar();
  });
  document.getElementById('ca-todos').addEventListener('click', function () { libres().forEach(function (c) { c.checked = true; }); refrescar(); });
  document.getElementById('ca-ninguno').addEventListener('click', function () { libres().forEach(function (c) { c.checked = false; }); refrescar(); });
  semana.addEventListener('change', pintarRango);
  form.addEventListener('submit', function () { btn.disabled = true; });
  pintarRango(); refrescar();
  window.CREAR_AGENDA = { refrescar: refrescar };
})();
