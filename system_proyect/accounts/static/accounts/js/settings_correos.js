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

  // ── Init ──────────────────────────────────────────────────────────────────
  activarTab('usuarios');

})();
