/* settings_envio_login.js — hecho por claude code */
(function () {
  'use strict';

  const _cfg        = document.getElementById('page-config');
  if (!_cfg) return;
  const URL_PREVIEW = _cfg.dataset.urlPreview;
  const URL_SEND    = _cfg.dataset.urlSend;
  const CSRF        = _cfg.dataset.csrf;

  const form        = document.getElementById('form-envio-login');
  const iframe      = document.getElementById('iframe-preview');
  const badgeEstado = document.getElementById('badge-preview-estado');
  const btnPreview  = document.getElementById('btn-preview');
  const btnEnviar   = document.getElementById('btn-enviar');

  // ── Lista de usuarios ──────────────────────────────────────────────────────
  const inputBuscar     = document.getElementById('input-buscar-usuarios');
  const btnSelTodos     = document.getElementById('btn-sel-todos');
  const btnSelNinguno   = document.getElementById('btn-sel-ninguno');
  const badgeSelec      = document.getElementById('badge-seleccionados');
  const textoSinResult  = document.getElementById('texto-sin-resultados');
  const listaUsuarios   = document.getElementById('lista-usuarios');

  function getCheckboxes() {
    return Array.from(form.querySelectorAll('.chk-usuario'));
  }

  function getVisibles() {
    return getCheckboxes().filter(function (chk) {
      return chk.closest('.user-check-item').style.display !== 'none';
    });
  }

  function actualizarContador() {
    const total = getCheckboxes().filter(function (c) { return c.checked; }).length;
    badgeSelec.textContent = total + ' seleccionado' + (total !== 1 ? 's' : '');
    badgeSelec.className = total > 0
      ? 'badge bg-blue-lt text-blue ms-1'
      : 'badge bg-secondary-lt text-secondary ms-1';
  }

  // Escuchar cambios en checkboxes
  listaUsuarios.addEventListener('change', function (e) {
    if (e.target.classList.contains('chk-usuario')) {
      actualizarContador();
    }
  });

  // Botón Todos — selecciona solo los visibles
  btnSelTodos.addEventListener('click', function () {
    getVisibles().forEach(function (c) { c.checked = true; });
    actualizarContador();
  });

  // Botón Ninguno — desmarca todos
  btnSelNinguno.addEventListener('click', function () {
    getCheckboxes().forEach(function (c) { c.checked = false; });
    actualizarContador();
  });

  // Buscador en tiempo real
  inputBuscar.addEventListener('input', function () {
    const q = this.value.trim().toLowerCase();
    let visibles = 0;

    getCheckboxes().forEach(function (chk) {
      const item   = chk.closest('.user-check-item');
      const nombre = (item.dataset.nombre || '').toLowerCase();
      const email  = (item.dataset.email  || '').toLowerCase();
      const match  = !q || nombre.includes(q) || email.includes(q);
      item.style.display = match ? '' : 'none';
      if (match) visibles++;
    });

    textoSinResult.style.display = visibles === 0 ? '' : 'none';
    actualizarContador();
  });

  // ── Marcar preview como "sin actualizar" al editar ─────────────────────────
  form.querySelectorAll('.preview-field').forEach(function (el) {
    el.addEventListener('input', function () {
      badgeEstado.textContent = 'Sin actualizar';
      badgeEstado.className = 'badge bg-orange-lt text-orange ms-auto';
    });
  });

  // ── Actualizar vista previa ────────────────────────────────────────────────
  function actualizarPreview() {
    btnPreview.disabled = true;
    btnPreview.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Cargando…';
    badgeEstado.textContent = 'Cargando…';
    badgeEstado.className = 'badge bg-blue-lt text-blue ms-auto';

    const data = new FormData(form);
    data.append('csrfmiddlewaretoken', CSRF);

    fetch(URL_PREVIEW, { method: 'POST', body: data })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (res.html) {
          iframe.srcdoc = res.html;
          badgeEstado.textContent = 'Actualizado';
          badgeEstado.className = 'badge bg-green-lt text-green ms-auto';
        }
      })
      .catch(function () {
        badgeEstado.textContent = 'Error';
        badgeEstado.className = 'badge bg-red-lt text-red ms-auto';
      })
      .finally(function () {
        btnPreview.disabled = false;
        btnPreview.innerHTML = '<i class="ti ti-eye me-1"></i>Actualizar vista previa';
      });
  }

  btnPreview.addEventListener('click', actualizarPreview);

  // ── Enviar correo ──────────────────────────────────────────────────────────
  btnEnviar.addEventListener('click', function () {
    const seleccionados = getCheckboxes().filter(function (c) { return c.checked; });

    if (seleccionados.length === 0) {
      alert('Selecciona al menos un usuario antes de enviar.');
      return;
    }

    const msg = seleccionados.length === 1
      ? '¿Enviar el correo a 1 usuario?'
      : '¿Enviar el correo a ' + seleccionados.length + ' usuarios?';

    if (!confirm(msg)) return;

    btnEnviar.disabled = true;
    btnEnviar.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando…';

    const data = new FormData(form);
    data.append('csrfmiddlewaretoken', CSRF);

    fetch(URL_SEND, { method: 'POST', body: data })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        const header = document.getElementById('modal-resultado-header');
        const title  = document.getElementById('modal-resultado-title');
        const body   = document.getElementById('modal-resultado-body');

        if (res.ok) {
          header.className = 'modal-header bg-green-lt';
          title.textContent = '✅ Correos enviados';
          let html = '<p class="mb-2">Se enviaron correctamente <strong>' + res.enviados + '</strong> correo(s).</p>';
          if (res.errores && res.errores.length) {
            html += '<div class="alert alert-warning py-2 mb-0">'
              + '<strong>No se pudo enviar a:</strong><br>'
              + res.errores.map(function (e) { return '<code>' + e + '</code>'; }).join(', ')
              + '</div>';
          }
          body.innerHTML = html;
        } else {
          header.className = 'modal-header bg-red-lt';
          title.textContent = '❌ Error al enviar';
          body.innerHTML = '<p class="text-danger mb-0">' + (res.error || 'Error desconocido') + '</p>';
        }

        const modal = new bootstrap.Modal(document.getElementById('modal-resultado'));
        modal.show();
      })
      .catch(function () {
        alert('Error de red al intentar enviar el correo.');
      })
      .finally(function () {
        btnEnviar.disabled = false;
        btnEnviar.innerHTML = '<i class="ti ti-send me-1"></i>Enviar correo';
      });
  });

  // Inicializar contador
  actualizarContador();

})();
