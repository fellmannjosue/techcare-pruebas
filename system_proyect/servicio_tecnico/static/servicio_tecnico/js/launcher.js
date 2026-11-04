/* launcher.js — <--- hecho por claude code (04-nov-2026): "Registrar" en Control y Servicio Técnico.
   Conmutador segmentado (Opción A): un solo modal con 3 paneles; cada panel enlaza a los
   formularios de alta que YA existen (reg_inv/reg_mant/reg_control). Un solo global: ST_LAUNCHER. */
(function () {
  'use strict';
  var seg = document.getElementById('regSeg');
  if (!seg) return;

  function activar(k) {
    seg.querySelectorAll('button[data-seg]').forEach(function (b) {
      b.classList.toggle('on', b.dataset.seg === k);
    });
    document.querySelectorAll('.reg-pane[data-pane]').forEach(function (p) {
      p.classList.toggle('on', p.dataset.pane === k);
    });
  }

  seg.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-seg]');
    if (b) activar(b.dataset.seg);
  });

  window.ST_LAUNCHER = { activar: activar };
})();
