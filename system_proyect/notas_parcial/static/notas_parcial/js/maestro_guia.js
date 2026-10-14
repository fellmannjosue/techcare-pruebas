/* maestro_guia.js — <--- hecho por claude code (13-oct-2026)
   Pantalla del coordinador: botón "Maestro guía" por grado-sección. Guarda vía POST JSON (maestro-guia/).
   Config por data-* (#guia-notas-config) + isla JSON (#guias-notas). Un solo global: MAESTRO_GUIA. */
(function () {
  'use strict';
  var cfg = document.getElementById('guia-notas-config');
  if (!cfg) return;
  var GUIAS = {};
  try { GUIAS = JSON.parse(document.getElementById('guias-notas').textContent) || {}; } catch (e) { GUIAS = {}; }
  var modalEl = document.getElementById('modalMaestroGuia');
  var inp = document.getElementById('guia-nombre-inp');
  var err = document.getElementById('guia-err');
  var actual = null;

  function pintar(ctrl) {
    var n = GUIAS[ctrl.dataset.grado + '|' + ctrl.dataset.seccion] || '';
    var b = ctrl.querySelector('.btn-guia');
    b.querySelector('.lbl').textContent = n ? 'Guía: ' + n : 'Asignar maestro guía';
    b.className = 'btn btn-sm btn-guia ' + (n ? 'btn-outline-primary' : 'btn-outline-secondary');
    b.title = n ? 'Maestro guía (firma del PDF): ' + n : 'Sin maestro guía: el PDF sale con la línea en blanco';
  }
  function mostrar() {
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl).show();
    else if (window.jQuery && jQuery.fn.modal) jQuery(modalEl).modal('show');
  }
  function ocultar() {
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl).hide();
    else if (window.jQuery && jQuery.fn.modal) jQuery(modalEl).modal('hide');
  }
  document.querySelectorAll('.guia-ctrl').forEach(function (ctrl) {
    pintar(ctrl);
    ctrl.querySelector('.btn-guia').addEventListener('click', function () {
      actual = ctrl;
      document.getElementById('guia-grupo-lbl').textContent = ctrl.dataset.grado + (ctrl.dataset.seccion ? ' ' + ctrl.dataset.seccion : '');
      inp.value = GUIAS[ctrl.dataset.grado + '|' + ctrl.dataset.seccion] || '';
      err.classList.add('d-none');
      mostrar();
      setTimeout(function () { inp.focus(); }, 300);
    });
  });
  function guardar(nombre) {
    if (!actual) return;
    fetch(cfg.dataset.url, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.dataset.csrf },
      body: JSON.stringify({ area: cfg.dataset.area, anio: cfg.dataset.anio, grado: actual.dataset.grado, seccion: actual.dataset.seccion, nombre: nombre })
    }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { err.textContent = d.error || 'No se pudo guardar.'; err.classList.remove('d-none'); return; }
      var k = actual.dataset.grado + '|' + actual.dataset.seccion;
      if (d.nombre) GUIAS[k] = d.nombre; else delete GUIAS[k];
      // el mismo grado-sección puede aparecer en más de una barra
      document.querySelectorAll('.guia-ctrl').forEach(function (c) { if (c.dataset.grado + '|' + c.dataset.seccion === k) pintar(c); });
      ocultar();
    }).catch(function () { err.textContent = 'Error de conexión.'; err.classList.remove('d-none'); });
  }
  document.getElementById('guia-guardar').addEventListener('click', function () {
    var v = inp.value.trim();
    if (v.length < 3) { err.textContent = 'Escribe el nombre del maestro guía.'; err.classList.remove('d-none'); return; }
    guardar(v);
  });
  document.getElementById('guia-quitar').addEventListener('click', function () { guardar(''); });
  inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); document.getElementById('guia-guardar').click(); } });
  window.MAESTRO_GUIA = { guias: GUIAS };
})();
