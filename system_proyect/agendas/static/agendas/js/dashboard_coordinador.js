/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #dashboard_coordinador-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("dashboard_coordinador-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
  };
})();

window._PAGE = { csrf: CFG.v0 };

(function () {
  var act = document.getElementById('bq-activo');
  if (act) act.addEventListener('change', function () {
    document.getElementById('bq-activo-lbl').textContent = act.checked ? 'Activo' : 'Inactivo';
  });
  var all = document.getElementById('bq-all'), none = document.getElementById('bq-none');
  if (all)  all.addEventListener('click',  function () { document.querySelectorAll('.bq-maestro').forEach(function (c) { c.checked = true; }); });
  if (none) none.addEventListener('click', function () { document.querySelectorAll('.bq-maestro').forEach(function (c) { c.checked = false; }); });
  var form = document.getElementById('form-bloqueo');
  if (form) form.addEventListener('submit', function (e) {
    e.preventDefault();
    var fd = new FormData();
    fd.append('csrfmiddlewaretoken', window._PAGE.csrf);
    fd.append('activo', act.checked ? '1' : '0');
    fd.append('mensaje', document.getElementById('bq-mensaje').value);
    fd.append('mensaje_jueves', document.getElementById('bq-mensaje-jue').value);
    fd.append('mensaje_viernes', document.getElementById('bq-mensaje-vie').value);
    fd.append('jueves_limite', document.getElementById('bq-jueves').value);
    document.querySelectorAll('.bq-maestro:checked').forEach(function (c) { fd.append('maestros', c.value); });
    var btn = document.getElementById('bq-guardar'); btn.disabled = true;
    fetch(CFG.v1, { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (d) { btn.disabled = false; if (d.ok) { location.reload(); } else { alert(d.error || 'Error'); } })
      .catch(function () { btn.disabled = false; alert('Error de red'); });
  });
})();
