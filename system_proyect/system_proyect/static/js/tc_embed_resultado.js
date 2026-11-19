/* <--- hecho por claude code (09-nov-2026): el formulario de la ventana «Registrar» terminó (guardado o error).
   Se avisa a la ventana padre; si se abrió suelto (sin padre), se va al destino normal. */
(function () {
  var d = {}; try { d = JSON.parse(document.getElementById('tc-embed-resultado').textContent); } catch (e) {}
  if (window.parent && window.parent !== window) {
    window.parent.postMessage({ tc: 'embed', tipo: 'resultado', ok: !!d.ok, mensajes: d.mensajes || [], destino: d.destino || '' }, location.origin);
  } else if (d.destino) {
    location.replace(d.destino);
  }
})();
