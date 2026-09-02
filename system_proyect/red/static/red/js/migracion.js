/* <--- hecho por claude code: migración de VLAN — "seleccionar todos" + confirmación final */
(function () {
  var todos = document.getElementById('chk-todos');
  var form = document.getElementById('form-migrar');
  if (!form) return;
  var devs = function () { return form.querySelectorAll('.chk-dev'); };

  if (todos) todos.addEventListener('change', function () {
    devs().forEach(function (c) { c.checked = todos.checked; });
  });

  form.addEventListener('submit', function (e) {
    var n = Array.prototype.filter.call(devs(), function (c) { return c.checked; }).length;
    if (n === 0) { e.preventDefault(); alert('Selecciona al menos un dispositivo.'); return; }
    if (!confirm('Se migrarán ' + n + ' equipo(s) y se les asignará una IP nueva. ¿Continuar?')) e.preventDefault();
  });
})();
