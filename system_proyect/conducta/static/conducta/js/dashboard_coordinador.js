// dashboard_coordinador.js
// Requires window._PAGE to be defined inline by the template.

(function () {
  'use strict';

  /* ══════ REENVIAR REPORTES (solo superuser) ══════ */
  if (window._PAGE && window._PAGE.isSuperuser) {
    document.getElementById('btnConfirmarReenvio')?.addEventListener('click', async function () {
      const fecha = document.getElementById('inputFechaReenvio').value;
      if (!fecha) { alert('Selecciona una fecha.'); return; }
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';
      const body = new URLSearchParams({ fecha });
      const res = await fetch(window._PAGE.urlReenviar, {
        method: 'POST',
        headers: { 'X-CSRFToken': window._PAGE.csrf, 'Content-Type': 'application/x-www-form-urlencoded' },
        body
      });
      const data = await res.json();
      this.disabled = false;
      this.innerHTML = '<i class="ti ti-send me-1"></i>Enviar';
      const msgEl = document.getElementById('reenvioMsg');
      msgEl.className = `alert mt-2 alert-${data.ok ? 'success' : 'danger'}`;
      msgEl.textContent = data.ok ? `Enviados: ${data.enviados} notificaciones` : `Error: ${data.error}`;
      msgEl.classList.remove('d-none');
    });
  }

  /* ══════ LIGHTBOX EVIDENCIA ══════ */
  document.querySelectorAll('.img-evidencia-click').forEach(function (img) {
    img.addEventListener('click', function () {
      document.getElementById('lightboxImg').src = this.src;
      document.getElementById('lightboxTitulo').textContent = this.title || 'Evidencia';
      new bootstrap.Modal(document.getElementById('modalLightbox')).show();
    });
  });

  /* ══════ ELIMINAR EVIDENCIA (doble confirmación) ══════ */
  (function () {
    const modalEl = document.getElementById('modalEliminarEvidencia');
    const modal   = new bootstrap.Modal(modalEl);
    const step1   = document.getElementById('ev-del-step1');
    const step2   = document.getElementById('ev-del-step2');
    const btn1    = document.getElementById('ev-del-btn1');
    const btn2    = document.getElementById('ev-del-btn2');
    let _evPk = null, _reportePk = null, _btnOrigen = null;

    function resetModal() {
      step1.classList.remove('d-none');
      step2.classList.add('d-none');
      btn1.classList.remove('d-none');
      btn2.classList.add('d-none');
      btn2.disabled = false;
      btn2.innerHTML = 'Confirmar eliminación';
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

    btn1.addEventListener('click', function () {
      step1.classList.add('d-none');
      step2.classList.remove('d-none');
      btn1.classList.add('d-none');
      btn2.classList.remove('d-none');
    });

    btn2.addEventListener('click', async function () {
      btn2.disabled = true;
      btn2.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';
      try {
        const res = await fetch(`/conducta/evidencia/${_evPk}/eliminar/`, {
          method: 'POST',
          headers: { 'X-CSRFToken': window._PAGE.csrf, 'X-Requested-With': 'XMLHttpRequest' }
        });
        const data = await res.json();
        if (data.ok) {
          modal.hide();
          const wrap      = _btnOrigen.closest('.ev-thumb-wrap');
          const uploadBtn = document.querySelector(`.btn-evidencia[data-id="${_reportePk}"]`);
          wrap.remove();
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

  /* ══════ CAMBIAR COORDINADOR (solo superuser) ══════ */
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
        const body = new URLSearchParams({ pk, tipo, coord });
        try {
          const res  = await fetch(window._PAGE.urlSetCoord, {
            method: 'POST',
            headers: { 'X-CSRFToken': window._PAGE.csrf, 'Content-Type': 'application/x-www-form-urlencoded' },
            body
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

  /* ══════ ELIMINAR REPORTE (doble confirmación) ══════ */
  (function () {
    let _pk = null, _tipo = null, _row = null;
    const modal      = new bootstrap.Modal(document.getElementById('modalEliminarReporte'));
    const step1Body  = document.getElementById('eliminar-step-1');
    const step2Body  = document.getElementById('eliminar-step-2');
    const btn1       = document.getElementById('eliminar-btn-step1');
    const btn2       = document.getElementById('eliminar-btn-step2');
    const detalle    = document.getElementById('eliminar-detalle');
    const title      = document.getElementById('eliminar-modal-title');

    function resetModal() {
      step1Body.classList.remove('d-none');
      step2Body.classList.add('d-none');
      btn1.classList.remove('d-none');
      btn2.classList.add('d-none');
      btn2.disabled = false;
      btn2.innerHTML = '<i class="ti ti-trash me-1"></i>Sí, ELIMINAR';
      title.innerHTML = '<i class="ti ti-alert-triangle me-2 text-warning"></i>Eliminar reporte';
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
      detalle.textContent = alumno + ' · ' + materia + ' · ' + fecha;
      resetModal();
      modal.show();
    });

    btn1.addEventListener('click', function () {
      step1Body.classList.add('d-none');
      step2Body.classList.remove('d-none');
      btn1.classList.add('d-none');
      btn2.classList.remove('d-none');
      title.innerHTML = '<i class="ti ti-skull me-2 text-danger"></i>Confirmación final';
    });

    btn2.addEventListener('click', async function () {
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

    document.getElementById('modalEliminarReporte').addEventListener('hidden.bs.modal', resetModal);
  })();

  /* ══════ MODAL EDICIÓN INLINE ══════ */
  (function () {
    const modalEl  = document.getElementById('modalEditarReporte');
    if (!modalEl) return;
    const modal    = new bootstrap.Modal(modalEl);
    const loading  = document.getElementById('me-loading');
    const body     = document.getElementById('me-body');
    const btnGuardar = document.getElementById('me-btn-guardar');

    // URL bases para edición completa
    const URL_BASE = {
      conductual: '/conducta/reporte-conductual/',
      informativo: '/conducta/reporte-informativo/',
      progress: '/conducta/progress-report/',
    };

    function poblarFirma(area) {
      const sel = document.getElementById('me-firma');
      sel.innerHTML = '<option value="">— Sin firma —</option>';
      const lista = area === 'bilingue'
        ? (window._PAGE.coordsBL  || [])
        : (window._PAGE.coordsCOL || []);
      lista.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        sel.appendChild(opt);
      });
    }

    document.addEventListener('click', async function (e) {
      const btn = e.target.closest('.btn-editar-inline');
      if (!btn) return;

      const pk   = btn.dataset.pk;
      const tipo = btn.dataset.tipo;
      const area = btn.dataset.area || 'bilingue';

      // Reset modal
      loading.classList.remove('d-none');
      body.classList.add('d-none');
      document.getElementById('me-title').innerHTML =
        '<i class="ti ti-pencil me-2 text-primary"></i>Editar Reporte';
      modal.show();

      try {
        const res  = await fetch(`${window._PAGE.urlEditarAjax}?pk=${pk}&tipo=${tipo}`);
        const data = await res.json();
        if (!data.ok) { alert('Error al cargar el reporte.'); modal.hide(); return; }

        // Campos de solo lectura
        document.getElementById('me-pk').value   = data.pk;
        document.getElementById('me-tipo').value = data.tipo;
        document.getElementById('me-alumno').textContent = data.alumno;
        document.getElementById('me-grado').textContent  = data.grado;
        document.getElementById('me-fecha').textContent  = data.fecha;

        // Docente / Materia
        const rowDocente  = document.getElementById('me-row-docente');
        const rowMateria  = document.getElementById('me-row-materia');
        if (tipo !== 'progress') {
          document.getElementById('me-docente').textContent = data.docente || '—';
          document.getElementById('me-materia').textContent = data.materia || '—';
          rowDocente.classList.remove('d-none');
          rowMateria.classList.remove('d-none');
        } else {
          rowDocente.classList.add('d-none');
          rowMateria.classList.add('d-none');
        }

        // Tipo reporte (solo informativo)
        const rowTipo = document.getElementById('me-row-tipo-reporte');
        if (tipo === 'informativo') {
          rowTipo.classList.remove('d-none');
          document.getElementById('me-tipo-reporte').value = data.tipo_reporte || 'academico';
        } else {
          rowTipo.classList.add('d-none');
        }

        // Estado
        document.getElementById('me-estado').value = data.estado || 'enviado';

        // Firma (poblar según área)
        poblarFirma(data.area || area);
        document.getElementById('me-firma').value = data.coordinador_firma || '';

        // Comentario docente (no progress)
        const rowComentario = document.getElementById('me-row-comentario');
        if (tipo !== 'progress') {
          rowComentario.classList.remove('d-none');
          document.getElementById('me-comentario').value = data.comentario || '';
        } else {
          rowComentario.classList.add('d-none');
        }

        // Comentario coordinador
        document.getElementById('me-comentario-coord').value = data.comentario_coordinador || '';

        // Aviso incisos conductual
        const avisoIncisos = document.getElementById('me-aviso-incisos');
        if (tipo === 'conductual') {
          avisoIncisos.classList.remove('d-none');
        } else {
          avisoIncisos.classList.add('d-none');
        }

        // Link edición completa
        const linkCompleto = document.getElementById('me-link-completo');
        linkCompleto.href = (URL_BASE[tipo] || '/conducta/') + pk + '/editar/';

        // Título del modal
        const labels = { conductual: 'Conductual', informativo: 'Informativo', progress: 'Progress' };
        document.getElementById('me-title').innerHTML =
          `<i class="ti ti-pencil me-2 text-primary"></i>Editar ${labels[tipo] || ''} #${pk}`;

        loading.classList.add('d-none');
        body.classList.remove('d-none');
      } catch (err) {
        console.error(err);
        alert('Error de red al cargar el reporte.');
        modal.hide();
      }
    });

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
          modal.hide();
          // Actualizar badge de estado en la fila sin recargar
          const pk   = document.getElementById('me-pk').value;
          const tipo = document.getElementById('me-tipo').value;
          const row  = document.querySelector(
            `.btn-editar-inline[data-pk="${pk}"][data-tipo="${tipo}"]`
          )?.closest('tr');
          if (row) {
            const estadoVal = document.getElementById('me-estado').value;
            const badgesMap = {
              enviado:   ['bg-secondary-lt', 'text-secondary', 'Enviado'],
              revisando: ['bg-warning-lt',   'text-warning',   'Revisando'],
              revisado:  ['bg-blue-lt',      'text-blue',      'Revisado'],
              aprobado:  ['bg-success-lt',   'text-success',   'Aprobado'],
            };
            const [bg, txt, label] = badgesMap[estadoVal] || badgesMap.enviado;
            const badgeEl = row.querySelector('.badge[class*="bg-secondary-lt"], .badge[class*="bg-warning-lt"], .badge[class*="bg-blue-lt"], .badge[class*="bg-success-lt"]');
            if (badgeEl && !badgeEl.classList.contains('bg-red-lt') && !badgeEl.classList.contains('bg-orange-lt') && !badgeEl.classList.contains('bg-blue-lt') && !badgeEl.classList.contains('bg-teal-lt')) {
              badgeEl.className = `badge ${bg} ${txt}`;
              badgeEl.textContent = label;
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

    // Reset al cerrar
    modalEl.addEventListener('hidden.bs.modal', function () {
      loading.classList.remove('d-none');
      body.classList.add('d-none');
    });
  })();

  /* ══════ DROPZONE + PASTE PARA EVIDENCIA ══════ */
  (function () {
    const dropzone    = document.getElementById('ev-dropzone');
    const fileInput   = document.getElementById('ev-imagen');
    const preview     = document.getElementById('ev-preview');
    const placeholder = document.getElementById('ev-dz-placeholder');
    const filename    = document.getElementById('ev-dz-filename');

    function showPreview(file) {
      if (!file || !file.type.startsWith('image/')) return;
      const reader = new FileReader();
      reader.onload = function (e) {
        preview.src = e.target.result;
        preview.classList.remove('d-none');
        placeholder.classList.add('d-none');
        filename.textContent = file.name || 'Imagen pegada';
        filename.classList.remove('d-none');
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

    fileInput.addEventListener('change', function () {
      if (this.files[0]) showPreview(this.files[0]);
    });

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
      if (!modal.classList.contains('show')) return;
      const items = (e.clipboardData || e.originalEvent?.clipboardData)?.items;
      if (!items) return;
      for (const item of items) {
        if (item.type.startsWith('image/')) {
          const file = item.getAsFile();
          if (file) setFile(file);
          break;
        }
      }
    });

    document.getElementById('modalEvidencia').addEventListener('hidden.bs.modal', function () {
      preview.src = '#';
      preview.classList.add('d-none');
      placeholder.classList.remove('d-none');
      filename.classList.add('d-none');
      filename.textContent = '';
      dropzone.style.borderColor = '#adb5bd';
      dropzone.style.background  = '#f8f9fa';
      fileInput.value = '';
    });
  })();
})();
