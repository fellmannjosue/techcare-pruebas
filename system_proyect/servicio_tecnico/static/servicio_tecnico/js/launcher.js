/* launcher.js — <--- hecho por claude code (22-oct-2026): "Registrar" en Control y Servicio Técnico.
   Modal 1 (qué registrar) → sub-modal (a qué pantalla). Encadena cerrando uno y abriendo el otro
   cuando el primero termina de cerrarse (evita backdrops colgados). Un solo global: ST_LAUNCHER. */
(function () {
  'use strict';
  function modal(el) { return (window.bootstrap && bootstrap.Modal) ? bootstrap.Modal.getOrCreateInstance(el) : null; }
  function chain(fromEl, toSel) {
    var toEl = document.querySelector(toSel);
    if (!toEl) return;
    if (fromEl) {
      fromEl.addEventListener('hidden.bs.modal', function once() {
        fromEl.removeEventListener('hidden.bs.modal', once);
        var m = modal(toEl); if (m) m.show();
      });
      var mf = modal(fromEl); if (mf) mf.hide();
    } else {
      var m2 = modal(toEl); if (m2) m2.show();
    }
  }
  document.addEventListener('click', function (e) {
    var next = e.target.closest('[data-reg-next]');
    if (next) { chain(next.closest('.modal'), next.dataset.regNext); return; }
    var back = e.target.closest('[data-reg-back]');
    if (back) { chain(back.closest('.modal'), back.dataset.regBack); return; }
  });
  window.ST_LAUNCHER = { chain: chain };
})();
