// Botón Volver: usa history.back() si hay historial, sino nav_home_url
(function(){
  var btn = document.getElementById('btn-volver');
  if (btn && window.history.length > 1) {
    btn.addEventListener('click', function(e){
      e.preventDefault();
      history.back();
    });
  }
})();

(function(){
  let selectedFile = null;

  const dropzone    = document.getElementById('dropzone');
  const filePreview = document.getElementById('filePreview');
  const fileNameEl  = document.getElementById('fileName');
  const inputBrowse = document.getElementById('inputBrowse');
  const inputCamera = document.getElementById('inputCamera');

  function setFile(file) {
    selectedFile = file;
    if (file) {
      const kb = (file.size / 1024).toFixed(1);
      fileNameEl.textContent = `${file.name}  (${kb} KB)`;
      filePreview.classList.remove('d-none');
      dropzone.style.borderColor = '#206bc4';
      dropzone.style.background  = '#f0f5ff';
    } else {
      filePreview.classList.add('d-none');
      dropzone.style.borderColor = '';
      dropzone.style.background  = '';
      inputBrowse.value = '';
      inputCamera.value = '';
    }
  }

  document.getElementById('btnBrowse').addEventListener('click', () => inputBrowse.click());
  document.getElementById('btnCamera').addEventListener('click', () => inputCamera.click());
  document.getElementById('removeFile').addEventListener('click', () => setFile(null));

  inputBrowse.addEventListener('change', function(){ if (this.files[0]) setFile(this.files[0]); });
  inputCamera.addEventListener('change', function(){ if (this.files[0]) setFile(this.files[0]); });

  // Drag & drop
  ['dragenter','dragover'].forEach(evt => {
    dropzone.addEventListener(evt, e => { e.preventDefault(); dropzone.classList.add('drag-over'); });
  });
  dropzone.addEventListener('dragleave', () => dropzone.classList.remove('drag-over'));
  dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    const f = e.dataTransfer.files[0];
    if (f) setFile(f);
  });

  // Paste desde portapapeles
  document.addEventListener('paste', e => {
    if (!e.clipboardData) return;
    for (const item of e.clipboardData.items) {
      if (item.kind === 'file') { setFile(item.getAsFile()); break; }
    }
  });

  // Envío
  document.getElementById('ticketForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const btn = document.getElementById('btnSubmit');
    if (btn.disabled) return;

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Enviando…';
    document.getElementById('spinnerBox').classList.remove('d-none');

    const fd = new FormData(this);
    if (selectedFile) fd.set('attachment', selectedFile);
    else fd.delete('attachment');

    fetch(window._PAGE.submitUrl, {
      method: 'POST',
      body: fd,
      headers: { 'X-CSRFToken': window._PAGE.csrf }
    })
    .then(r => r.json())
    .then(data => {
      document.getElementById('spinnerBox').classList.add('d-none');
      if (data.redirect_url) {
        localStorage.setItem('ticketCreado', '1');
        window.location.href = data.redirect_url;
      } else {
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-send me-2"></i>Enviar Ticket';
        // Mostrar el detalle real de validación (campo + mensaje) si viene
        let detalle = '';
        if (data.details) {
          try {
            const errs = JSON.parse(data.details);
            const partes = [];
            for (const campo in errs) {
              const msg = (errs[campo][0] && errs[campo][0].message) || '';
              partes.push(msg);
            }
            detalle = partes.join(' ');
          } catch (_) {}
        }
        Swal.fire({ title: 'Error', text: detalle || data.error || 'Error al enviar.', icon: 'error' });
      }
    })
    .catch(() => {
      document.getElementById('spinnerBox').classList.add('d-none');
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-send me-2"></i>Enviar Ticket';
      Swal.fire({ title: 'Error de red', text: 'Verifica tu conexión e intenta de nuevo.', icon: 'error' });
    });
  });
})();
