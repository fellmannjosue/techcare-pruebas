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
