(function(){
  if (typeof window._PAGE === 'undefined') return;

  const CSRF         = window._PAGE.csrf;
  const URL_ESTADO   = window._PAGE.urlEstadoMantenimiento;
  const URL_TOGGLE   = window._PAGE.urlToggleMantenimiento;

  const badge        = document.getElementById('mant-badge');
  const badgeTxt     = document.getElementById('mant-badge-txt');
  const statusBar    = document.getElementById('mant-status-bar');
  const activateBtn  = document.getElementById('mant-activate-btn');
  const deactivateBtn= document.getElementById('mant-deactivate-btn');
  const messageInput = document.getElementById('mant-message');
  const endTimeInput = document.getElementById('mant-end-time');
  const blockedCount = document.getElementById('mant-blocked-count');
  const contador     = document.getElementById('mant-contador');

  // Guard: modal only present for superusers
  if (!badge) return;

  let selectedArea = 'all';
  let countdownInterval = null;

  // ── Área buttons ────────────────────────────────────────────────────
  const hints = {
    all:     document.getElementById('mant-hint-all'),
    bilingue:document.getElementById('mant-hint-bilingue'),
    colegio: document.getElementById('mant-hint-colegio'),
    staff:   document.getElementById('mant-hint-staff'),
  };

  function filtrarFilasPorArea(area) {
    document.querySelectorAll('.mant-fila').forEach(tr => {
      const isStaff = tr.dataset.staff === '1';
      const groups  = tr.dataset.groups || '';
      let visible = false;
      if (area === 'staff')         visible = isStaff;
      else if (area === 'all')      visible = !isStaff;
      else if (area === 'bilingue') visible = !isStaff && groups.includes('maestros_bilingue');
      else if (area === 'colegio')  visible = !isStaff && groups.includes('maestros_colegio');
      tr.style.display = visible ? '' : 'none';
      if (!visible) tr.querySelector('.mant-chk').checked = false;
    });
    actualizarContador();
  }

  document.querySelectorAll('.mant-area-btn').forEach(btn => {
    btn.addEventListener('click', function(){
      selectedArea = this.dataset.area;
      document.querySelectorAll('.mant-area-btn').forEach(b => {
        b.classList.remove('btn-primary'); b.classList.add('btn-outline-primary');
      });
      this.classList.remove('btn-outline-primary'); this.classList.add('btn-primary');
      Object.values(hints).forEach(h => { if(h) h.style.display = 'none'; });
      if (hints[selectedArea]) hints[selectedArea].style.display = '';
      filtrarFilasPorArea(selectedArea);
    });
  });
  // Aplicar filtro inicial
  filtrarFilasPorArea('all');

  // ── Tabla usuarios ──────────────────────────────────────────────────
  function actualizarContador(){
    const n = document.querySelectorAll('.mant-chk:checked').length;
    contador.textContent = n + ' seleccionados';
    if(n > 0){
      blockedCount.textContent = n + ' usuario' + (n > 1 ? 's' : '') + ' bloqueado' + (n > 1 ? 's' : '');
      blockedCount.style.display = '';
    } else {
      blockedCount.style.display = 'none';
    }
  }

  document.getElementById('mant-buscar').addEventListener('input', function(){
    const q = this.value.toLowerCase();
    document.querySelectorAll('.mant-fila').forEach(tr => {
      tr.style.display = (tr.dataset.nombre.includes(q) || tr.dataset.email.includes(q)) ? '' : 'none';
    });
  });

  document.getElementById('mant-sel-todos').addEventListener('click', () => {
    document.querySelectorAll('.mant-fila:not([style*="none"]) .mant-chk').forEach(c => c.checked = true);
    document.getElementById('mant-chk-header').checked = true;
    actualizarContador();
  });

  document.getElementById('mant-desel-todos').addEventListener('click', () => {
    document.querySelectorAll('.mant-chk').forEach(c => c.checked = false);
    document.getElementById('mant-chk-header').checked = false;
    actualizarContador();
  });

  document.getElementById('mant-chk-header').addEventListener('change', function(){
    document.querySelectorAll('.mant-fila:not([style*="none"]) .mant-chk').forEach(c => c.checked = this.checked);
    actualizarContador();
  });

  document.querySelectorAll('.mant-chk').forEach(c => c.addEventListener('change', actualizarContador));

  // ── Utilidades ──────────────────────────────────────────────────────
  function pad(n){ return String(n).padStart(2,'0'); }

  function startCountdown(endTimeStr){
    if(countdownInterval) clearInterval(countdownInterval);
    if(!endTimeStr) return;
    const endDt = new Date(endTimeStr);
    function tick(){
      const diff = endDt - Date.now();
      if(diff <= 0){ badgeTxt.textContent = 'ACTIVO'; return; }
      const h = Math.floor(diff/3600000);
      const m = Math.floor((diff%3600000)/60000);
      const s = Math.floor((diff%60000)/1000);
      badgeTxt.textContent = `ACTIVO ${pad(h)}:${pad(m)}:${pad(s)}`;
    }
    tick();
    countdownInterval = setInterval(tick, 1000);
  }

  function setInputsDisabled(dis){
    messageInput.disabled = dis;
    endTimeInput.disabled  = dis;
    document.querySelectorAll('.mant-area-btn').forEach(b => b.disabled = dis);
    document.querySelectorAll('.mant-chk, #mant-chk-header, #mant-sel-todos, #mant-desel-todos, #mant-buscar').forEach(el => el.disabled = dis);
  }

  function aplicarEstado(data){
    const activo = data.activo;

    if(activo){
      badge.style.display     = '';
      statusBar.style.display = '';
      statusBar.className     = 'alert alert-danger py-2 mb-3';
      const areaLabel = {all:'Todas las áreas', bilingue:'Bilingüe', colegio:'Colegio', staff:'Staff'}[data.area] || data.area;
      const blocked = data.blocked_users || [];
      let extra = blocked.length
        ? ` — <strong>${blocked.length} usuario${blocked.length>1?'s':''} específico${blocked.length>1?'s':''}</strong>`
        : '';
      statusBar.innerHTML = `<i class="ti ti-lock me-1"></i><strong>Mantenimiento ACTIVO</strong> — Área: ${areaLabel}${extra}`;
      activateBtn.style.display   = 'none';
      deactivateBtn.style.display = '';
      setInputsDisabled(true);
      startCountdown(data.end_time || '');

      // Marcar checkboxes de los usuarios bloqueados (solo lectura)
      document.querySelectorAll('.mant-chk').forEach(c => {
        c.checked  = blocked.includes(c.value.toLowerCase());
      });
      actualizarContador();
    } else {
      badge.style.display     = 'none';
      statusBar.style.display = '';
      statusBar.className     = 'alert alert-success py-2 mb-3';
      statusBar.innerHTML     = '<i class="ti ti-check me-1"></i>Sistema <strong>activo</strong> — No hay mantenimiento en curso.';
      activateBtn.style.display   = '';
      deactivateBtn.style.display = 'none';
      setInputsDisabled(false);
      if(countdownInterval){ clearInterval(countdownInterval); badgeTxt.textContent = 'ACTIVO'; }
      if(data.message)  messageInput.value = data.message;
      if(data.end_time) endTimeInput.value  = data.end_time;
      // Sincronizar área
      selectedArea = data.area || 'all';
      document.querySelectorAll('.mant-area-btn').forEach(b => {
        const sel = b.dataset.area === selectedArea;
        b.classList.toggle('btn-primary', sel);
        b.classList.toggle('btn-outline-primary', !sel);
      });
      Object.values(hints).forEach(h => { if(h) h.style.display = 'none'; });
      if (hints[selectedArea]) hints[selectedArea].style.display = '';
      filtrarFilasPorArea(selectedArea);

      // Limpiar selección de usuarios
      document.querySelectorAll('.mant-chk').forEach(c => c.checked = false);
      document.getElementById('mant-chk-header').checked = false;
      actualizarContador();
    }
  }

  // Cargar estado al abrir el modal
  const modalEl = document.getElementById('modalMantenimiento');
  if (modalEl) {
    modalEl.addEventListener('show.bs.modal', function(){
      fetch(URL_ESTADO).then(r => r.json()).then(aplicarEstado);
    });
  }

  // Badge en page load
  fetch(URL_ESTADO).then(r => r.json()).then(d => {
    if(d.activo){ badge.style.display = ''; startCountdown(d.end_time || ''); }
  });

  window.mantToggle = async function(){
    activateBtn.disabled   = true;
    deactivateBtn.disabled = true;
    const blockedUsers = [...document.querySelectorAll('.mant-chk:checked')].map(c => c.value);
    const payload = {
      area:          selectedArea,
      message:       messageInput.value.trim(),
      end_time:      endTimeInput.value,
      blocked_users: blockedUsers,
    };
    try {
      const res = await fetch(URL_TOGGLE, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if(data.ok) aplicarEstado(data);
    } catch(e) {
      alert('Error al cambiar el estado de mantenimiento.');
    }
    activateBtn.disabled   = false;
    deactivateBtn.disabled = false;
  };
})();
