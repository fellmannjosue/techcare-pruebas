/* <--- hecho por claude code: lógica del visor de logs (extraído de settings_logs.html) */
(function () {
  const cfg     = document.getElementById('logs-config');
  const API     = cfg ? cfg.dataset.apiUrl : '';

  const tabs    = document.querySelectorAll('#log-tabs .nav-link');
  const output  = document.getElementById('log-output');
  const spinner = document.getElementById('main-spinner');

  const panelFile  = document.getElementById('panel-file');
  const panelDj    = document.getElementById('panel-django');
  const panelAc    = document.getElementById('panel-accesos');
  const toolbarF   = document.getElementById('toolbar-file');
  const toolbarT   = document.getElementById('toolbar-table');

  let currentTab = 'apache_error';
  let debounce   = null;

  // ── Helpers ──────────────────────────────────────────────────────────────
  function esc(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function hl(text, q) {
    if (!q) return esc(text);
    const i = text.toLowerCase().indexOf(q.toLowerCase());
    if (i === -1) return esc(text);
    return esc(text.slice(0, i))
      + '<mark class="log-hl">' + esc(text.slice(i, i + q.length)) + '</mark>'
      + esc(text.slice(i + q.length));
  }

  function timestamp() {
    return new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  }

  // ── Render terminal ───────────────────────────────────────────────────────
  function renderTerminal(lines) {
    const q = (document.getElementById('log-filtro').value || '').trim();
    let cntErr = 0, cntWarn = 0;

    if (!lines.length) {
      output.innerHTML = '<span class="text-muted small">Sin resultados para el filtro actual.</span>';
    } else {
      output.innerHTML = lines.map((l, i) => {
        if (l.nivel === 'error')   cntErr++;
        if (l.nivel === 'warning') cntWarn++;
        return `<div class="log-line lvl-${l.nivel}"><span class="log-num">${i + 1}</span><span class="log-txt">${hl(l.text, q)}</span></div>`;
      }).join('');
    }

    document.getElementById('cnt-error').textContent  = cntErr;
    document.getElementById('cnt-warn').textContent   = cntWarn;
    document.getElementById('log-total').textContent  = `${lines.length} líneas`;
    document.getElementById('stat-errores').textContent = cntErr;
    document.getElementById('last-update').textContent   = timestamp();
  }

  // ── Fetch log ─────────────────────────────────────────────────────────────
  function cargarLog(tab) {
    const lineas = document.getElementById('log-lineas').value;
    const q      = (document.getElementById('log-filtro').value || '').trim();
    spinner.parentElement.classList.add('is-loading');
    output.innerHTML = '<span class="text-muted small"><i class="ti ti-loader-2 me-1"></i>Cargando…</span>';

    fetch(`${API}?log=${tab}&lineas=${lineas}&q=${encodeURIComponent(q)}`)
      .then(r => r.json())
      .then(d => {
        spinner.parentElement.classList.remove('is-loading');
        if (!d.ok) {
          output.innerHTML = `<span class="text-danger"><i class="ti ti-alert-circle me-1"></i>${esc(d.error)}</span>`;
          return;
        }
        document.getElementById('stat-requests').textContent = d.total;
        renderTerminal(d.lines);
      })
      .catch(e => {
        spinner.parentElement.classList.remove('is-loading');
        output.innerHTML = `<span class="text-danger"><i class="ti ti-wifi-off me-1"></i>Error de red: ${e}</span>`;
      });
  }

  // ── Cambiar tab ───────────────────────────────────────────────────────────
  function activarTab(tab) {
    currentTab = tab;
    tabs.forEach(t => t.classList.toggle('active', t.dataset.tab === tab));

    const esArchivo = ['apache_error', 'apache_access', 'apache_general'].includes(tab);

    panelFile.style.display = esArchivo ? '' : 'none';
    panelDj.style.display   = tab === 'django'  ? '' : 'none';
    panelAc.style.display   = tab === 'accesos' ? '' : 'none';
    toolbarF.style.display  = esArchivo ? '' : 'none';
    toolbarT.style.display  = !esArchivo ? '' : 'none';

    if (esArchivo) cargarLog(tab);
    else {
      actualizarTabla();
      document.getElementById('last-update').textContent = timestamp();
    }
  }

  // ── Filtro tablas ─────────────────────────────────────────────────────────
  function actualizarTabla() {
    const q    = (document.getElementById('tbl-filtro').value || '').trim().toLowerCase();
    const rows = document.querySelectorAll(
      currentTab === 'django' ? '.dj-row' : '.ac-row'
    );
    let visible = 0;
    rows.forEach(r => {
      const ok = !q || r.dataset.text.includes(q);
      r.style.display = ok ? '' : 'none';
      if (ok) visible++;
    });
    document.getElementById('tbl-info').textContent = `${visible} registros`;
  }

  // ── Eventos ───────────────────────────────────────────────────────────────
  tabs.forEach(t => t.addEventListener('click', () => activarTab(t.dataset.tab)));

  document.getElementById('log-filtro').addEventListener('input', function () {
    clearTimeout(debounce);
    debounce = setTimeout(() => cargarLog(currentTab), 350);
  });

  document.getElementById('log-lineas').addEventListener('change', () => cargarLog(currentTab));
  document.getElementById('btn-refresh').addEventListener('click', () => activarTab(currentTab));

  document.getElementById('btn-scroll-top').addEventListener('click', () => {
    output.scrollTop = 0;
  });

  document.getElementById('tbl-filtro').addEventListener('input', function () {
    clearTimeout(debounce);
    debounce = setTimeout(actualizarTabla, 250);
  });

  // ── Init ──────────────────────────────────────────────────────────────────
  activarTab('apache_error');

})();
