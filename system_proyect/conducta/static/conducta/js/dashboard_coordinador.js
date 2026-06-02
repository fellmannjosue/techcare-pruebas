// dashboard_coordinador.js
// Requires window._PAGE to be defined inline by the template.

(function () {
  'use strict';

  /* ══════════════════════════════════════════════════════════════
     MODAL EDICIÓN INLINE — se define al TOPE del IIFE para que
     window._abrirEditar quede disponible ANTES de cualquier otro
     código que pudiera fallar (bootstrap.Modal, getElementById, etc.)
     <--- hecho por claude code
     ══════════════════════════════════════════════════════════════ */
  const URL_BASE = {
    conductual:  '/conducta/reporte-conductual/',
    informativo: '/conducta/reporte-informativo/',
    progress:    '/conducta/progress-report/',
  };

  function poblarFirma(area) {
    const sel = document.getElementById('me-firma');
    if (!sel) return;
    sel.innerHTML = '<option value="">— Sin firma —</option>';
    const lista = area === 'bilingue'
      ? (window._PAGE.coordsBL  || [])
      : (window._PAGE.coordsCOL || []);
    lista.forEach(function(c) {
      const opt = document.createElement('option');
      opt.value = c; opt.textContent = c;
      sel.appendChild(opt);
    });
  }

  // Función principal — busca el modal y sus elementos cada vez
  // para no depender de que estén en el DOM al cargar el script.
  async function abrirModalEditar(pk, tipo, area) {
    const modalEl = document.getElementById('modalEditarReporte');
    if (!modalEl) { console.warn('[editar] modalEditarReporte no encontrado'); return; }

    // Obtener o crear instancia de Bootstrap modal
    var bsModal = typeof bootstrap !== 'undefined'
      ? (bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl))
      : null;
    if (!bsModal) { console.warn('[editar] Bootstrap no disponible'); return; }

    const loading    = document.getElementById('me-loading');
    const bodyEl     = document.getElementById('me-body');
    const titleEl    = document.getElementById('me-title');

    if (loading) loading.classList.remove('d-none');
    if (bodyEl)  bodyEl.classList.add('d-none');
    if (titleEl) titleEl.innerHTML = '<i class="ti ti-pencil me-2 text-primary"></i>Editar Reporte';

    bsModal.show();

    try {
      const res  = await fetch(window._PAGE.urlEditarAjax + '?pk=' + pk + '&tipo=' + tipo);
      const data = await res.json();
      if (!data.ok) { alert('Error al cargar el reporte.'); bsModal.hide(); return; }

      var el = function(id) { return document.getElementById(id); };

      el('me-pk').value   = data.pk;
      el('me-tipo').value = data.tipo;
      el('me-alumno').textContent = data.alumno;
      el('me-grado').textContent  = data.grado;
      el('me-fecha').textContent  = data.fecha;

      var rowDocente = el('me-row-docente');
      var rowMateria = el('me-row-materia');
      if (tipo !== 'progress') {
        el('me-docente').textContent = data.docente || '—';
        el('me-materia').textContent = data.materia || '—';
        if (rowDocente) rowDocente.classList.remove('d-none');
        if (rowMateria) rowMateria.classList.remove('d-none');
      } else {
        if (rowDocente) rowDocente.classList.add('d-none');
        if (rowMateria) rowMateria.classList.add('d-none');
      }

      var rowTipo = el('me-row-tipo-reporte');
      if (tipo === 'informativo') {
        if (rowTipo) rowTipo.classList.remove('d-none');
        el('me-tipo-reporte').value = data.tipo_reporte || 'academico';
      } else {
        if (rowTipo) rowTipo.classList.add('d-none');
      }

      el('me-estado').value = data.estado || 'enviado';

      poblarFirma(data.area || area);
      el('me-firma').value = data.coordinador_firma || '';

      var rowComentario = el('me-row-comentario');
      if (tipo !== 'progress') {
        if (rowComentario) rowComentario.classList.remove('d-none');
        el('me-comentario').value = data.comentario || '';
      } else {
        if (rowComentario) rowComentario.classList.add('d-none');
      }

      el('me-comentario-coord').value = data.comentario_coordinador || '';

      var avisoIncisos = el('me-aviso-incisos');
      if (avisoIncisos) {
        avisoIncisos.classList[tipo === 'conductual' ? 'remove' : 'add']('d-none');
      }

      var linkCompleto = el('me-link-completo');
      if (linkCompleto) linkCompleto.href = (URL_BASE[tipo] || '/conducta/') + pk + '/editar/';

      var labels = { conductual: 'Conductual', informativo: 'Informativo', progress: 'Progress' };
      if (titleEl) titleEl.innerHTML =
        '<i class="ti ti-pencil me-2 text-primary"></i>Editar ' + (labels[tipo] || '') + ' #' + pk;

      if (loading) loading.classList.add('d-none');
      if (bodyEl)  bodyEl.classList.remove('d-none');

    } catch (err) {
      console.error('[editar] error:', err);
      alert('Error de red al cargar el reporte.');
      bsModal.hide();
    }
  }

  // ★ Exponer INMEDIATAMENTE — antes de cualquier código que pueda fallar
  window._abrirEditar = abrirModalEditar;

  // Botón Guardar del modal editar
  document.addEventListener('DOMContentLoaded', function() {});  // no-op, DOM ya ready
  var btnGuardar = document.getElementById('me-btn-guardar');
  if (btnGuardar) {
    btnGuardar.addEventListener('click', async function () {
      const form = document.getElementById('me-form');
      const fd   = new FormData(form);
      btnGuardar.disabled = true;
      btnGuardar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando…';
      try {
        const res  = await fetch(window._PAGE.urlEditarAjax, {
          method: 'POST',
          headers: { 'X-CSRFToken': window._PAGE.csrf },
          body: fd,
        });
        const data = await res.json();
        if (data.ok) {
          const modalEl = document.getElementById('modalEditarReporte');
          if (modalEl) {
            const bsM = bootstrap.Modal.getInstance(modalEl);
            if (bsM) bsM.hide();
          }
          // Actualizar badge de estado en la fila sin recargar
          const pk   = document.getElementById('me-pk').value;
          const tipo = document.getElementById('me-tipo').value;
          const row  = document.querySelector(
            '.btn-editar-inline[data-pk="' + pk + '"][data-tipo="' + tipo + '"]'
          );
          if (row) {
            const tr = row.closest('tr');
            if (tr) {
              const estadoVal = document.getElementById('me-estado').value;
              const badgesMap = {
                enviado:   ['bg-secondary-lt', 'text-secondary', 'Enviado'],
                revisando: ['bg-warning-lt',   'text-warning',   'Revisando'],
                revisado:  ['bg-blue-lt',      'text-blue',      'Revisado'],
                aprobado:  ['bg-success-lt',   'text-success',   'Aprobado'],
              };
              const bm = badgesMap[estadoVal] || badgesMap.enviado;
              const badgeEl = tr.querySelector(
                '.badge.bg-secondary-lt, .badge.bg-warning-lt, .badge.bg-blue-lt, .badge.bg-success-lt'
              );
              if (badgeEl && !badgeEl.classList.contains('bg-red-lt')
                          && !badgeEl.classList.contains('bg-orange-lt')
                          && !badgeEl.classList.contains('bg-teal-lt')) {
                badgeEl.className  = 'badge ' + bm[0] + ' ' + bm[1];
                badgeEl.textContent = bm[2];
              }
            }
          }
        } else {
          alert('Error: ' + (data.error || 'No se pudo guardar.'));
        }
      } catch (err) {
        console.error(err);
        alert('Error de red. Intenta de nuevo.');
      } finally {
        btnGuardar.disabled = false;
        btnGuardar.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
      }
    });
  }

  // Reset al cerrar modal editar
  var modalEditarEl = document.getElementById('modalEditarReporte');
  if (modalEditarEl) {
    modalEditarEl.addEventListener('hidden.bs.modal', function () {
      var loading = document.getElementById('me-loading');
      var bodyEl  = document.getElementById('me-body');
      if (loading) loading.classList.remove('d-none');
      if (bodyEl)  bodyEl.classList.add('d-none');
    });
  }

  /* ══════ REENVIAR REPORTES (solo superuser) ══════ */
  try {
    if (window._PAGE && window._PAGE.isSuperuser) {
      document.getElementById('btnConfirmarReenvio')?.addEventListener('click', async function () {
        const fecha = document.getElementById('inputFechaReenvio').value;
        if (!fecha) { alert('Selecciona una fecha.'); return; }
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';
        const bodyData = new URLSearchParams({ fecha });
        const res = await fetch(window._PAGE.urlReenviar, {
          method: 'POST',
          headers: { 'X-CSRFToken': window._PAGE.csrf, 'Content-Type': 'application/x-www-form-urlencoded' },
          body: bodyData
        });
        const data = await res.json();
        this.disabled = false;
        this.innerHTML = '<i class="ti ti-send me-1"></i>Enviar';
        const msgEl = document.getElementById('reenvioMsg');
        msgEl.className = 'alert mt-2 alert-' + (data.ok ? 'success' : 'danger');
        msgEl.textContent = data.ok ? 'Enviados: ' + data.enviados + ' notificaciones' : 'Error: ' + data.error;
        msgEl.classList.remove('d-none');
      });
    }
  } catch(e) { console.error('[reenviar]', e); }

  /* ══════ LIGHTBOX EVIDENCIA ══════ */
  try {
    document.querySelectorAll('.img-evidencia-click').forEach(function (img) {
      img.addEventListener('click', function () {
        var lbImg    = document.getElementById('lightboxImg');
        var lbTitulo = document.getElementById('lightboxTitulo');
        var lbEl     = document.getElementById('modalLightbox');
        if (lbImg)    lbImg.src = this.src;
        if (lbTitulo) lbTitulo.textContent = this.title || 'Evidencia';
        if (lbEl)     new bootstrap.Modal(lbEl).show();
      });
    });
  } catch(e) { console.error('[lightbox]', e); }

  /* ══════ ELIMINAR EVIDENCIA (doble confirmación) ══════ */
  try {
    (function () {
      const modalEl = document.getElementById('modalEliminarEvidencia');
      if (!modalEl) return;
      const modal   = new bootstrap.Modal(modalEl);
      const step1   = document.getElementById('ev-del-step1');
      const step2   = document.getElementById('ev-del-step2');
      const btn1    = document.getElementById('ev-del-btn1');
      const btn2    = document.getElementById('ev-del-btn2');
      let _evPk = null, _reportePk = null, _btnOrigen = null;

      function resetModal() {
        if (step1) { step1.classList.remove('d-none'); }
        if (step2) { step2.classList.add('d-none'); }
        if (btn1)  { btn1.classList.remove('d-none'); }
        if (btn2)  { btn2.classList.add('d-none'); btn2.disabled = false; btn2.innerHTML = 'Confirmar eliminación'; }
      }

      document.addEventListener('click', function (e) {
        const btn = e.target.closest('.btn-ev-delete');
        if (!btn) return;
        _evPk      = btn.dataset.evPk;
        _reportePk = btn.dataset.reportePk;
        _btnOrigen = btn;
        resetModal();
        modal.show();
      });

      if (btn1) btn1.addEventListener('click', function () {
        if (step1) step1.classList.add('d-none');
        if (step2) step2.classList.remove('d-none');
        if (btn1)  btn1.classList.add('d-none');
        if (btn2)  btn2.classList.remove('d-none');
      });

      if (btn2) btn2.addEventListener('click', async function () {
        btn2.disabled = true;
        btn2.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';
        try {
          const res = await fetch('/conducta/evidencia/' + _evPk + '/eliminar/', {
            method: 'POST',
            headers: { 'X-CSRFToken': window._PAGE.csrf, 'X-Requested-With': 'XMLHttpRequest' }
          });
          const data = await res.json();
          if (data.ok) {
            modal.hide();
            const wrap      = _btnOrigen.closest('.ev-thumb-wrap');
            const uploadBtn = document.querySelector('.btn-evidencia[data-id="' + _reportePk + '"]');
            if (wrap) wrap.remove();
            if (uploadBtn) {
              const numEl = parseInt(uploadBtn.dataset.numEvidencias || '0') - 1;
              uploadBtn.dataset.numEvidencias = numEl;
              uploadBtn.classList.remove('btn-danger', 'btn-success', 'btn-secondary', 'disabled');
              uploadBtn.classList.add(numEl > 0 ? 'btn-success' : 'btn-secondary');
              uploadBtn.title = 'Subir evidencia';
              uploadBtn.querySelector('i').className = numEl > 0 ? 'ti ti-photo' : 'ti ti-camera';
            }
          } else {
            alert('Error: ' + (data.error || 'No se pudo eliminar.'));
            resetModal();
          }
        } catch {
          alert('Error de red.');
          resetModal();
        }
      });

      modalEl.addEventListener('hidden.bs.modal', resetModal);
    })();
  } catch(e) { console.error('[ev-delete]', e); }

  /* ══════ CAMBIAR COORDINADOR (solo superuser) ══════ */
  try {
    if (window._PAGE && window._PAGE.isSuperuser) {
      (function () {
        const COLORES = { C1: '#c92a2a', C2: '#1971c2', C3: '#2f9e44', C4: '#e67700' };
        document.addEventListener('change', async function (e) {
          const sel = e.target.closest('.coord-badge-select');
          if (!sel) return;
          const pk    = sel.dataset.pk;
          const tipo  = sel.dataset.tipo;
          const coord = sel.value;
          sel.disabled = true;
          const bodyData = new URLSearchParams({ pk, tipo, coord });
          try {
            const res  = await fetch(window._PAGE.urlSetCoord, {
              method: 'POST',
              headers: { 'X-CSRFToken': window._PAGE.csrf, 'Content-Type': 'application/x-www-form-urlencoded' },
              body: bodyData
            });
            const data = await res.json();
            if (data.ok) {
              sel.style.background = COLORES[coord] || '#6c757d';
              sel.title = 'Override manual activo';
            } else {
              alert('Error: ' + (data.error || 'No se pudo guardar.'));
              location.reload();
            }
          } catch {
            alert('Error de red.');
            location.reload();
          } finally {
            sel.disabled = false;
          }
        });
      })();
    }
  } catch(e) { console.error('[coord-change]', e); }

  /* ══════ ELIMINAR REPORTE (doble confirmación) ══════ */
  try {
    (function () {
      let _pk = null, _tipo = null, _row = null;
      const modalEl   = document.getElementById('modalEliminarReporte');
      if (!modalEl) return;
      const modal     = new bootstrap.Modal(modalEl);
      const step1Body = document.getElementById('eliminar-step-1');
      const step2Body = document.getElementById('eliminar-step-2');
      const btn1      = document.getElementById('eliminar-btn-step1');
      const btn2      = document.getElementById('eliminar-btn-step2');
      const detalle   = document.getElementById('eliminar-detalle');
      const title     = document.getElementById('eliminar-modal-title');

      function resetModal() {
        if (step1Body) step1Body.classList.remove('d-none');
        if (step2Body) step2Body.classList.add('d-none');
        if (btn1) { btn1.classList.remove('d-none'); }
        if (btn2) { btn2.classList.add('d-none'); btn2.disabled = false;
                    btn2.innerHTML = '<i class="ti ti-trash me-1"></i>Sí, ELIMINAR'; }
        if (title) title.innerHTML = '<i class="ti ti-alert-triangle me-2 text-warning"></i>Eliminar reporte';
      }

      document.addEventListener('click', function (e) {
        const btn = e.target.closest('.btn-eliminar-reporte');
        if (!btn) return;
        _pk   = btn.dataset.pk;
        _tipo = btn.dataset.tipo;
        _row  = btn.closest('tr');
        const alumno  = btn.dataset.alumno  || '—';
        const materia = btn.dataset.materia || '—';
        const fecha   = btn.dataset.fecha   || '—';
        if (detalle) detalle.textContent = alumno + ' · ' + materia + ' · ' + fecha;
        resetModal();
        modal.show();
      });

      if (btn1) btn1.addEventListener('click', function () {
        if (step1Body) step1Body.classList.add('d-none');
        if (step2Body) step2Body.classList.remove('d-none');
        if (btn1) btn1.classList.add('d-none');
        if (btn2) btn2.classList.remove('d-none');
        if (title) title.innerHTML = '<i class="ti ti-skull me-2 text-danger"></i>Confirmación final';
      });

      if (btn2) btn2.addEventListener('click', async function () {
        btn2.disabled = true;
        btn2.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';
        const url = '/conducta/reporte-' + _tipo + '/' + _pk + '/eliminar/';
        try {
          const res = await fetch(url, {
            method: 'POST',
            headers: { 'X-CSRFToken': window._PAGE.csrf }
          });
          const data = await res.json();
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

      modalEl.addEventListener('hidden.bs.modal', resetModal);
    })();
  } catch(e) { console.error('[report-delete]', e); }

  /* ══════ DROPZONE + PASTE PARA EVIDENCIA ══════ */
  try {
    (function () {
      const dropzone    = document.getElementById('ev-dropzone');
      const fileInput   = document.getElementById('ev-imagen');
      const preview     = document.getElementById('ev-preview');
      const placeholder = document.getElementById('ev-dz-placeholder');
      const filename    = document.getElementById('ev-dz-filename');
      if (!dropzone || !fileInput) return;

      function showPreview(file) {
        if (!file || !file.type.startsWith('image/')) return;
        const reader = new FileReader();
        reader.onload = function (e) {
          if (preview)     { preview.src = e.target.result; preview.classList.remove('d-none'); }
          if (placeholder) placeholder.classList.add('d-none');
          if (filename)    { filename.textContent = file.name || 'Imagen pegada'; filename.classList.remove('d-none'); }
          dropzone.style.borderColor = '#4299e1';
          dropzone.style.background  = '#ebf8ff';
        };
        reader.readAsDataURL(file);
      }

      function setFile(file) {
        if (!file) return;
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
        showPreview(file);
      }

      dropzone.addEventListener('click', function () { fileInput.click(); });
      fileInput.addEventListener('change', function () { if (this.files[0]) showPreview(this.files[0]); });

      dropzone.addEventListener('dragover', function (e) {
        e.preventDefault();
        this.style.borderColor = '#4299e1';
        this.style.background  = '#ebf8ff';
      });
      dropzone.addEventListener('dragleave', function () {
        if (!fileInput.files[0]) {
          this.style.borderColor = '#adb5bd';
          this.style.background  = '#f8f9fa';
        }
      });
      dropzone.addEventListener('drop', function (e) {
        e.preventDefault();
        const file = e.dataTransfer.files[0];
        if (file) setFile(file);
      });

      document.addEventListener('paste', function (e) {
        const modal = document.getElementById('modalEvidencia');
        if (!modal || !modal.classList.contains('show')) return;
        const items = (e.clipboardData || (e.originalEvent && e.originalEvent.clipboardData))?.items;
        if (!items) return;
        for (const item of items) {
          if (item.type.startsWith('image/')) { setFile(item.getAsFile()); break; }
        }
      });

      var modalEvidEl = document.getElementById('modalEvidencia');
      if (modalEvidEl) {
        modalEvidEl.addEventListener('hidden.bs.modal', function () {
          if (preview)     { preview.src = '#'; preview.classList.add('d-none'); }
          if (placeholder) placeholder.classList.remove('d-none');
          if (filename)    { filename.classList.add('d-none'); filename.textContent = ''; }
          dropzone.style.borderColor = '#adb5bd';
          dropzone.style.background  = '#f8f9fa';
          fileInput.value = '';
        });
      }
    })();
  } catch(e) { console.error('[dropzone]', e); }

})();

// ── Filtro tabla Materia-Docente BL (solo superuser) ──────────────────────────
(function(){
  const filtro = document.getElementById('filtro-materias-bl');
  if (!filtro) return;
  filtro.addEventListener('input', function(){
    const q = this.value.toLowerCase();
    document.querySelectorAll('.fila-materia-bl').forEach(tr => {
      tr.style.display = !q || tr.dataset.search.includes(q) ? '' : 'none';
    });
  });
  const collapseEl = document.getElementById('collapse-materias-bl');
  const icon = document.getElementById('icon-materias-bl');
  if (collapseEl && icon) {
    collapseEl.addEventListener('show.bs.collapse', () => icon.className = 'ti ti-chevron-up');
    collapseEl.addEventListener('hide.bs.collapse', () => icon.className = 'ti ti-chevron-down');
  }
})();

// ── Checkboxes + Eliminación masiva de reportes ───────────────────────────────
// <--- hecho por claude code
(function(){
  const CSRF     = window._PAGE.csrf;
  const URL_BULK = window._PAGE.urlBulkDelete;
  if (!URL_BULK) return;

  const bulkBar  = document.getElementById('bulk-bar-reportes');
  const bulkCount = document.getElementById('bulk-count-reportes');
  if (!bulkBar) return;

  // ── Actualizar barra ──
  function actualizarBarra() {
    const checked = document.querySelectorAll('.chk-reporte:checked');
    const n = checked.length;
    bulkCount.textContent = n;
    bulkBar.style.display = n > 0 ? 'flex' : 'none';
  }

  // ── Seleccionar todos en un tab ──
  document.querySelectorAll('.chk-all-tab').forEach(chkAll => {
    chkAll.addEventListener('change', function() {
      const tab    = this.dataset.tab;
      const tabla  = document.getElementById('tabla-' + tab);
      if (!tabla) return;
      // DataTables: iterar sobre todas las filas (incluyendo páginas no visibles)
      if ($.fn.DataTable && $.fn.DataTable.isDataTable('#tabla-' + tab)) {
        const dt = $('#tabla-' + tab).DataTable();
        dt.rows().nodes().each(function(node) {
          const chk = node.querySelector('.chk-reporte');
          if (chk) chk.checked = this.checked;
        }.bind(this));
      } else {
        tabla.querySelectorAll('.chk-reporte').forEach(c => c.checked = this.checked);
      }
      actualizarBarra();
    });
  });

  // ── Click en checkbox individual ──
  document.addEventListener('change', function(e) {
    if (!e.target.classList.contains('chk-reporte')) return;
    actualizarBarra();
    // Sincronizar chk-all si aplica
    const tr    = e.target.closest('tr');
    const tabla = tr?.closest('table');
    if (!tabla) return;
    const tabId  = tabla.id?.replace('tabla-', '');
    const chkAll = document.querySelector(`.chk-all-tab[data-tab="${tabId}"]`);
    if (!chkAll) return;
    const total   = tabla.querySelectorAll('.chk-reporte').length;
    const marcados = tabla.querySelectorAll('.chk-reporte:checked').length;
    chkAll.indeterminate = marcados > 0 && marcados < total;
    chkAll.checked = marcados === total;
  });

  // ── Cancelar selección ──
  document.getElementById('btn-bulk-cancel-reportes').addEventListener('click', function() {
    document.querySelectorAll('.chk-reporte, .chk-all-tab').forEach(c => {
      c.checked = false;
      c.indeterminate = false;
    });
    actualizarBarra();
  });

  // ── Eliminar seleccionados ──
  document.getElementById('btn-bulk-delete-reportes').addEventListener('click', async function() {
    const checked = [...document.querySelectorAll('.chk-reporte:checked')];
    if (!checked.length) return;

    const nombres = checked.slice(0, 5).map(c => {
      const tr = c.closest('tr');
      const alumno = tr?.querySelectorAll('td')[2]?.textContent?.trim() || `#${c.dataset.pk}`;
      return `• ${alumno}`;
    });
    const extras = checked.length > 5 ? `\n• ...y ${checked.length - 5} más` : '';

    const conf = await Swal.fire({
      title: `¿Eliminar ${checked.length} reporte(s)?`,
      html: `<div class="text-start small text-muted">${nombres.join('<br>')}${extras}</div>`,
      icon: 'warning',
      showCancelButton:   true,
      confirmButtonText:  'Sí, eliminar todos',
      cancelButtonText:   'Cancelar',
      confirmButtonColor: '#d63939',
    });
    if (!conf.isConfirmed) return;

    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';

    const items = checked.map(c => ({ pk: parseInt(c.dataset.pk), tipo: c.dataset.tipo }));

    try {
      const res  = await fetch(URL_BULK, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body:    JSON.stringify({ items }),
      });
      const data = await res.json();

      if (data.ok) {
        // Eliminar filas del DOM
        checked.forEach(c => {
          const tr = c.closest('tr');
          // Si DataTables, usar API; si no, remove directo
          const tabla = tr?.closest('table');
          if (tabla && $.fn.DataTable && $.fn.DataTable.isDataTable(tabla)) {
            $(tabla).DataTable().row(tr).remove().draw(false);
          } else {
            tr?.remove();
          }
        });
        actualizarBarra();
        Swal.fire({
          icon: 'success', title: `${data.eliminados} reporte(s) eliminado(s)`,
          timer: 1800, showConfirmButton: false,
        });
      } else {
        Swal.fire('Error', data.error || 'No se pudo eliminar.', 'error');
      }
    } catch(e) {
      Swal.fire('Error', 'Error de conexión.', 'error');
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-trash me-1"></i>Eliminar seleccionados';
  });

})();
