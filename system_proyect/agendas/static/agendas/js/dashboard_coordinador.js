/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #dashboard_coordinador-config (un .js no lo procesa Django). */
const CFG_AGENDAS_DASHBOARD_COORDINADOR = (function(){
  var d = document.getElementById("dashboard_coordinador-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
  };
})();

window._PAGE = { csrf: CFG_AGENDAS_DASHBOARD_COORDINADOR.v0 };

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
    fetch(CFG_AGENDAS_DASHBOARD_COORDINADOR.v1, { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (d) { btn.disabled = false; if (d.ok) { location.reload(); } else { alert(d.error || 'Error'); } })
      .catch(function () { btn.disabled = false; alert('Error de red'); });
  });
})();


/* <--- hecho por claude code: lógica recuperada de d5d2026 (DataTable + modal de
   eliminar agenda con confirmación en 2 pasos). Se perdió al extraer el JS; el botón
   'eliminar agenda' y el detalle no hacían nada. Lee window._PAGE.csrf (definido arriba). */
/* dashboard_coordinador.js – agendas */
$(document).ready(function () {
  // Las agendas ahora se agrupan por tabs (parcial → semana); ya no hay una sola tabla.
  if ($('#tablaAgendas').length) {
    $('#tablaAgendas').DataTable({
      order: [[4, 'desc']],
      language: { url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json' }
    });
  }
});

(function () {
  var PAGE = window._PAGE || {};
  var CSRF = PAGE.csrf || '';

  var _pk  = null;
  var _row = null;

  var modal   = new bootstrap.Modal(document.getElementById('modalEliminarAgenda'));
  var step1   = document.getElementById('ag-step-1');
  var step2   = document.getElementById('ag-step-2');
  var btn1    = document.getElementById('ag-btn-step1');
  var btn2    = document.getElementById('ag-btn-step2');
  var detalle = document.getElementById('ag-detalle');
  var title   = document.getElementById('ag-modal-title');

  function resetModal() {
    step1.classList.remove('d-none');
    step2.classList.add('d-none');
    btn1.classList.remove('d-none');
    btn2.classList.add('d-none');
    btn2.disabled = false;
    btn2.innerHTML = '<i class="ti ti-trash me-1"></i>Sí, ELIMINAR';
    title.innerHTML = '<i class="ti ti-alert-triangle me-2 text-warning"></i>Eliminar agenda';
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest('.btn-eliminar-agenda');
    if (!btn) return;
    _pk  = btn.dataset.pk;
    _row = btn.closest('tr');
    detalle.textContent = btn.dataset.grado + ' · ' + btn.dataset.semana + ' · ' + btn.dataset.maestro;
    resetModal();
    modal.show();
  });

  btn1.addEventListener('click', function () {
    step1.classList.add('d-none');
    step2.classList.remove('d-none');
    btn1.classList.add('d-none');
    btn2.classList.remove('d-none');
    title.innerHTML = '<i class="ti ti-skull me-2 text-danger"></i>Confirmación final';
  });

  btn2.addEventListener('click', async function () {
    btn2.disabled = true;
    btn2.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';
    try {
      var res  = await fetch('/agendas/' + _pk + '/eliminar/', {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF }
      });
      var data = await res.json();
      if (data.ok) {
        modal.hide();
        if (_row) _row.remove();
      } else {
        alert('Error: ' + (data.error || 'No se pudo eliminar.'));
        resetModal();
      }
    } catch (err) {
      alert('Error de red. Intenta de nuevo.');
      resetModal();
    }
  });

  document.getElementById('modalEliminarAgenda').addEventListener('hidden.bs.modal', resetModal);
})();
