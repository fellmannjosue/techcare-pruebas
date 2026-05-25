/* materias_docentes_bl.js — hecho por claude code: CRUD inline + DataTables ordenable */
(function () {
  'use strict';

  const M    = window._MATERIAS;
  const CSRF = M.csrf;

  /* ── DataTable ── */
  let dt = null;
  $(document).ready(function() {
    dt = $('#tabla-materias').DataTable({
      order:      [[1, 'asc']],   // ordenar por Docente A-Z por defecto
      pageLength: 25,
      language:   { url: '//cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json' },
      columnDefs: [
        { orderable: false, targets: [2, 3, 4] }  // Coord, Activo, Acciones — no ordenables
      ],
      // El buscador de DT reemplaza al servidor — queda integrado en la UI
      dom: '<"d-flex align-items-center justify-content-between mb-2"lf>rtip',
    });
  });

  /* ── Modal ── */
  let modal = null;
  function getModal() {
    if (!modal) modal = new bootstrap.Modal(document.getElementById('modalMateria'));
    return modal;
  }

  function resetForm() {
    document.getElementById('edit-pk').value       = '';
    document.getElementById('edit-materia').value  = '';
    document.getElementById('edit-docente').value  = '';
    document.getElementById('edit-activo').checked = true;
    document.querySelectorAll('#coord-checks input[type=checkbox]').forEach(c => c.checked = false);
    document.getElementById('modal-error').classList.add('d-none');
  }

  function abrirCrear() {
    resetForm();
    document.getElementById('modal-titulo').innerHTML =
      '<i class="ti ti-plus me-2 text-primary"></i>Nueva Materia';
    getModal().show();
    setTimeout(() => document.getElementById('edit-materia').focus(), 300);
  }

  function abrirEditar(row) {
    resetForm();
    const pk    = row.dataset.pk;
    const coord = (row.dataset.coordinador || '').split(',').map(s => s.trim()).filter(Boolean);
    document.getElementById('edit-pk').value       = pk;
    document.getElementById('edit-materia').value  = row.dataset.materia;
    document.getElementById('edit-docente').value  = row.dataset.docente;
    document.getElementById('edit-activo').checked = row.dataset.activo === '1';
    coord.forEach(c => {
      const chk = document.querySelector(`#coord-checks input[value="${c}"]`);
      if (chk) chk.checked = true;
    });
    document.getElementById('modal-titulo').innerHTML =
      '<i class="ti ti-pencil me-2 text-primary"></i>Editar Materia';
    getModal().show();
  }

  /* ── Botones Agregar ── */
  document.getElementById('btn-nueva-materia')?.addEventListener('click', abrirCrear);
  document.getElementById('btn-nueva-materia-footer')?.addEventListener('click', abrirCrear);

  /* ── Click en tabla (delegado en document para compatibilidad con DataTables) ── */
  document.getElementById('tabla-materias').addEventListener('click', function(e) {
    if (e.target.closest('.btn-editar')) {
      const pk  = e.target.closest('.btn-editar').dataset.pk;
      const row = document.querySelector(`tr[data-pk="${pk}"]`);
      if (row) abrirEditar(row);
      return;
    }
    if (e.target.closest('.btn-eliminar')) {
      const btn    = e.target.closest('.btn-eliminar');
      eliminar(btn.dataset.pk, btn.dataset.nombre);
      return;
    }
    // Clic en la fila (no en botones)
    const row = e.target.closest('tr.fila-materia');
    if (row && !e.target.closest('td:last-child')) abrirEditar(row);
  });

  /* ── Guardar (crear o editar) ── */
  document.getElementById('btn-guardar-materia').addEventListener('click', async function() {
    const pk      = document.getElementById('edit-pk').value;
    const materia = document.getElementById('edit-materia').value.trim();
    const docente = document.getElementById('edit-docente').value.trim();
    const activo  = document.getElementById('edit-activo').checked;
    const coords  = [...document.querySelectorAll('#coord-checks input:checked')].map(c => c.value);
    const errDiv  = document.getElementById('modal-error');
    errDiv.classList.add('d-none');

    if (!materia || !docente) {
      errDiv.querySelector('.alert').textContent = 'Materia y docente son obligatorios.';
      errDiv.classList.remove('d-none');
      return;
    }

    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

    const url = pk ? M.urlUpdate.replace('{pk}', pk) : M.urlCreate;

    try {
      const res  = await fetch(url, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body:    JSON.stringify({ materia, docente, coordinadores: coords, activo }),
      });
      const data = await res.json();

      if (!data.ok) {
        errDiv.querySelector('.alert').textContent = data.error || 'Error al guardar.';
        errDiv.classList.remove('d-none');
      } else {
        getModal().hide();
        if (pk) {
          actualizarFila(pk, data);
        } else {
          agregarFila(data);
        }
        actualizarContadores();
      }
    } catch(e) {
      errDiv.querySelector('.alert').textContent = 'Error de conexión.';
      errDiv.classList.remove('d-none');
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
  });

  /* ── Eliminar ── */
  async function eliminar(pk, nombre) {
    const ok = await Swal.fire({
      title: '¿Eliminar materia?',
      html:  `<strong>${nombre}</strong><br><span class="text-muted small">Esta acción no se puede deshacer.</span>`,
      icon:  'warning',
      showCancelButton:    true,
      confirmButtonText:   'Sí, eliminar',
      cancelButtonText:    'Cancelar',
      confirmButtonColor:  '#d63939',
    });
    if (!ok.isConfirmed) return;

    const res  = await fetch(M.urlDelete.replace('{pk}', pk), {
      method: 'POST', headers: { 'X-CSRFToken': CSRF },
    });
    const data = await res.json();
    if (data.ok) {
      if (dt) {
        // Eliminar la fila desde la API de DataTables
        const rowNode = document.querySelector(`tr[data-pk="${pk}"]`);
        if (rowNode) dt.row(rowNode).remove().draw(false);
      } else {
        document.querySelector(`tr[data-pk="${pk}"]`)?.remove();
      }
      actualizarContadores();
    } else {
      Swal.fire('Error', data.error || 'No se pudo eliminar.', 'error');
    }
  }

  /* ── Render helpers ── */
  function coordBadgesHtml(coordStr) {
    if (!coordStr) return '<span class="text-muted small">—</span>';
    const codes = coordStr.split(',').map(s => s.trim()).filter(Boolean);
    return codes.map(code => {
      const cfg = M.configs.find(c => c.codigo === code);
      if (!cfg) return `<span class="badge-coord me-1" style="background:#6c757d;">${code}</span>`;
      return `<span class="badge-coord me-1" style="background:${cfg.color};">${cfg.codigo} – ${cfg.nombre}</span>`;
    }).join('');
  }

  function activoBadgeHtml(activo) {
    return activo
      ? '<span class="badge bg-green-lt text-green fw-semibold"><i class="ti ti-check me-1"></i>Sí</span>'
      : '<span class="badge bg-red-lt text-red fw-semibold"><i class="ti ti-x me-1"></i>No</span>';
  }

  function accionesBtnsHtml(pk, nombre) {
    const n = escHtml(nombre);
    return `
      <button class="btn btn-sm btn-ghost-primary btn-editar px-2 py-1" title="Editar" data-pk="${pk}">
        <i class="ti ti-pencil"></i>
      </button>
      <button class="btn btn-sm btn-ghost-danger btn-eliminar px-2 py-1" title="Eliminar"
              data-pk="${pk}" data-nombre="${n}">
        <i class="ti ti-trash"></i>
      </button>`;
  }

  function actualizarFila(pk, data) {
    const row = document.querySelector(`tr[data-pk="${pk}"]`);
    if (!row) return;
    const coordStr = data.coordinador || '';
    row.dataset.materia     = data.materia;
    row.dataset.docente     = data.docente;
    row.dataset.coordinador = coordStr;
    row.dataset.activo      = data.activo ? '1' : '0';
    const cells = row.querySelectorAll('td');
    cells[0].textContent = data.materia;
    cells[1].textContent = data.docente;
    cells[2].innerHTML   = coordBadgesHtml(coordStr);
    cells[3].innerHTML   = activoBadgeHtml(data.activo);
    cells[4].innerHTML   = accionesBtnsHtml(pk, data.materia);
    // Informar a DataTables del cambio para que reordene
    if (dt) dt.row(row).invalidate().draw(false);
  }

  function agregarFila(data) {
    const coordStr = data.coordinador || '';
    const tr = document.createElement('tr');
    tr.className = 'fila-materia';
    tr.dataset.pk          = data.pk;
    tr.dataset.materia     = data.materia;
    tr.dataset.docente     = data.docente;
    tr.dataset.coordinador = coordStr;
    tr.dataset.activo      = data.activo ? '1' : '0';
    tr.innerHTML = `
      <td class="fw-semibold">${escHtml(data.materia)}</td>
      <td class="text-muted">${escHtml(data.docente)}</td>
      <td>${coordBadgesHtml(coordStr)}</td>
      <td class="text-center">${activoBadgeHtml(data.activo)}</td>
      <td class="text-center">${accionesBtnsHtml(data.pk, data.materia)}</td>`;

    if (dt) {
      dt.row.add(tr).draw(false);
    } else {
      document.getElementById('tbody-materias').appendChild(tr);
    }
  }

  function actualizarContadores() {
    const n = dt
      ? dt.data().length
      : document.querySelectorAll('#tbody-materias tr.fila-materia').length;
    const el1 = document.getElementById('total-count');
    const el2 = document.getElementById('badge-total');
    const el3 = document.getElementById('footer-total');
    if (el1) el1.textContent = n;
    if (el2) el2.textContent = n + ' registros';
    if (el3) el3.textContent = n;
  }

  function escHtml(str) {
    return String(str)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;')
      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

})();
