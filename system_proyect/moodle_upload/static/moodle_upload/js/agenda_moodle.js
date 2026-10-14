/* agenda_moodle.js — <--- hecho por claude code (14-oct-2026): Dashboard de Agendas → "Publicar en Moodle" (pruebas).
   Config por data-* (#mda-config) + isla JSON (#mda-publicadas). Un solo global: AGENDA_MOODLE. */
(function () {
  'use strict';
  var cfg = document.getElementById('mda-config');
  if (!cfg) return;
  var PUB = {};
  try { PUB = JSON.parse(document.getElementById('mda-publicadas').textContent) || {}; } catch (e) { PUB = {}; }
  var modalEl = document.getElementById('modalMoodleAgenda');
  var form = document.getElementById('mda-form');
  var selCurso = document.getElementById('mda-curso');
  var inpImg = document.getElementById('mda-imagen');
  var prev = document.getElementById('mda-preview');
  var msg = document.getElementById('mda-msg');
  var btn = document.getElementById('mda-btn');
  var actual = null, cursosCargados = false;

  function modal(accion) {
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl)[accion]();
    else if (window.jQuery && jQuery.fn.modal) jQuery(modalEl).modal(accion);
  }
  function aviso(tipo, html) { msg.className = 'mda-msg mda-msg--' + tipo; msg.innerHTML = html; }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }

  /* Marca "Moodle ✓" en las filas ya publicadas (y al redibujar la tabla) */
  function pintar() {
    document.querySelectorAll('.btn-moodle-agenda').forEach(function (b) {
      var p = PUB[b.dataset.pk];
      b.classList.toggle('mda-hecha', !!p);
      var badge = b.parentNode.querySelector('.mda-badge');
      if (p && !badge) { badge = document.createElement('span'); badge.className = 'badge mda-badge'; b.parentNode.appendChild(badge); }
      if (badge && p) { badge.innerHTML = '<i class="ti ti-check"></i> Moodle'; badge.title = 'Publicada ' + p.fecha + ' en ' + p.curso + (p.n > 1 ? ' (' + p.n + ' veces)' : ''); }
    });
  }
  pintar();
  if (window.jQuery) jQuery(document).on('draw.dt', pintar);

  function cargarCursos() {
    if (cursosCargados) return;
    fetch(cfg.dataset.urlCursos, { credentials: 'same-origin' }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { selCurso.innerHTML = '<option value="">No se pudo conectar con Moodle</option>'; aviso('err', esc(d.error)); return; }
      selCurso.innerHTML = '<option value="">— Elige el curso —</option>' + d.cursos.map(function (c) {
        return '<option value="' + c.id + '">' + esc(c.nombre) + (c.corto && c.corto !== c.nombre ? ' · ' + esc(c.corto) : '') + '</option>';
      }).join('');
      var ult = null; try { ult = localStorage.getItem('mda-curso'); } catch (e) {}
      if (ult && selCurso.querySelector('option[value="' + ult + '"]')) selCurso.value = ult;
      cursosCargados = true;
    }).catch(function () { aviso('err', 'Error de conexión al pedir los cursos.'); });
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('.btn-moodle-agenda');
    if (!b) return;
    actual = b;
    document.getElementById('mda-titulo').textContent = b.dataset.grado + ' · ' + b.dataset.semana;
    form.reset(); prev.classList.add('d-none'); prev.removeAttribute('src'); msg.className = 'mda-msg d-none';
    btn.disabled = false;
    var p = PUB[b.dataset.pk];
    if (p) aviso('info', 'Ya se publicó el ' + esc(p.fecha) + ' en <b>' + esc(p.curso) + '</b>. Si publicas otra vez, <b>se reemplaza</b>.');
    cargarCursos();
    modal('show');
  });

  inpImg.addEventListener('change', function () {
    var f = inpImg.files && inpImg.files[0];
    if (!f) { prev.classList.add('d-none'); return; }
    prev.src = URL.createObjectURL(f); prev.classList.remove('d-none');
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!actual) return;
    if (!selCurso.value || !inpImg.files.length) { aviso('err', 'Elige el curso y la imagen.'); return; }
    var fd = new FormData(); fd.append('curso', selCurso.value); fd.append('imagen', inpImg.files[0]);
    try { localStorage.setItem('mda-curso', selCurso.value); } catch (er) {}
    btn.disabled = true; aviso('info', '<i class="ti ti-loader-2 mda-gira"></i> Publicando en Moodle…');
    fetch(cfg.dataset.urlPublicar.replace('/0/', '/' + actual.dataset.pk + '/'), {
      method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': cfg.dataset.csrf }
    }).then(function (r) { return r.json(); }).then(function (d) {
      btn.disabled = false;
      if (!d.ok) { aviso('err', '<b>No se publicó:</b> ' + esc(d.error)); return; }
      var prev2 = PUB[actual.dataset.pk];
      PUB[actual.dataset.pk] = { fecha: d.fecha, curso: d.curso, n: (prev2 ? prev2.n : 0) + 1 };
      pintar();
      aviso('ok', '<b>' + (d.creada ? 'Agenda publicada' : 'Agenda reemplazada') + '</b> en «' + esc(d.curso) + '». ' +
        (d.url ? '<a href="' + esc(d.url) + '" target="_blank" rel="noopener">Abrir el curso</a>' : ''));
    }).catch(function () { btn.disabled = false; aviso('err', 'Error de conexión.'); });
  });

  window.AGENDA_MOODLE = { publicadas: PUB };
})();
