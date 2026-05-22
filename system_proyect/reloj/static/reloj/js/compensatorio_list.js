// ── Modal: Tiempo Extra Autorizado (only when canEditExtra) ──
if (window._PAGE.canEditExtra) {
(function() {
  const URL_SET_EXTRA = window._PAGE.urlSetExtra;
  let _emp = '', _fecha = '';

  document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn-set-extra');
    if (!btn) return;
    _emp   = btn.dataset.emp;
    _fecha = btn.dataset.fecha;
    document.getElementById('extra-modal-empleado').textContent =
      btn.dataset.nombre + ' · ' + btn.dataset.fecha;
    document.getElementById('extra-minutos').value       = btn.dataset.minutos || 0;
    document.getElementById('extra-razon').value         = btn.dataset.razon || '';
    document.getElementById('extra-comentario').value    = btn.dataset.comentario || '';
    document.getElementById('extra-autorizado-por').value = btn.dataset.autorizado || '';
    const modal = new bootstrap.Modal(document.getElementById('modalExtraDia'));
    modal.show();
  });

  document.getElementById('btn-guardar-extra').addEventListener('click', function() {
    const minutos       = parseInt(document.getElementById('extra-minutos').value) || 0;
    const razon         = document.getElementById('extra-razon').value.trim();
    const comentario    = document.getElementById('extra-comentario').value.trim();
    const autorizado_por = document.getElementById('extra-autorizado-por').value.trim();

    fetch(URL_SET_EXTRA, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookie('csrftoken')},
      body: JSON.stringify({emp_code: _emp, fecha: _fecha, minutos, razon, comentario, autorizado_por})
    })
    .then(r => r.json())
    .then(data => {
      if (!data.ok) { alert('Error: ' + (data.error || 'desconocido')); return; }
      bootstrap.Modal.getInstance(document.getElementById('modalExtraDia')).hide();
      // Actualizar la celda sin recargar
      const dateKey = _fecha.replaceAll('-', '');
      const cell = document.getElementById('extra-cell-' + _emp + '-' + dateKey);
      if (cell) {
        const badgeEl = cell.querySelector('.extra-badge');
        if (badgeEl) {
          if (data.minutos > 0) {
            badgeEl.className = 'badge bg-blue-lt text-blue extra-badge';
            badgeEl.innerHTML = '<i class="ti ti-clock-bolt me-1"></i>' + data.minutos + 'm';
          } else {
            badgeEl.className = 'text-muted extra-badge';
            badgeEl.textContent = '—';
          }
        }
        // Actualizar data attrs del botón
        const btnRow = cell.querySelector('.btn-set-extra');
        if (btnRow) {
          btnRow.dataset.minutos    = data.minutos;
          btnRow.dataset.razon      = data.razon;
          btnRow.dataset.comentario = data.comentario;
          btnRow.dataset.autorizado = data.autorizado_por;
        }
      }
    })
    .catch(() => alert('Error de conexión.'));
  });

  function getCookie(name) {
    const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
  }
})();
}

// ── DataTable ──
document.addEventListener('DOMContentLoaded', function() {
  if (typeof $.fn.DataTable !== 'undefined') {
    $('#tabla-compensatorio').DataTable({
      order: [[2, 'desc']],
      pageLength: 25,
      language: {
        url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json'
      }
    });
  }
});
