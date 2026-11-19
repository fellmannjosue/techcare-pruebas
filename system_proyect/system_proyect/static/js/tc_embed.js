/* <--- hecho por claude code (09-nov-2026): página abierta DENTRO de la ventana «Registrar» (?embed=1).
   Solo se ve el formulario (modal) que la página abre sola con ?nuevo=. Cerrar ese modal = cerrar la ventana padre. */
(function () {
  if (!document.body.classList.contains('tc-embed') || window.parent === window) return;
  function avisar(tipo, extra) { var m = { tc: 'embed', tipo: tipo }; for (var k in (extra || {})) m[k] = extra[k]; window.parent.postMessage(m, location.origin); }
  var enviando = false;
  document.addEventListener('submit', function () { enviando = true; avisar('enviando'); }, true);
  document.addEventListener('hidden.bs.modal', function () {
    if (enviando) return;
    setTimeout(function () { if (!document.querySelector('.modal.show')) avisar('cerrar'); }, 50);
  });
  window.addEventListener('load', function () {
    setTimeout(function () {
      var m = document.querySelector('.modal.show');
      if (m) { avisar('listo', { titulo: (m.querySelector('.modal-title') || {}).textContent || '' }); }
      else { avisar('sin-formulario'); }
    }, 700);
  });
})();
