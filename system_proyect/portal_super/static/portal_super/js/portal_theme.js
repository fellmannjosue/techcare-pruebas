/* portal_theme.js — <--- hecho por claude code
   Toggle de tema claro/oscuro DENTRO del user dropdown (antes era un botón flotante).
   Comparte la clave 'tc-theme' con la SPA para que la preferencia sea la misma. */
(function () {
  function aplicar(dark) {
    document.documentElement.classList.toggle('dark', dark);
    try { localStorage.setItem('tc-theme', dark ? 'dark' : 'light'); } catch (e) {}
  }
  function init() {
    var tgl = document.getElementById('tc-theme-toggle');
    if (!tgl) return;
    tgl.checked = document.documentElement.classList.contains('dark');
    tgl.addEventListener('change', function () { aplicar(tgl.checked); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
