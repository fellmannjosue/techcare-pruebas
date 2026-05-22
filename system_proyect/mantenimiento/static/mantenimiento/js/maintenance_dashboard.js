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

  // ── Signature pad ──
  const canvas = document.getElementById('signature-canvas');
  const ctx    = canvas.getContext('2d');
  let drawing  = false, lastX = 0, lastY = 0;

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

  canvas.addEventListener('mousedown',  e => { drawing=true; [lastX,lastY]=getPos(e); });
  canvas.addEventListener('mousemove',  e => {
    if (!drawing) return;
    ctx.beginPath(); ctx.moveTo(lastX, lastY);
    [lastX,lastY]=getPos(e); ctx.lineTo(lastX, lastY);
    ctx.strokeStyle='#1a1a2e'; ctx.lineWidth=2; ctx.lineCap='round'; ctx.stroke();
  });
  canvas.addEventListener('mouseup',   () => drawing=false);
  canvas.addEventListener('mouseleave',() => drawing=false);
  canvas.addEventListener('touchstart', e => { e.preventDefault(); drawing=true; [lastX,lastY]=getPos(e); }, {passive:false});
  canvas.addEventListener('touchmove',  e => {
    if (!drawing) return; e.preventDefault();
    ctx.beginPath(); ctx.moveTo(lastX, lastY);
    [lastX,lastY]=getPos(e); ctx.lineTo(lastX, lastY);
    ctx.strokeStyle='#1a1a2e'; ctx.lineWidth=2; ctx.lineCap='round'; ctx.stroke();
  }, {passive:false});
  canvas.addEventListener('touchend',  () => drawing=false);

  document.getElementById('btn-clear-firma').addEventListener('click', () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  });

  // Antes de enviar el form de nuevo registro → capturar firma como base64
  $('#modalNuevoRegistro form').on('submit', function(){
    document.getElementById('firma_data').value = canvas.toDataURL('image/png');
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
