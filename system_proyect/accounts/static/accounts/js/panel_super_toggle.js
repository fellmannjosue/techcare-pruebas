/* <--- hecho por claude code: activa el portal nuevo desde el panel clásico.
   Config por data-* en #portal-config (un .js no lo procesa Django). */
(function () {
  var cfg = document.getElementById('portal-config');
  if (!cfg) return;
  var URL = cfg.dataset.url, CSRF = cfg.dataset.csrf;
  var btn = document.getElementById('btnPortalNuevo');
  if (!btn) return;
  btn.addEventListener('click', function () {
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Abriendo…';
    fetch(URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ prefer_new_ui: true }),
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        window.location.href = (d && d.destino) ? d.destino : '/portal/app/';
      })
      .catch(function () {
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-sparkles me-1"></i>Probar interfaz nueva';
        alert('No se pudo abrir el portal nuevo.');
      });
  });
})();
