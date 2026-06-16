// <--- hecho por claude code: permisos coordinadores; Eliminar con fecha+hora seleccionable
(function () {
  const _cfg  = document.getElementById('page-config');
  if (!_cfg) return;
  const CSRF  = _cfg.dataset.csrf;
  const URL   = _cfg.dataset.url;
  const badgeTimers = new WeakMap();

  // ── helpers ──────────────────────────────────────────────────────────────────
  function mostrarGuardado() {
    const card  = document.querySelector('.card');
    const badge = card ? card.querySelector('.badge-saved') : null;
    if (!badge) return;
    badge.style.display = '';
    clearTimeout(badgeTimers.get(badge));
    badgeTimers.set(badge, setTimeout(() => badge.style.display = 'none', 2000));
  }

  function formatRemaining(ms) {
    if (ms <= 0) return 'Expirado';
    const d = Math.floor(ms / 86400000);
    const h = Math.floor((ms % 86400000) / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    if (d > 0) return d + 'd ' + h + 'h';
    if (h > 0) return h + 'h ' + m + 'm';
    return m + 'm';
  }

  function defaultLocal() {
    // ahora + 24 h en formato datetime-local (YYYY-MM-DDTHH:MM), hora local
    const t = new Date(Date.now() + 86400000);
    const p = n => String(n).padStart(2, '0');
    return `${t.getFullYear()}-${p(t.getMonth()+1)}-${p(t.getDate())}T${p(t.getHours())}:${p(t.getMinutes())}`;
  }

  function inputDe(chk) {
    return chk.parentElement.querySelector('.perm-hasta-input');
  }

  // ── enviar cambio de permiso ──────────────────────────────────────────────────
  function sendToggle(chk, valor, hastaLocal, callback) {
    const userId = parseInt(chk.dataset.user);
    const campo  = chk.dataset.campo;
    chk.disabled = true;
    fetch(URL, {
      method: 'POST',
      headers: {
        'Content-Type':     'application/json',
        'X-CSRFToken':      CSRF,
        'X-Requested-With': 'XMLHttpRequest',
      },
      body: JSON.stringify({ user_id: userId, campo, valor, hasta: hastaLocal || null }),
    })
    .then(r => r.json())
    .then(data => {
      chk.disabled = false;
      if (data.ok) {
        mostrarGuardado();
        if (callback) callback(data);
      } else {
        chk.checked = !valor;
        alert('Error al guardar el permiso.');
      }
    })
    .catch(() => { chk.disabled = false; chk.checked = !valor; });
  }

  // ── temporizador (cuenta regresiva) ───────────────────────────────────────────
  function arrancarTimer(chk, hastaISO) {
    if (!hastaISO) return;
    const hasta = new Date(hastaISO);
    if (isNaN(hasta)) return;
    let wrap = chk.parentElement.querySelector('.timer-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'timer-wrap small text-warning mt-1';
      wrap.innerHTML = '<i class="ti ti-clock"></i> <span class="timer-txt">…</span>';
      chk.parentElement.appendChild(wrap);
    }
    const txt = wrap.querySelector('.timer-txt');
    if (wrap._tid) clearTimeout(wrap._tid);
    (function tick() {
      const remaining = hasta - Date.now();
      if (remaining <= 0) {
        chk.checked = false;
        chk.dataset.hasta = '';
        const inp = inputDe(chk); if (inp) inp.classList.add('d-none');
        wrap.remove();
        sendToggle(chk, false, null, null);
        return;
      }
      if (txt) txt.textContent = formatRemaining(remaining);
      wrap._tid = setTimeout(tick, remaining < 3600000 ? 10000 : 60000);
    })();
  }

  function quitarTimer(chk) {
    const wrap = chk.parentElement.querySelector('.timer-wrap');
    if (wrap) { if (wrap._tid) clearTimeout(wrap._tid); wrap.remove(); }
  }

  // ── inicializar timers existentes ─────────────────────────────────────────────
  document.querySelectorAll('.perm-eliminar').forEach(chk => {
    if (chk.checked && chk.dataset.hasta) arrancarTimer(chk, chk.dataset.hasta);
  });

  // ── toggles (editar y eliminar) ───────────────────────────────────────────────
  document.querySelectorAll('.perm-toggle').forEach(chk => {
    chk.addEventListener('change', function () {
      const valor = this.checked;
      if (!this.classList.contains('perm-eliminar')) {
        sendToggle(this, valor, null, null);
        return;
      }
      // Eliminar: usa la fecha+hora del input (default +24h al activar)
      const inp = inputDe(this);
      if (valor) {
        if (inp) {
          if (!inp.value) inp.value = defaultLocal();
          inp.classList.remove('d-none');
        }
        sendToggle(this, true, inp ? inp.value : null, data => {
          this.dataset.hasta = data.hasta || '';
          if (data.hasta) arrancarTimer(this, data.hasta);
        });
      } else {
        if (inp) inp.classList.add('d-none');
        this.dataset.hasta = '';
        quitarTimer(this);
        sendToggle(this, false, null, null);
      }
    });
  });

  // ── cambiar la fecha/hora actualiza el "hasta" ────────────────────────────────
  document.querySelectorAll('.perm-hasta-input').forEach(inp => {
    inp.addEventListener('change', function () {
      const chk = this.parentElement.querySelector('.perm-eliminar');
      if (!chk || !chk.checked || !this.value) return;
      sendToggle(chk, true, this.value, data => {
        chk.dataset.hasta = data.hasta || '';
        if (data.hasta) arrancarTimer(chk, data.hasta);
      });
    });
  });
})();
