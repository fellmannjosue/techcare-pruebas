/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(function(){});});}

/* <--- hecho por claude code: init de tooltips de Bootstrap (descripción de grupos en el form de usuario) */
window.addEventListener('load', function () {
  if (window.bootstrap && bootstrap.Tooltip) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(function (el) {
      new bootstrap.Tooltip(el);
    });
  }
});

/* <--- hecho por claude code (06-nov-2026): acordeón de Configuración — abre la sección del acceso actual, buscador y «Reenviar correo» */
document.addEventListener('DOMContentLoaded', function () {
  var nav = document.querySelector('.cfg-nav'); if (!nav) return;
  var grupos = nav.querySelectorAll('details.cfg-acc');
  var act = nav.querySelector('.cfg-link.active');
  if (act) act.closest('details').open = true; else if (grupos[0]) grupos[0].open = true;
  grupos.forEach(function (d) {   // una sección abierta a la vez (como acordeón), salvo mientras se busca
    d.addEventListener('toggle', function () {
      if (!d.open || document.getElementById('cfg-q').value.trim()) return;
      grupos.forEach(function (o) { if (o !== d) o.open = false; });
    });
  });
  var q = document.getElementById('cfg-q');
  if (q) q.addEventListener('input', function () {
    var t = q.value.trim().toLowerCase();
    grupos.forEach(function (d) {
      var vis = 0;
      d.querySelectorAll('.cfg-link').forEach(function (a) { var ok = !t || a.textContent.toLowerCase().indexOf(t) > -1 || d.querySelector('summary').textContent.toLowerCase().indexOf(t) > -1; a.hidden = !ok; vis += ok ? 1 : 0; });
      d.hidden = !!t && !vis; if (t) d.open = vis > 0;
    });
    if (!t) { grupos.forEach(function (d) { d.open = false; }); var a = nav.querySelector('.cfg-link.active'); (a ? a.closest('details') : grupos[0]).open = true; }
  });
  nav.addEventListener('click', function (e) {   // «Reenviar correo»: el mismo botón del menú del superusuario
    var r = e.target.closest('.js-abrir-reenviar'); if (!r) return;
    e.preventDefault();
    var b = document.getElementById('btnAbrirReenviar'); if (b) b.click();
  });
});
