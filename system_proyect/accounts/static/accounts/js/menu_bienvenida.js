/* <--- hecho por claude code: lógica "reenviar bienvenida" del panel principal (extraído de menu.html) */
(function () {
  const cfg = document.getElementById('bienvenida-config');
  if (!cfg) return;

  const URL_REENVIAR = cfg.dataset.urlReenviar;
  const CSRF         = cfg.dataset.csrf;

  function getMensaje() {
    const el = document.getElementById('mensajeExtra');
    return el ? el.value.trim() : '';
  }

  async function enviar(modo, email) {
    const body = new URLSearchParams({ modo, email: email || '', mensaje_extra: getMensaje() });
    const res  = await fetch(URL_REENVIAR, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/x-www-form-urlencoded' },
      body
    });
    return res.json();
  }

  function toast(msg, ok) {
    const el = document.createElement('div');
    el.className = `alert alert-${ok ? 'success' : 'danger'} alert-dismissible tc-toast-solido`;
    el.style.zIndex = 9999;
    // <--- hecho por claude code (10-nov-2026): fondo SÓLIDO y por encima del botón del asistente, aunque el navegador tenga el CSS viejo en caché
    Object.assign(el.style, {position: 'fixed', right: '16px', bottom: '88px', margin: '0', opacity: '1',
      maxWidth: 'min(420px, calc(100vw - 32px))', background: ok ? '#ebfbee' : '#fff5f5', color: '#1d2433',
      border: '1px solid ' + (ok ? '#b2f2bb' : '#ffc9c9'), borderLeft: '5px solid ' + (ok ? '#2fb344' : '#d63939'),
      borderRadius: '10px', boxShadow: '0 10px 28px rgba(15,23,42,.25)', fontWeight: '600', backdropFilter: 'none'});
    el.innerHTML = `<i class="ti ti-${ok ? 'check' : 'x'} me-1"></i>${msg}<button class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(el);
    setTimeout(() => el.remove(), 4000);
  }

  function actualizarContador() {
    const n = document.querySelectorAll('.chk-usuario:checked').length;
    const el = document.getElementById('contadorSel');
    if (el) el.textContent = n + ' seleccionados';
  }

  const buscador = document.getElementById('buscadorUsuarios');
  if (buscador) {
    buscador.addEventListener('input', function () {
      const q = this.value.toLowerCase();
      document.querySelectorAll('.fila-usuario').forEach(tr => {
        const coincide = tr.dataset.nombre.includes(q) || tr.dataset.email.includes(q);
        tr.style.display = coincide ? '' : 'none';
      });
    });
  }

  const btnSel = document.getElementById('btnSelTodos');
  if (btnSel) {
    btnSel.addEventListener('click', () => {
      document.querySelectorAll('.fila-usuario:not([style*="none"]) .chk-usuario').forEach(c => c.checked = true);
      const hdr = document.getElementById('chkTodosHeader');
      if (hdr) hdr.checked = true;
      actualizarContador();
    });
  }

  const btnDesel = document.getElementById('btnDeselTodos');
  if (btnDesel) {
    btnDesel.addEventListener('click', () => {
      document.querySelectorAll('.chk-usuario').forEach(c => c.checked = false);
      const hdr = document.getElementById('chkTodosHeader');
      if (hdr) hdr.checked = false;
      actualizarContador();
    });
  }

  const chkHeader = document.getElementById('chkTodosHeader');
  if (chkHeader) {
    chkHeader.addEventListener('change', function () {
      document.querySelectorAll('.fila-usuario:not([style*="none"]) .chk-usuario').forEach(c => c.checked = this.checked);
      actualizarContador();
    });
  }

  document.querySelectorAll('.chk-usuario').forEach(c => c.addEventListener('change', actualizarContador));

  document.querySelectorAll('.btn-enviar-uno').forEach(btn => {
    btn.addEventListener('click', async function () {
      const email  = this.dataset.email;
      const nombre = this.dataset.nombre;
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
      const data = await enviar('uno', email);
      this.disabled = false;
      this.innerHTML = '<i class="ti ti-send me-1"></i>Enviar';
      toast(data.ok ? `Correo enviado a ${nombre}` : `Error: ${data.error}`, data.ok);
    });
  });

  const btnEnviarSel = document.getElementById('btnEnviarSeleccionados');
  if (btnEnviarSel) {
    btnEnviarSel.addEventListener('click', async function () {
      const seleccionados = [...document.querySelectorAll('.chk-usuario:checked')].map(c => c.value);
      if (!seleccionados.length) { toast('Selecciona al menos un usuario.', false); return; }
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';
      let ok = 0, err = 0;
      for (const email of seleccionados) {
        const data = await enviar('uno', email);
        data.ok ? ok++ : err++;
      }
      this.disabled = false;
      this.innerHTML = '<i class="ti ti-mail me-1"></i>Enviar a seleccionados';
      toast(`Enviados: ${ok}${err ? ` | Errores: ${err}` : ''}`, err === 0);
    });
  }
})();
