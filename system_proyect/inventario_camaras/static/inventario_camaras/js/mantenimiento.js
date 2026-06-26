// Mantenimiento de cámaras: ficha por grupo, fotos, firma del responsable, edición y link de firma del técnico.
const CAM_GRUPO = window._IC.camarasPorGrupo;

$(function () {
  try {
    $('#tablaMant').DataTable({
      pageLength: 15, order: [[4, 'desc']],
      language: {
        lengthMenu: "Mostrar _MENU_", zeroRecords: "Sin resultados",
        info: "Mostrando _START_ a _END_ de _TOTAL_", infoEmpty: "Sin registros",
        infoFiltered: "(de _MAX_)", search: "Buscar:",
        paginate: { first: "«", last: "»", next: "›", previous: "‹" }
      }
    });
  } catch (e) { console.warn(e); }

  const modalEl = document.getElementById('modalMant');
  const modal   = bootstrap.Modal.getOrCreateInstance(modalEl);
  const form    = document.getElementById('formMant');
  const createUrl = window.location.pathname;

  // ── Mostrar cámaras del grupo seleccionado ──
  function renderCamarasGrupo(grupo) {
    const cams = CAM_GRUPO[grupo] || [];
    $('#cam-count').text(cams.length);
    const cont = $('#camaras-lista');
    if (!grupo) {
      cont.html('<div class="text-muted small text-center py-2">Selecciona un grupo para ver sus cámaras.</div>');
      return;
    }
    if (!cams.length) {
      cont.html('<div class="text-muted small text-center py-2">El grupo no tiene cámaras.</div>');
      return;
    }
    let html = '<table class="table table-sm table-vcenter mb-0"><thead><tr>' +
      '<th>ID</th><th>Modelo</th><th>Serie</th><th>Ubicación</th><th>Estado</th></tr></thead><tbody>';
    cams.forEach(c => {
      html += `<tr><td><span class="badge bg-green-lt text-green">${c.camara_id}</span></td>` +
        `<td>${c.modelo || '—'}</td><td class="small font-monospace">${c.serie || '—'}</td>` +
        `<td>${c.ubicacion || '—'}</td><td>${c.estado || '—'}</td></tr>`;
    });
    html += '</tbody></table>';
    cont.html(html);
  }
  $('#id_grupo').on('change', function () { renderCamarasGrupo(this.value); });

  // ── Drop zone fotos ──
  const dropZone = document.getElementById('drop-zone');
  const fotosInput = document.getElementById('fotos-input');
  const preview = document.getElementById('fotos-preview');
  let selectedFiles = [];

  dropZone.addEventListener('click', () => fotosInput.click());
  dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('bg-azure-lt'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('bg-azure-lt'));
  dropZone.addEventListener('drop', e => { e.preventDefault(); dropZone.classList.remove('bg-azure-lt'); addFiles(e.dataTransfer.files); });
  fotosInput.addEventListener('change', () => addFiles(fotosInput.files));

  function addFiles(files) {
    for (const f of files) {
      if (selectedFiles.length >= 5) break;
      if (!f.type.startsWith('image/')) continue;
      selectedFiles.push(f);
    }
    renderPreviews();
    const dt = new DataTransfer();
    selectedFiles.forEach(f => dt.items.add(f));
    fotosInput.files = dt.files;
  }
  function renderPreviews() {
    preview.innerHTML = '';
    selectedFiles.forEach((f, i) => {
      const url = URL.createObjectURL(f);
      const w = document.createElement('div');
      w.style.position = 'relative';
      w.innerHTML = `<img src="${url}" style="width:70px;height:70px;object-fit:cover;border-radius:6px;">
        <button type="button" class="btn btn-sm btn-ghost-danger" onclick="icRemoveFile(${i})"
          style="position:absolute;top:-6px;right:-6px;padding:0 5px;">✕</button>`;
      preview.appendChild(w);
    });
  }
  window.icRemoveFile = i => { selectedFiles.splice(i, 1); renderPreviews(); };
  function clearFotos() { selectedFiles = []; preview.innerHTML = ''; fotosInput.value = ''; }

  // ── Signature pad ──
  const canvas = document.getElementById('signature-canvas');
  const ctx = canvas.getContext('2d');
  let drawing = false, lastX = 0, lastY = 0, hasDrawn = false;
  function resizeCanvas() { const r = canvas.getBoundingClientRect(); canvas.width = r.width; canvas.height = r.height; }
  function getPos(e) { const r = canvas.getBoundingClientRect(); const s = e.touches ? e.touches[0] : e; return [s.clientX - r.left, s.clientY - r.top]; }
  function draw(e) {
    if (!drawing) return; e.preventDefault && e.preventDefault();
    ctx.beginPath(); ctx.moveTo(lastX, lastY);
    [lastX, lastY] = getPos(e); ctx.lineTo(lastX, lastY);
    ctx.strokeStyle = '#1a1a2e'; ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.stroke(); hasDrawn = true;
  }
  canvas.addEventListener('mousedown', e => { drawing = true;[lastX, lastY] = getPos(e); });
  canvas.addEventListener('mousemove', draw);
  canvas.addEventListener('mouseup', () => drawing = false);
  canvas.addEventListener('mouseleave', () => drawing = false);
  canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing = true;[lastX, lastY] = getPos(e); }, { passive: false });
  canvas.addEventListener('touchmove', draw, { passive: false });
  canvas.addEventListener('touchend', () => drawing = false);
  document.getElementById('btn-clear-firma').addEventListener('click', () => { ctx.clearRect(0, 0, canvas.width, canvas.height); hasDrawn = false; });

  function resetFirma() { ctx.clearRect(0, 0, canvas.width, canvas.height); hasDrawn = false; }

  // Capturar firma al enviar
  $(form).on('submit', function () {
    document.getElementById('firma_responsable_data').value = hasDrawn ? canvas.toDataURL('image/png') : '';
  });

  // ── Nuevo ──
  $('#btnNuevo').on('click', function () {
    form.reset(); form.action = createUrl; clearFotos(); resetFirma();
    renderCamarasGrupo('');
    $('#mantTitle').html('<i class="ti ti-tool me-2 text-primary"></i>Nuevo Registro');
    modal.show();
    setTimeout(resizeCanvas, 200);
  });

  // ── Editar ──
  $(document).on('click', '.btn-edit-mant', function () {
    const pk = $(this).data('pk');
    $.getJSON(window._IC.editBase + pk + '/editar/', function (d) {
      form.reset(); clearFotos(); resetFirma();
      form.action = window._IC.editBase + pk + '/editar/';
      $('#id_grupo').val(d.grupo || '');
      renderCamarasGrupo(d.grupo || '');
      $('#id_tipo_falla').val(d.tipo_falla || '');
      $('#id_date').val(d.date);
      $('#id_status').val(d.status);
      $('#id_solucion').val(d.solucion);
      $('#id_observaciones').val(d.observaciones);
      $('#id_responsable_nombre').val(d.responsable_nombre);
      $('#mantTitle').html('<i class="ti ti-pencil me-2 text-primary"></i>Editar ' + d.record_id);
      modal.show();
      setTimeout(resizeCanvas, 200);
    }).fail(() => Swal.fire('Error', 'No se pudo cargar el registro.', 'error'));
  });

  // ── Eliminar ──
  $(document).on('click', '.btn-del-mant', function () {
    const pk = $(this).data('pk'), rid = $(this).data('rid');
    Swal.fire({
      title: '¿Eliminar ' + rid + '?', icon: 'warning', showCancelButton: true,
      confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar', confirmButtonColor: '#d63939',
    }).then(r => {
      if (r.isConfirmed) {
        const f = $('<form method="post">').attr('action', window._IC.editBase + pk + '/eliminar/');
        f.append($('<input type="hidden" name="csrfmiddlewaretoken">').val(window._IC.csrf));
        $('body').append(f); f.submit();
      }
    });
  });

  // ── Link de firma del técnico (WhatsApp / Copiar) ──
  $(document).on('click', '.btn-firma-link', function () {
    const link = $(this).data('link');
    const rid  = $(this).data('rid');
    const markUrl = $(this).data('mark');
    const msg = `Hola, por favor firma el mantenimiento ${rid} de la cámara en este enlace: ${link}`;
    const wa  = 'https://wa.me/?text=' + encodeURIComponent(msg);

    Swal.fire({
      title: 'Enviar link de firma',
      html: `<p class="text-muted small mb-2">Comparte este enlace con el técnico para que firme:</p>
             <input id="ic-link" class="form-control form-control-sm mb-2" value="${link}" readonly onclick="this.select()">`,
      showCancelButton: true,
      confirmButtonText: '<i class="ti ti-brand-whatsapp"></i> WhatsApp',
      confirmButtonColor: '#25D366',
      cancelButtonText: '<i class="ti ti-copy"></i> Copiar link',
      cancelButtonColor: '#206bc4',
    }).then(res => {
      // Marcar como solicitada (sin bloquear)
      $.post(markUrl, { csrfmiddlewaretoken: window._IC.csrf });
      if (res.isConfirmed) {
        window.open(wa, '_blank');
      } else if (res.dismiss === Swal.DismissReason.cancel) {
        navigator.clipboard.writeText(link).then(
          () => Swal.fire({ icon: 'success', title: 'Link copiado', timer: 1200, showConfirmButton: false }),
          () => { document.getElementById('ic-link'); }
        );
      }
    });
  });
});
