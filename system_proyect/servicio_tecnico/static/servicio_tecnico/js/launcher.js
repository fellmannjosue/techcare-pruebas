/* launcher.js — <--- hecho por claude code (06-nov-2026): «Registrar» Opción C (panel maestro-detalle).
   Selector a la izquierda, panel en vivo a la derecha; «Continuar» abre el formulario de alta REAL ya preseleccionado
   (las URLs vienen de reg_inv/reg_mant/reg_control del servidor). Un solo global: ST_LAUNCHER. */
(function () {
  'use strict';
  var side = document.getElementById('rgcSide');
  if (!side) return;
  var META = {
    inv: { t: 'Inventario', s: 'Alta de un activo con su foto e historial', i: 'ti-package', bg: '#eff4ff', fg: '#2563eb' },
    man: { t: 'Mantenimiento', s: 'Ficha de reparación o mantenimiento', i: 'ti-tool', bg: '#e6f7f0', fg: '#0ca678' },
    ctl: { t: 'Control de equipo', s: 'Evaluación del equipo del maestro', i: 'ti-clipboard-check', bg: '#f1edff', fg: '#7048e8' }
  };
  var go = document.getElementById('rgcGo'), hint = document.getElementById('rgcHint');
  var actual = (side.querySelector('.rgc-optn.on') || side.querySelector('.rgc-optn') || {}).dataset;
  actual = actual ? actual.k : 'inv';

  function on(grupo) { return document.querySelector('.rgc-chips[data-grupo="' + grupo + '"] .rgc-chip.on'); }
  function destino() {
    var c;
    if (actual === 'ctl') {
      var acc = on('ctl-accion'), varr = on('ctl-variante');
      var esControl = acc && acc.dataset.accion === 'control';
      document.querySelectorAll('.rgc-chips[data-grupo="ctl-variante"] .rgc-chip').forEach(function (b) {
        b.disabled = !esControl; if (!esControl) b.classList.remove('on');
      });
      c = (esControl && varr) ? varr : acc;
      if (c) hint.textContent = 'Se abrirá: ' + (acc ? acc.dataset.t : '') + (esControl && varr ? ' · ' + varr.dataset.t : '');
    } else {
      c = on(actual);
      if (c) hint.textContent = 'Se abrirá: ' + META[actual].t + ' · ' + c.dataset.t;
    }
    go.href = c ? c.dataset.url : '#';
    go.classList.toggle('disabled', !c);
  }
  function activar(k) {
    actual = k;
    side.querySelectorAll('.rgc-optn').forEach(function (o) { o.classList.toggle('on', o.dataset.k === k); });
    document.querySelectorAll('.rgc-pane[data-pane]').forEach(function (p) { p.classList.toggle('on', p.dataset.pane === k); });
    var m = META[k], tag = document.getElementById('rgcTag');
    document.getElementById('rgcTitle').textContent = m.t;
    document.getElementById('rgcSub').textContent = m.s;
    tag.style.background = m.bg; tag.style.color = m.fg; tag.innerHTML = '<i class="ti ' + m.i + '"></i>';
    destino();
  }
  side.addEventListener('click', function (e) { var o = e.target.closest('.rgc-optn'); if (o) activar(o.dataset.k); });
  document.addEventListener('click', function (e) {
    var c = e.target.closest('.rgc-chip'); if (!c || c.disabled) return;
    var box = c.parentElement, grupo = box.dataset.grupo;
    if (grupo === 'ctl-variante') { var era = c.classList.contains('on'); box.querySelectorAll('.rgc-chip').forEach(function (x) { x.classList.remove('on'); }); if (!era) c.classList.add('on'); }
    else { box.querySelectorAll('.rgc-chip').forEach(function (x) { x.classList.remove('on'); }); c.classList.add('on'); }
    destino();
  });
  activar(actual);
  window.ST_LAUNCHER = { activar: activar };
})();
