(function(){
  if (typeof window._PAGE === 'undefined') return;
  const CSRF = window._PAGE.csrf;
  const URL  = window._PAGE.url;
  let badgeTimer;

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
      .then(function(r){ return r.json(); })
      .then(function(data){
        if (!data.ok) {
          self.checked = !valor;
          alert('Error al guardar el permiso.');
        } else {
          const badge = document.getElementById('badge-saved');
          badge.style.display = '';
          clearTimeout(badgeTimer);
          badgeTimer = setTimeout(function(){ badge.style.display = 'none'; }, 2000);
        }
      })
      .catch(function(){
        self.checked = !valor;
      })
      .finally(function(){ self.disabled = false; });
    });
  });
})();
