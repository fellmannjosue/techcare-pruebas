/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
// <--- hecho por claude code: permiso provisional para registrar permisos (guardar + cuenta regresiva)
(function () {
  const cfg = document.getElementById('page-config');
  const CSRF = cfg.dataset.csrf, URL = cfg.dataset.url;

  async function guardar(user, valor) {
    const res = await fetch(URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest' },
      body: JSON.stringify({ user_id: user, campo: 'permisos_registrar_hasta', valor: valor }),
    });
    return res.json();
  }
  function badge(user, ms) {
    const b = document.querySelector(`.perm-hasta-cd[data-user="${user}"]`);
    if (b) b.dataset.ms = ms || 0;
  }
  document.querySelectorAll('.perm-hasta-save').forEach(btn => {
    btn.addEventListener('click', async function () {
      const user = this.dataset.user;
      const inp = document.querySelector(`.perm-hasta-input[data-user="${user}"]`);
      this.disabled = true;
      const r = await guardar(user, inp.value || '');
      this.disabled = false;
      if (r.ok) badge(user, r.hasta_ms); else alert(r.error || 'Error al guardar');
    });
  });
  document.querySelectorAll('.perm-hasta-clear').forEach(btn => {
    btn.addEventListener('click', async function () {
      const user = this.dataset.user;
      const inp = document.querySelector(`.perm-hasta-input[data-user="${user}"]`);
      inp.value = '';
      const r = await guardar(user, '');
      if (r.ok) badge(user, 0);
    });
  });
  // Cuenta regresiva en vivo
  function tick() {
    const now = Date.now();
    document.querySelectorAll('.perm-hasta-cd').forEach(b => {
      const ms = parseInt(b.dataset.ms || '0', 10);
      if (!ms) { b.className = 'ms-auto badge bg-secondary-lt text-secondary perm-hasta-cd'; b.textContent = 'Sin permiso'; b.dataset.ms = 0; return; }
      let diff = Math.floor((ms - now) / 1000);
      if (diff <= 0) { b.className = 'ms-auto badge bg-secondary-lt text-secondary perm-hasta-cd'; b.textContent = 'Vencido'; return; }
      const d = Math.floor(diff / 86400); diff %= 86400;
      const h = Math.floor(diff / 3600); diff %= 3600;
      const m = Math.floor(diff / 60), s = diff % 60;
      const cls = (ms - now) < 3600000 ? 'bg-red-lt text-red' : 'bg-green-lt text-green';
      b.className = `ms-auto badge ${cls} perm-hasta-cd`;
      b.innerHTML = `<i class="ti ti-clock-hour-4 me-1"></i>${d ? d + 'd ' : ''}${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
    });
  }
  tick(); setInterval(tick, 1000);
})();
