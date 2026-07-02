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
