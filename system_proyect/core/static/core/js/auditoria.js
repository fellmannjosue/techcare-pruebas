/* <--- hecho por claude code (10-nov-2026): rol Auditoría — en solo lectura los campos de los formularios
   que GUARDAN (form method=post, autoguardado, contenteditable) quedan deshabilitados, y en TODO el sistema
   no se puede escribir en ningún campo ni marcar casillas (también buscadores). Los select de filtro fuera
   de formularios de guardar siguen activos. El servidor igual rechaza toda escritura. */
(function () {
  'use strict';
  var PERMITIDOS = ['/accounts/logout/', '/accounts/maestro_logout/'];
  var SEL = 'input, select, textarea, button';

  function formPermitido(f) {
    var a = f.getAttribute('action') || '';
    for (var i = 0; i < PERMITIDOS.length; i++) { if (a.indexOf(PERMITIDOS[i]) !== -1) return true; }
    return false;
  }

  function bloquearCampo(el) {
    if (el.dataset.tcAud) return;
    var t = (el.getAttribute('type') || '').toLowerCase();
    if (t === 'hidden' || t === 'search') return;
    if (el.tagName === 'BUTTON' || t === 'submit' || t === 'reset' || t === 'button' || t === 'image') {
      var tipoBtn = el.tagName === 'BUTTON' ? (el.getAttribute('type') || 'submit').toLowerCase() : t;
      if (tipoBtn !== 'submit' && tipoBtn !== 'image') return;   // botones que solo abren/cierran cosas
    }
    el.dataset.tcAud = '1';
    el.disabled = true;
    el.title = 'Modo auditoría: solo lectura';
  }

  function bloquearTodo(el) {
    if (el.dataset.tcAudOk) return;
    el.dataset.tcAudOk = '1';
    el.disabled = true;
    el.title = 'Modo auditoría: solo lectura';
  }

  function aplicar(raiz) {
    raiz = raiz || document;
    var forms = raiz.querySelectorAll ? raiz.querySelectorAll('form') : [];
    for (var i = 0; i < forms.length; i++) {
      var f = forms[i];
      if ((f.getAttribute('method') || 'get').toLowerCase() !== 'post' || formPermitido(f)) continue;
      var campos = f.querySelectorAll(SEL);
      for (var j = 0; j < campos.length; j++) bloquearCampo(campos[j]);
      // campos asociados al form desde fuera (atributo form="id")
      if (f.id) {
        var ext = document.querySelectorAll('[form="' + f.id + '"]');
        for (var k = 0; k < ext.length; k++) bloquearCampo(ext[k]);
      }
    }
    var auto = raiz.querySelectorAll ? raiz.querySelectorAll('[data-autoguardar] input, [data-autoguardar] select, [data-autoguardar] textarea') : [];
    for (var m = 0; m < auto.length; m++) bloquearCampo(auto[m]);
    // «Solo ver, no escribir» (pedido del usuario): en TODO el sistema no se escribe en ningún campo
    // ni se marcan casillas, tampoco en buscadores. Quedan los select de filtro fuera de formularios de guardar.
    var escribir = raiz.querySelectorAll ? raiz.querySelectorAll('textarea, input') : [];
    for (var q = 0; q < escribir.length; q++) {
      var tp = (escribir[q].getAttribute('type') || 'text').toLowerCase();
      if (['hidden', 'submit', 'button', 'reset', 'image'].indexOf(tp) !== -1) continue;
      if (escribir[q].form && formPermitido(escribir[q].form)) continue;
      escribir[q].dataset.tcAud = '';   // fuerza el bloqueo aunque type=search
      bloquearTodo(escribir[q]);
    }
    var ce = raiz.querySelectorAll ? raiz.querySelectorAll('[contenteditable=""], [contenteditable="true"]') : [];
    for (var n = 0; n < ce.length; n++) ce[n].setAttribute('contenteditable', 'false');
  }

  function iniciar() {
    aplicar(document);
    var pendiente = false;
    new MutationObserver(function () {
      if (pendiente) return;
      pendiente = true;
      setTimeout(function () { pendiente = false; aplicar(document); }, 150);
    }).observe(document.body, { childList: true, subtree: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', iniciar);
  else iniciar();
})();
