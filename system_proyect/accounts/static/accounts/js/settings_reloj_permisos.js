// <--- hecho por claude code: permisos reloj — checkboxes AJAX + label dinámico Visualizar
(function(){
  const _cfg = document.getElementById('page-config');
  if (!_cfg) return;
  const CSRF = _cfg.dataset.csrf;
  const URL  = _cfg.dataset.url;
  const badgeTimers = new WeakMap();

  function mostrarGuardado() {
    const card  = document.querySelector('.card');
    const badge = card ? card.querySelector('.badge-saved') : null;
    if (!badge) return;
    badge.style.display = '';
    clearTimeout(badgeTimers.get(badge));
    badgeTimers.set(badge, setTimeout(() => badge.style.display = 'none', 2000));
  }

  document.querySelectorAll('.perm-toggle').forEach(function(chk){
    chk.addEventListener('change', function(){
      const self   = this;
      const userId = parseInt(this.dataset.user);
      const campo  = this.dataset.campo;
      const valor  = this.checked;
      self.disabled = true;

      fetch(URL, {
        method: 'POST',
        headers: {
          'Content-Type':     'application/json',
          'X-CSRFToken':      CSRF,
          'X-Requested-With': 'XMLHttpRequest',
        },
        body: JSON.stringify({ user_id: userId, campo: campo, valor: valor }),
      })
      .then(r => r.json())
      .then(data => {
        self.disabled = false;
        if (data.ok) {
          mostrarGuardado();
          // Actualizar label "Todos" / "Solo marcados" en la columna Visualizar
          if (campo === 'ver_todos') {
            const labelEl = self.parentElement.querySelector('.small');
            if (labelEl) labelEl.textContent = valor ? 'Todos' : 'Solo marcados';
          }
        } else {
          self.checked = !valor;
          alert('Error al guardar el permiso.');
        }
      })
      .catch(() => {
        self.disabled = false;
        self.checked = !valor;
      });
    });
  });
})();
