// <--- hecho por claude code: permisos coordinadores con eliminación cronometrada (24 h)
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
    const h = Math.floor(ms / 3600000);
    const m = Math.floor((ms % 3600000) / 60000);
    if (h > 0) return h + 'h ' + m + 'm';
    return m + 'm';
  }

  // ── enviar cambio de permiso ──────────────────────────────────────────────────
  function sendToggle(chk, valor, callback) {
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
      body: JSON.stringify({ user_id: userId, campo, valor }),
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
    .catch(() => {
      chk.disabled = false;
      chk.checked = !valor;
    });
  }

  // ── arrancar temporizador para un checkbox elimininar ─────────────────────────
  function arrancarTimer(chk, hastaISO) {
    if (!hastaISO) return;
    const hasta = new Date(hastaISO);
    if (isNaN(hasta)) return;

    // Buscar o crear el div del timer junto al checkbox
    let wrap = chk.parentElement.querySelector('.timer-wrap');
    if (!wrap) {
      wrap = document.createElement('div');
      wrap.className = 'timer-wrap small text-warning mt-1';
      wrap.innerHTML = '<i class="ti ti-clock"></i> <span class="timer-txt">…</span>';
      chk.parentElement.appendChild(wrap);
    }
    const txt = wrap.querySelector('.timer-txt');

    function tick() {
      const remaining = hasta - Date.now();
      if (remaining <= 0) {
        // Tiempo expirado: deshabilitar sin animación
        chk.checked = false;
        chk.dataset.hasta = '';
        wrap.remove();
        sendToggle(chk, false, null);
        return;
      }
      if (txt) txt.textContent = formatRemaining(remaining);
      // Actualizar cada minuto (o cada 10 s si queda menos de 1 h)
      setTimeout(tick, remaining < 3600000 ? 10000 : 60000);
    }
    tick();
  }

  // ── inicializar checkboxes existentes ────────────────────────────────────────
  document.querySelectorAll('.perm-eliminar').forEach(chk => {
    const hastaISO = chk.dataset.hasta;
    if (chk.checked && hastaISO) {
      arrancarTimer(chk, hastaISO);
    }
  });

  // ── listener de cambio ───────────────────────────────────────────────────────
  document.querySelectorAll('.perm-toggle').forEach(chk => {
    chk.addEventListener('change', function () {
      const valor = this.checked;
      sendToggle(this, valor, data => {
        if (this.classList.contains('perm-eliminar')) {
          if (valor && data.hasta) {
            this.dataset.hasta = data.hasta;
            arrancarTimer(this, data.hasta);
          } else {
            this.dataset.hasta = '';
            const wrap = this.parentElement.querySelector('.timer-wrap');
            if (wrap) wrap.remove();
          }
        }
      });
    });
  });
})();
