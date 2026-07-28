/* portal_theme.js — <--- hecho por claude code
   Botón flotante de tema claro/oscuro para las páginas Django del portal nuevo.
   Comparte la clave 'tc-theme' con la SPA para que la preferencia sea la misma. */
(function () {
  function aplicar(dark) {
    document.documentElement.classList.toggle('dark', dark);
    try { localStorage.setItem('tc-theme', dark ? 'dark' : 'light'); } catch (e) {}
    if (btn) btn.innerHTML = '<i class="ti ' + (dark ? 'ti-sun' : 'ti-moon') + '"></i>';
  }
  var dark = document.documentElement.classList.contains('dark');
  var btn = document.createElement('button');
  btn.id = 'ps-theme-btn';
  btn.type = 'button';
  btn.title = 'Cambiar tema';
  btn.innerHTML = '<i class="ti ' + (dark ? 'ti-sun' : 'ti-moon') + '"></i>';
  btn.addEventListener('click', function () { aplicar(!document.documentElement.classList.contains('dark')); });
  document.addEventListener('DOMContentLoaded', function () { document.body.appendChild(btn); });
})();
