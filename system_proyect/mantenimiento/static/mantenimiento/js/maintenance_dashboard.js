// Datos de computadoras para auto-fill (inyectados desde el bridge window._PAGE)
const COMP_DATA = window._PAGE.computadorasJson;

$(function () {

  // DataTable (envuelto en try-catch para que un error no detenga el resto del JS)
  try {
    $.fn.dataTable.ext.errMode = 'none';
    $('#tablaMantenimiento').DataTable({
      pageLength: 15, order: [[7, 'desc']],
      language: {
        lengthMenu:"Mostrar _MENU_ registros", zeroRecords:"Sin registros",
        info:"Mostrando _START_ a _END_ de _TOTAL_", infoEmpty:"Sin registros",
        infoFiltered:"(de _MAX_ totales)", search:"Buscar:",
        paginate:{first:"«",last:"»",next:"›",previous:"‹"}
      }
    });
  } catch(e) { console.warn('DataTable init:', e); }

  // ── Tipo de Falla: opción "Agregar nueva" → muestra un campo de texto inline ──
  // Pares de [select, input de nueva falla]
  const TF_PAIRS = [['#id_tipo_falla', '#id_tipo_falla_nueva'], ['#edit-tipo-falla', '#edit-tipo-falla-nueva']];
  TF_PAIRS.forEach(function (p) {
    const $s = $(p[0]);
    if ($s.length && !$s.find('option[value="__nueva__"]').length) {
      $s.append('<option value="__nueva__">➕ Agregar nueva falla…</option>');
    }
    $(document).on('change', p[0], function () {
      const $inp = $(p[1]);
      const nueva = this.value === '__nueva__';
      $inp.toggleClass('d-none', !nueva);
      if (nueva) { $inp.focus(); } else { $inp.val(''); }
    });
  });

  // Al abrir el modal disparar fill si ya hay valor
  $('#modalNuevoRegistro').on('shown.bs.modal', function(){
    const _val = $('#id_computadora').val();
    if (_val) fillFromComputadora(_val);
  });

  // Auto-fill al seleccionar computadora
  function fillFromComputadora(val) {
    const data = COMP_DATA[val] || {};
    $('#id_model').val(data.modelo || '');
    $('#mant-asignado').val(data.asignado || '');
    $('#mant-area').val(data.area || '');
    $('#mant-grado').val(data.grado || '');
    $('#hidden_teacher_name').val(data.asignado || '');
    $('#hidden_grade').val(data.grado || '');
  }

  $('#id_computadora').on('change', function(){
    fillFromComputadora(this.value);
    const data = COMP_DATA[this.value] || {};
    const serieInput = $('#id_serie');
    const chk = $('#chk-serie-mant');
    if (!chk.is(':checked')) {
      serieInput.val(data.serie || '').addClass('bg-light text-muted').prop('readonly', true);
    }
  });

  // Toggle serie manual
  $('#chk-serie-mant').on('change', function(){
    const inp = $('#id_serie');
    if ($(this).is(':checked')) {
      inp.removeClass('bg-light text-muted').prop('readonly', false).focus();
    } else {
      const compId = $('#id_computadora').val();
      const serie = compId && COMP_DATA[compId] ? COMP_DATA[compId].serie : '';
      inp.addClass('bg-light text-muted').prop('readonly', true).val(serie);
    }
  });

  // ── Drop zone fotos ──
  const dropZone   = document.getElementById('drop-zone');
  const fotosInput = document.getElementById('fotos-input');
  const preview    = document.getElementById('fotos-preview');
  let   selectedFiles = [];

  dropZone.addEventListener('click',     () => fotosInput.click());
  dropZone.addEventListener('dragover',  e  => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    addFiles(e.dataTransfer.files);
  });
  fotosInput.addEventListener('change', () => addFiles(fotosInput.files));

  function addFiles(files) {
    for (const f of files) {
      if (selectedFiles.length >= 5) break;
      if (!f.type.startsWith('image/')) continue;
      selectedFiles.push(f);
    }
    renderPreviews();
    // Reconstruir el FileList en el input via DataTransfer
    const dt = new DataTransfer();
    selectedFiles.forEach(f => dt.items.add(f));
    fotosInput.files = dt.files;
  }

  function renderPreviews() {
    preview.innerHTML = '';
    selectedFiles.forEach((f, i) => {
      const url = URL.createObjectURL(f);
      const wrap = document.createElement('div');
      wrap.style.position = 'relative';
      wrap.innerHTML = `<img src="${url}" title="${f.name}">
        <button type="button" class="btn btn-sm btn-ghost-danger" onclick="removeFile(${i})"
          style="position:absolute;top:-4px;right:-4px;padding:0 4px;font-size:.7rem;">✕</button>`;
      preview.appendChild(wrap);
    });
  }
  window.removeFile = i => { selectedFiles.splice(i,1); renderPreviews(); };

  // ── Signature pads (reutilizable: técnico + maestro) ──
  function initPad(canvasId, clearBtnId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return { data: () => '' };
    const ctx = canvas.getContext('2d');
    let drawing = false, hasDrawn = false, lastX = 0, lastY = 0;

    function resizeCanvas() {
      const rect = canvas.getBoundingClientRect();
      canvas.width  = rect.width;
      canvas.height = rect.height;
    }
    resizeCanvas();
    new ResizeObserver(resizeCanvas).observe(canvas);

    function getPos(e) {
      const r = canvas.getBoundingClientRect();
      const src = e.touches ? e.touches[0] : e;
      return [src.clientX - r.left, src.clientY - r.top];
    }
    function start(e) { drawing = true; [lastX, lastY] = getPos(e); }
    function move(e) {
      if (!drawing) return;
      hasDrawn = true;
      ctx.beginPath(); ctx.moveTo(lastX, lastY);
      [lastX, lastY] = getPos(e); ctx.lineTo(lastX, lastY);
      ctx.strokeStyle = '#1a1a2e'; ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.stroke();
    }
    canvas.addEventListener('mousedown', start);
    canvas.addEventListener('mousemove', move);
    canvas.addEventListener('mouseup',   () => drawing = false);
    canvas.addEventListener('mouseleave',() => drawing = false);
    canvas.addEventListener('touchstart', e => { e.preventDefault(); start(e); }, {passive:false});
    canvas.addEventListener('touchmove',  e => { e.preventDefault(); move(e);  }, {passive:false});
    canvas.addEventListener('touchend',  () => drawing = false);

    function clear() { ctx.clearRect(0, 0, canvas.width, canvas.height); hasDrawn = false; }
    const clearBtn = document.getElementById(clearBtnId);
    if (clearBtn) clearBtn.addEventListener('click', clear);
    return { data: () => hasDrawn ? canvas.toDataURL('image/png') : '', clear };
  }

  const padMaestro = initPad('signature-canvas',          'btn-clear-firma');
  const padTecnico = initPad('signature-canvas-tec',      'btn-clear-firma-tec');
  const padEditTec = initPad('edit-signature-canvas-tec', 'edit-btn-clear-firma-tec');
  const padEditMae = initPad('edit-signature-canvas-mae', 'edit-btn-clear-firma-mae');

  // Al guardar la edición → capturar firmas (vacío = no cambia)
  $('#form-edit-mant').on('submit', function(){
    document.getElementById('edit-firma-tecnico-data').value = padEditTec.data();
    document.getElementById('edit-firma-data').value         = padEditMae.data();
  });

  // Antes de enviar el form → capturar ambas firmas (vacío si no se dibujó)
  $('#modalNuevoRegistro form').on('submit', function(){
    document.getElementById('firma_data').value         = padMaestro.data();
    document.getElementById('firma_tecnico_data').value = padTecnico.data();
  });

  // ── Enviar link de firma al maestro (WhatsApp / Copiar) ──
  $(document).on('click', '.btn-firma-link', function () {
    const link = $(this).data('link');
    const rid  = $(this).data('rid');
    const markUrl = $(this).data('mark');
    const msg = `Hola, por favor firme el mantenimiento ${rid} de su equipo en este enlace: ${link}`;
    const wa  = 'https://wa.me/?text=' + encodeURIComponent(msg);
    Swal.fire({
      title: 'Enviar firma al maestro',
      html: `<p class="text-muted small mb-2">Comparte este enlace para que el maestro firme:</p>
             <input id="mant-link" class="form-control form-control-sm mb-3" value="${link}" readonly onclick="this.select()">
             <div class="d-flex gap-2 justify-content-center">
               <a href="${wa}" target="_blank" rel="noopener" id="mant-wa" class="btn" style="background:#25D366;color:#fff">
                 <i class="ti ti-brand-whatsapp me-1"></i>WhatsApp</a>
               <button type="button" id="mant-copy" class="btn btn-primary">
                 <i class="ti ti-copy me-1"></i>Copiar link</button>
             </div>`,
      showConfirmButton: false,
      showCancelButton: true,
      cancelButtonText: 'Cerrar',
      didOpen: () => {
        const mark = () => $.post(markUrl, { csrfmiddlewaretoken: window._PAGE.csrf });
        // WhatsApp: es un <a target="_blank"> → clic directo (funciona en PC y celular).
        // No cerramos el diálogo de inmediato: en móvil eso cancelaba la apertura de WhatsApp.
        document.getElementById('mant-wa').addEventListener('click', () => {
          mark();
          setTimeout(() => { try { Swal.close(); } catch (e) {} }, 800);
        });
        document.getElementById('mant-copy').addEventListener('click', () => {
          navigator.clipboard.writeText(link).then(() => {
            mark();
            Swal.fire({ icon: 'success', title: 'Link copiado', timer: 1200, showConfirmButton: false });
          }, () => {});
        });
      },
    });
  });

  // ── Editar registro ──
  $(document).on('click', '.btn-editar-mant', function(){
    const pk = $(this).data('pk');
    $.getJSON(`/mantenimiento/${pk}/editar/`, function(d){
      $('#edit-record-id-badge').text(d.record_id);
      $('#form-edit-mant').attr('action', `/mantenimiento/${pk}/editar/`);
      $('#edit-computadora').val(d.computadora);
      const comp = COMP_DATA[String(d.computadora)] || {};
      $('#edit-model').val(d.model || comp.modelo || '');
      $('#edit-serie').val(d.serie || comp.serie || '');
      $('#edit-asignado-display').val(d.teacher_name || comp.asignado || '');
      $('#edit-area-display').val(comp.area || '');
      $('#edit-grado-display').val(d.grade || comp.grado || '');
      $('#edit-teacher-name').val(d.teacher_name || comp.asignado || '');
      $('#edit-grade').val(d.grade || comp.grado || '');
      $('#edit-tipo-falla').val(String(d.tipo_falla));
      $('#edit-date').val(d.date);
      $('#edit-status').val(d.status);
      $('#edit-solucion').val(d.solucion);
      $('#edit-observaciones').val(d.observaciones);
      // Firma del técnico: mostrar la actual (si existe) y limpiar el lienzo
      padEditTec.clear();
      if (d.firma_tecnico) {
        $('#edit-firma-tec-img').attr('src', d.firma_tecnico);
        $('#edit-firma-tec-actual').show();
      } else {
        $('#edit-firma-tec-actual').hide();
      }
      // Firma del maestro: mostrar la actual (si existe) y limpiar el lienzo
      padEditMae.clear();
      if (d.firma) {
        $('#edit-firma-mae-img').attr('src', d.firma);
        $('#edit-firma-mae-actual').show();
      } else {
        $('#edit-firma-mae-actual').hide();
      }
      $('#modalEditarRegistro').modal('show');
    }).fail(() => Swal.fire('Error', 'No se pudo cargar el registro.', 'error'));
  });

  // Auto-fill al cambiar computadora en modal editar
  $('#edit-computadora').on('change', function(){
    const comp = COMP_DATA[this.value] || {};
    $('#edit-model').val(comp.modelo || '');
    $('#edit-serie').val(comp.serie || '');
    $('#edit-asignado-display').val(comp.asignado || '');
    $('#edit-area-display').val(comp.area || '');
    $('#edit-grado-display').val(comp.grado || '');
    $('#edit-teacher-name').val(comp.asignado || '');
    $('#edit-grade').val(comp.grado || '');
  });

  // ── Eliminar registro ──
  $(document).on('click', '.btn-eliminar-mant', function(){
    const pk  = $(this).data('pk');
    const rid = $(this).data('rid');
    Swal.fire({
      title: '¿Eliminar ' + rid + '?',
      text: 'Se eliminará el registro y la numeración se reiniciará desde 001.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d63939',
    }).then(res => {
      if (res.isConfirmed) {
        const f = $('<form method="post">').attr('action', `/mantenimiento/${pk}/eliminar/`);
        f.append($('<input type="hidden" name="csrfmiddlewaretoken">').val(window._PAGE.csrf));
        $('body').append(f);
        f.submit();
      }
    });
  });

});
