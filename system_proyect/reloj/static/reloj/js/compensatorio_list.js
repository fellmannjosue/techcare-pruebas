// ── Actualizar resumen de totales en la card superior ──
function actualizarResumenTotales(delta) {
  const elTotal    = document.getElementById('resumen-total-min');
  const elTiempo   = document.getElementById('resumen-tiempo-txt');
  const elExtraDiv = document.getElementById('resumen-extra-div');
  const elExtraMin = document.getElementById('resumen-extra-min');
  if (!elTotal) return;

  const nuevoTotal = (parseInt(elTotal.textContent.trim()) || 0) + delta;
  elTotal.textContent = nuevoTotal;

  // Actualizar "Xh Xm de tiempo compensatorio acumulado"
  if (elTiempo) {
    const h    = Math.floor(nuevoTotal / 60);
    const m    = nuevoTotal % 60;
    const hTxt = h > 0 ? h + 'h ' : '';
    elTiempo.innerHTML = hTxt + m + 'm <span class="text-muted fw-normal fs-5 ms-1">de tiempo compensatorio acumulado</span>';
  }

  // Actualizar "incl. Xm extra"
  if (elExtraMin && elExtraDiv) {
    const nuevoExtra = (parseInt(elExtraMin.textContent.trim()) || 0) + delta;
    elExtraMin.textContent = nuevoExtra;
    if (nuevoExtra > 0) {
      elExtraDiv.classList.remove('d-none');
    } else {
      elExtraDiv.classList.add('d-none');
    }
  }
}

// ── Modal: Tiempo Extra Autorizado (only when canEditExtra) ──
if (window._PAGE.canEditExtra) {
(function() {
  const URL_SET_EXTRA = window._PAGE.urlSetExtra;
  let _emp = '', _fecha = '', _oldMinutos = 0;

  document.addEventListener('click', function(e) {
    const btn = e.target.closest('.btn-set-extra');
    if (!btn) return;
    _emp         = btn.dataset.emp;
    _fecha       = btn.dataset.fecha;
    _oldMinutos  = parseInt(btn.dataset.minutos) || 0;
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

      // Actualizar resumen superior automáticamente
      const delta = data.minutos - _oldMinutos;
      actualizarResumenTotales(delta);
      _oldMinutos = data.minutos;
    })
    .catch(() => alert('Error de conexión.'));
  });

  function getCookie(name) {
    const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
  }
})();
}

// ── Formulario: Registrar tiempo extra por mes ──
(function() {
  const btn = document.getElementById('btn-te-mes-guardar');
  if (!btn) return;
  const url = window._PAGE.urlTeAddByEmp;
  if (!url) return;

  btn.addEventListener('click', async function() {
    const mes    = document.getElementById('te-mes-inp').value;       // "YYYY-MM"
    const min    = parseInt(document.getElementById('te-mes-min-inp').value);
    const razon  = (document.getElementById('te-mes-razon-inp').value || '').trim();
    const msgDiv = document.getElementById('te-mes-msg');
    msgDiv.className = 'd-none mt-2';
    msgDiv.innerHTML = '';

    if (!mes) {
      msgDiv.className = 'mt-2 alert alert-warning py-1 px-2 small';
      msgDiv.textContent = 'Selecciona un mes.';
      return;
    }
    if (!min || min <= 0) {
      msgDiv.className = 'mt-2 alert alert-warning py-1 px-2 small';
      msgDiv.textContent = 'Ingresa una cantidad de minutos válida.';
      return;
    }

    const fecha = mes + '-01';   // primer día del mes
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

    try {
      const res  = await fetch(url, {
        method:  'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': getCookieTe('csrftoken')},
        body:    JSON.stringify({ fecha, minutos: min, razon }),
      });
      const data = await res.json();
      if (data.ok) {
        document.getElementById('te-mes-min-inp').value   = '';
        document.getElementById('te-mes-razon-inp').value = '';
        msgDiv.className = 'mt-2 alert alert-success py-1 px-2 small';
        msgDiv.innerHTML = '<i class="ti ti-circle-check me-1"></i>Registrado: ' +
          min + ' min para ' + mes.replace('-', '/');
        // Actualizar resumen superior
        actualizarResumenTotales(min);
      } else {
        msgDiv.className = 'mt-2 alert alert-danger py-1 px-2 small';
        msgDiv.textContent = data.error || 'Error al guardar.';
      }
    } catch(e) {
      msgDiv.className = 'mt-2 alert alert-danger py-1 px-2 small';
      msgDiv.textContent = 'Error de conexión.';
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
  });

  function getCookieTe(name) {
    const v = document.cookie.match('(^|;) ?' + name + '=([^;]*)(;|$)');
    return v ? v[2] : null;
  }
})();

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
