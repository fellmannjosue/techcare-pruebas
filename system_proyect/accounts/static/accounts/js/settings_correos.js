/* <--- hecho por claude code: lógica página de configuración de correos */
(function () {
  const _cfg = document.getElementById('page-config');
  if (!_cfg) return;

  const CSRF        = _cfg.dataset.csrf;
  const URL_TEST    = _cfg.dataset.urlTest;
  const URL_SMTP    = _cfg.dataset.urlSmtp;

  // ── Tabs ─────────────────────────────────────────────────────────────────
  const tabs   = document.querySelectorAll('.correos-tab-link');
  const panels = document.querySelectorAll('.correos-panel');

  function activarTab(tabId) {
    tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tabId));
    panels.forEach(p => p.style.display = (p.id === 'panel-' + tabId) ? '' : 'none');
    if (tabId === 'smtp') verificarSmtp();
  }

  tabs.forEach(t => t.addEventListener('click', () => activarTab(t.dataset.tab)));

  // ── Filtro tabla usuarios ─────────────────────────────────────────────────
  const filtroInput = document.getElementById('correos-filtro');
  if (filtroInput) {
    filtroInput.addEventListener('input', function () {
      const q = this.value.toLowerCase();
      document.querySelectorAll('.user-row').forEach(tr => {
        tr.style.display = !q || tr.dataset.search.includes(q) ? '' : 'none';
      });
    });
  }

  // ── Verificar SMTP ────────────────────────────────────────────────────────
  function verificarSmtp() {
    const el = document.getElementById('smtp-status-result');
    if (!el || el.dataset.checked) return;
    el.dataset.checked = '1';
    el.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Verificando conexión…';

    fetch(URL_SMTP)
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          el.innerHTML = '<i class="ti ti-circle-check text-success me-1"></i><strong class="text-success">Conexión SMTP correcta</strong>';
        } else {
          el.innerHTML = `<i class="ti ti-alert-circle text-danger me-1"></i><strong class="text-danger">Error SMTP:</strong> ${d.error}`;
        }
      })
      .catch(() => {
        el.innerHTML = '<i class="ti ti-wifi-off text-warning me-1"></i>No se pudo verificar (error de red)';
      });
  }

  // ── Enviar correo de prueba ───────────────────────────────────────────────
  const btnTest   = document.getElementById('btn-test-email');
  const testResult = document.getElementById('test-result');
  if (btnTest) {
    btnTest.addEventListener('click', async function () {
      const dest = document.getElementById('test-dest').value.trim();
      if (!dest) { return; }
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando…';
      testResult.className = 'test-result';

      try {
        const res = await fetch(URL_TEST, {
          method: 'POST',
          headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
          body: JSON.stringify({ dest }),
        });
        const d = await res.json();
        testResult.innerHTML = d.ok
          ? `<div class="alert alert-success py-2"><i class="ti ti-check me-1"></i>Correo enviado a <strong>${dest}</strong>.</div>`
          : `<div class="alert alert-danger py-2"><i class="ti ti-x me-1"></i>Error: ${d.error}</div>`;
      } catch (e) {
        testResult.innerHTML = `<div class="alert alert-danger py-2">Error de red: ${e}</div>`;
      }

      testResult.classList.add('show');
      this.disabled = false;
      this.innerHTML = '<i class="ti ti-send me-1"></i>Enviar prueba';
    });
  }

  // ── Ping + Test por módulo ───────────────────────────────────────────────
  const URL_MODULO  = _cfg.dataset.urlModuloTest;
  const MODULO_NOMBRES = { enfermeria: 'Enfermería', bl: 'Coordinación BL', col: 'Coordinación Colegio' };

  // Ping (verificar conexión)
  document.querySelectorAll('.btn-modulo-ping').forEach(btn => {
    btn.addEventListener('click', async function () {
      const modulo = this.dataset.modulo;
      const card   = this.closest('.card-body');
      const status = card.querySelector('.modulo-status');
      const spin   = this.querySelector('.spinner-modulo');
      const icon   = this.querySelector('.modulo-icon');

      this.disabled = true;
      spin.classList.remove('d-none');
      icon.classList.add('d-none');
      status.className = 'modulo-status mt-1 small';
      status.textContent = '';

      try {
        const r = await fetch(URL_MODULO, {
          method: 'POST',
          headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
          body: JSON.stringify({ modulo, ping: true }),
        });
        const d = await r.json();
        status.classList.remove('d-none');
        if (d.ok) {
          status.innerHTML = '<i class="ti ti-circle-check text-success me-1"></i><span class="text-success">Conexión OK</span>';
        } else {
          status.innerHTML = `<i class="ti ti-alert-circle text-danger me-1"></i><span class="text-danger">${d.error}</span>`;
        }
      } catch (e) {
        status.classList.remove('d-none');
        status.innerHTML = '<i class="ti ti-wifi-off text-warning me-1"></i>Error de red';
      }

      spin.classList.add('d-none');
      icon.classList.remove('d-none');
      this.disabled = false;
    });
  });

  // Test email por módulo — abre modal
  let _moduloActivo = '';
  const modalEl     = document.getElementById('modal-modulo-test');
  const modal       = modalEl ? new bootstrap.Modal(modalEl) : null;

  document.querySelectorAll('.btn-modulo-test').forEach(btn => {
    btn.addEventListener('click', function () {
      _moduloActivo = this.dataset.modulo;
      if (!modal) return;
      document.getElementById('modal-modulo-nombre').textContent = MODULO_NOMBRES[_moduloActivo] || _moduloActivo;
      document.getElementById('modal-modulo-result').className = 'mt-2 d-none';
      modal.show();
    });
  });

  const btnModalEnviar = document.getElementById('btn-modal-modulo-enviar');
  if (btnModalEnviar) {
    btnModalEnviar.addEventListener('click', async function () {
      const dest    = document.getElementById('modal-modulo-dest').value.trim();
      const resultEl = document.getElementById('modal-modulo-result');
      if (!dest) return;

      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando…';
      resultEl.className = 'mt-2 d-none';

      try {
        const r = await fetch(URL_MODULO, {
          method: 'POST',
          headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
          body: JSON.stringify({ modulo: _moduloActivo, dest }),
        });
        const d = await r.json();
        resultEl.classList.remove('d-none');
        if (d.ok) {
          resultEl.innerHTML = `<div class="alert alert-success py-1 small mb-0"><i class="ti ti-check me-1"></i>Enviado desde <strong>${d.from}</strong> a <strong>${dest}</strong>.</div>`;
        } else {
          resultEl.innerHTML = `<div class="alert alert-danger py-1 small mb-0"><i class="ti ti-x me-1"></i>${d.error}</div>`;
        }
      } catch (e) {
        resultEl.classList.remove('d-none');
        resultEl.innerHTML = `<div class="alert alert-danger py-1 small mb-0">Error de red: ${e}</div>`;
      }

      this.disabled = false;
      this.innerHTML = '<i class="ti ti-send me-1"></i>Enviar';
    });
  }

  // ── Notificaciones por correo — checkboxes ──────────────────────────────
  const URL_NOTIF = _cfg.dataset.urlNotifToggle;

  function mostrarGuardado(panelEl) {
    const badge = panelEl ? panelEl.querySelector('.badge-notif-saved')
                          : document.querySelector('.badge-notif-saved');
    if (!badge) return;
    badge.style.display = '';
    clearTimeout(badge._t);
    badge._t = setTimeout(() => { badge.style.display = 'none'; }, 2000);
  }

  function _guardarNotif(chk) {
    const userId  = chk.dataset.user;
    const campo   = chk.dataset.campo;
    const valor   = chk.checked;
    const panelEl = chk.closest('.correos-panel');

    chk.disabled = true;
    fetch(URL_NOTIF, {
      method:      'POST',
      credentials: 'same-origin',
      headers:     { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body:        JSON.stringify({ user_id: userId, campo, valor }),
    })
    .then(r => {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(d => {
      chk.disabled = false;
      if (d.ok) {
        mostrarGuardado(panelEl);
      } else {
        chk.checked = !valor;
        alert('Error al guardar: ' + (d.error || 'desconocido'));
      }
    })
    .catch(err => {
      chk.disabled = false;
      chk.checked = !valor;
      alert('Error al guardar: ' + err);
    });
  }

  // Adjuntar a todos los checkboxes de toggle al cargar la página
  document.querySelectorAll('.notif-toggle').forEach(chk => {
    chk.addEventListener('change', () => _guardarNotif(chk));
  });

  // ── Init ──────────────────────────────────────────────────────────────────
  activarTab('usuarios');

})();
