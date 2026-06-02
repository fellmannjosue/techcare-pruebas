/* <--- hecho por claude code: historial médico — tabla global + tabla agrupada + modal estilo conducta */
(function () {
  'use strict';

  const CFG     = window._MH || {};
  const URL_H   = CFG.urlHistorial || '';
  const URL_PDF = CFG.urlPdf       || '';

  const dtLang = { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' };

  // ── DataTable 1: Todos los registros ──────────────────────────────────────
  $('#tabla-historial').DataTable({
    order:      [[1, 'desc']],   // fecha desc
    pageLength: 25,
    lengthMenu: [10, 25, 50, 100],
    language:   dtLang,
    columnDefs: [
      { orderable: false, targets: [5] },   // columna Historial no ordena
    ],
  });

  // ── DataTable 2: Por Alumno (lazy — se inicia al mostrar el tab) ──────────
  let dtAgrupado = null;
  document.getElementById('tab-agrupado-btn')?.addEventListener('shown.bs.tab', function () {
    if (!dtAgrupado) {
      dtAgrupado = $('#tabla-agrupado').DataTable({
        order:      [[3, 'desc']],   // última visita desc
        pageLength: 25,
        lengthMenu: [10, 25, 50, 100],
        language:   dtLang,
        columnDefs: [
          { orderable: false, targets: [4] },
        ],
      });
    } else {
      dtAgrupado.columns.adjust().draw(false);
    }
  });

  // ── Modal ──────────────────────────────────────────────────────────────────
  const modalEl  = document.getElementById('modalHistorialAlumno');
  const modal    = modalEl ? new bootstrap.Modal(modalEl) : null;
  const elContent = document.getElementById('historial-content');
  const elTotal   = document.getElementById('modal-total-registros');

  function abrirHistorial(estudiante) {
    if (!modal) return;

    // Mostrar spinner
    elContent.innerHTML = `
      <div class="text-center py-5">
        <span class="spinner-border text-cyan" role="status"></span>
        <p class="text-muted mt-2 mb-0">Cargando historial…</p>
      </div>`;
    elTotal.textContent = '';
    modal.show();

    fetch(`${URL_H}?student=${encodeURIComponent(estudiante)}`, {
      credentials: 'same-origin',
    })
      .then(r => r.ok ? r.json() : Promise.reject(r))
      .then(data => {
        const lista = data.history || [];

        if (!lista.length) {
          elContent.innerHTML = `
            <div class="text-center py-5">
              <i class="ti ti-mood-empty d-block mb-2 opacity-25" style="font-size:3rem;"></i>
              <p class="text-muted mb-0">Sin registros para este alumno.</p>
            </div>`;
          return;
        }

        const filas = lista.map(h => {
          const pdfUrl = URL_PDF.replace('{pk}', h.pk);
          return `
            <tr>
              <td class="fw-semibold">${_esc(h.student || estudiante)}</td>
              <td><span class="badge bg-cyan-lt text-cyan fw-semibold">Atención Médica</span></td>
              <td class="text-muted small">${h.date_time}</td>
              <td class="small">
                ${_esc(h.reason)}
              </td>
              <td class="small text-muted">${_esc(h.grade)}</td>
              <td class="small text-muted">${_esc(h.attendant)}</td>
              <td>
                <a href="${pdfUrl}" target="_blank" rel="noopener"
                   class="btn btn-sm btn-ghost-secondary" title="Ver PDF">
                  <i class="ti ti-file-description"></i>
                </a>
              </td>
            </tr>`;
        }).join('');

        elContent.innerHTML = `
          <table class="table table-vcenter table-hover table-sm mb-0">
            <thead class="table-light">
              <tr>
                <th>Estudiante</th>
                <th style="width:130px;">Tipo</th>
                <th style="width:120px;">Fecha</th>
                <th>Motivo</th>
                <th style="width:150px;">Grado</th>
                <th style="width:130px;">Responsable</th>
                <th style="width:60px;" class="text-center">Acciones</th>
              </tr>
            </thead>
            <tbody>${filas}</tbody>
          </table>`;

        elTotal.textContent =
          `${lista.length} atención${lista.length !== 1 ? 'es' : ''} registrada${lista.length !== 1 ? 's' : ''}`;
      })
      .catch(() => {
        elContent.innerHTML = `
          <div class="text-center text-danger py-5">
            <i class="ti ti-alert-circle d-block mb-2" style="font-size:2rem;"></i>
            Error al cargar el historial.
          </div>`;
      });
  }

  // ── Evento: click en botón historial (ambas tablas) ───────────────────────
  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-ver-historial');
    if (!btn) return;
    abrirHistorial(btn.dataset.estudiante);
  });

  // ── Helper: escapar HTML ──────────────────────────────────────────────────
  function _esc(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

})();
