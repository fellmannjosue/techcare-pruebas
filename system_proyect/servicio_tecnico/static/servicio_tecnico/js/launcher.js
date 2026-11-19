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
    cargar(c ? c.dataset.url : '');
  }

  /* <--- hecho por claude code (09-nov-2026): «Lo que vas a llenar» es el formulario REAL dentro de la ventana.
     Se carga la pantalla de alta con ?embed=1 (core.middleware.EmbedVentanaMiddleware + tc_embed.js): solo se ve su
     formulario y, al guardar, el servidor avisa aquí por postMessage en vez de ir a la lista. */
  var modal = document.getElementById('modalRegistrar');
  var frame = document.getElementById('rgcFrame'), load = document.getElementById('rgcLoad'), msg = document.getElementById('rgcMsg');
  var urlActual = '', pendiente = '', huboCambios = false;
  function abierta() { return modal && modal.classList.contains('show'); }
  function cargar(url) {
    pendiente = url;
    if (!frame || !abierta() || !url || url === urlActual) return;
    urlActual = url;
    load.hidden = false; frame.classList.remove('on');
    frame.src = url + (url.indexOf('?') >= 0 ? '&' : '?') + 'embed=1';
  }
  function recargar() { var u = urlActual; urlActual = ''; cargar(u || pendiente); }
  function aviso(tipo, html) {
    msg.innerHTML = '<div class="alert alert-' + tipo + ' py-2 mb-2 small">' + html + '</div>';
    if (tipo === 'success') setTimeout(function () { msg.innerHTML = ''; }, 6000);
  }
  function esc(t) { return String(t).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  if (modal) {
    modal.addEventListener('shown.bs.modal', function () { urlActual = ''; cargar(pendiente); });
    modal.addEventListener('hidden.bs.modal', function () {
      msg.innerHTML = '';
      if (huboCambios) location.reload();   // los KPIs y la actividad del hub se actualizan
    });
  }
  window.addEventListener('message', function (e) {
    if (e.origin !== location.origin || !e.data || e.data.tc !== 'embed' || !frame || e.source !== frame.contentWindow) return;
    var d = e.data;
    if (d.tipo === 'listo') { load.hidden = true; frame.classList.add('on'); }
    else if (d.tipo === 'enviando') { load.hidden = false; load.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Guardando…'; }
    else if (d.tipo === 'cerrar') { if (window.bootstrap) bootstrap.Modal.getOrCreateInstance(modal).hide(); }
    else if (d.tipo === 'sin-formulario') { load.hidden = true; frame.classList.add('on'); }
    else if (d.tipo === 'resultado') {
      load.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Cargando formulario…';
      var textos = (d.mensajes || []).map(function (m) { return esc(m.texto); }).join('<br>');
      if (d.ok) { huboCambios = true; aviso('success', '<i class="ti ti-check me-1"></i>' + (textos || 'Registro guardado.') + ' Puedes registrar otro.'); }
      else { aviso('danger', '<i class="ti ti-alert-triangle me-1"></i>' + (textos || 'No se pudo guardar. Revisa los campos.')); }
      recargar();
    }
  });
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
