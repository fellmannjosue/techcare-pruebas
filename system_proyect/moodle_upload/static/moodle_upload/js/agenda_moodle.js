/* agenda_moodle.js — <--- hecho por claude code (14-oct-2026): Dashboard de Agendas → "Publicar en Moodle" (pruebas).
   15-oct-2026: cursos agrupados por grado-sección con selección múltiple (componente MU_SELECTOR, mu_selector.js),
   grupo sugerido según el grado de la agenda y publicación curso por curso con avance.
   Config por data-* (#mda-config) + isla JSON (#mda-publicadas). Un solo global: AGENDA_MOODLE. */
(function () {
  'use strict';
  var cfg = document.getElementById('mda-config');
  if (!cfg || !window.MU_SELECTOR) return;
  var esc = MU_SELECTOR.esc;
  var PUB = {};
  try { PUB = JSON.parse(document.getElementById('mda-publicadas').textContent) || {}; } catch (e) { PUB = {}; }
  var modalEl = document.getElementById('modalMoodleAgenda');
  var form = document.getElementById('mda-form');
  var inpImg = document.getElementById('mda-imagen');
  var prev = document.getElementById('mda-preview');
  var msg = document.getElementById('mda-msg');
  var btn = document.getElementById('mda-btn');
  var actual = null, publicando = false, peticion = 0;

  var SEL = MU_SELECTOR.montar(document.getElementById('mda-selector'), function (n) {
    btn.innerHTML = '<i class="ti ti-send me-1"></i>' + (n > 1 ? 'Publicar en ' + n + ' cursos' : 'Publicar');
  });

  function modal(accion) {
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(modalEl)[accion]();
    else if (window.jQuery && jQuery.fn.modal) jQuery(modalEl).modal(accion);
  }
  function aviso(tipo, html) { msg.className = 'mda-msg mda-msg--' + tipo; msg.innerHTML = html; }

  /* Marca "Moodle ✓" en las filas ya publicadas (y al redibujar la tabla) */
  function pintar() {
    document.querySelectorAll('.btn-moodle-agenda').forEach(function (b) {
      var p = PUB[b.dataset.pk];
      b.classList.toggle('mda-hecha', !!p);
      var badge = b.parentNode.querySelector('.mda-badge');
      if (p && !badge) { badge = document.createElement('span'); badge.className = 'badge mda-badge'; b.parentNode.appendChild(badge); }
      if (badge && p) {
        badge.innerHTML = '<i class="ti ti-check"></i> Moodle' + (p.ncursos > 1 ? ' · ' + p.ncursos : '');
        badge.title = 'Última publicación ' + p.fecha + (p.ncursos > 1 ? ' · en ' + p.ncursos + ' cursos' : ' en ' + p.curso);
      }
    });
  }
  pintar();
  if (window.jQuery) jQuery(document).on('draw.dt', pintar);

  function cargarCursos(pk) {
    var yo = ++peticion;
    SEL.vaciar('<span class="text-muted"><i class="ti ti-loader-2 mda-gira"></i> Cargando cursos de Moodle…</span>');
    fetch(cfg.dataset.urlCursos + '?agenda=' + encodeURIComponent(pk), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); }).then(function (d) {
        if (yo !== peticion) return;
        if (!d.ok) { SEL.vaciar('<span class="text-danger">No se pudo conectar con Moodle.</span>'); aviso('err', esc(d.error)); return; }
        SEL.cargar(d.grupos || [], d.sugerido || '');
      }).catch(function () { if (yo === peticion) aviso('err', 'Error de conexión al pedir los cursos.'); });
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('.btn-moodle-agenda');
    if (!b || publicando) return;
    actual = b;
    document.getElementById('mda-titulo').textContent = b.dataset.grado + ' · ' + b.dataset.semana;
    form.reset(); prev.classList.add('d-none'); prev.removeAttribute('src'); msg.className = 'mda-msg d-none';
    btn.disabled = false;
    var p = PUB[b.dataset.pk];
    if (p) aviso('info', 'Ya se publicó el ' + esc(p.fecha) + (p.ncursos > 1 ? ' en <b>' + p.ncursos + ' cursos</b>' : ' en <b>' + esc(p.curso) + '</b>') + '. Si publicas otra vez, <b>se reemplaza</b>.');
    cargarCursos(b.dataset.pk);
    modal('show');
  });

  inpImg.addEventListener('change', function () {
    var f = inpImg.files && inpImg.files[0];
    if (!f) { prev.classList.add('d-none'); return; }
    prev.src = URL.createObjectURL(f); prev.classList.remove('d-none');
  });

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!actual || publicando) return;
    var sel = SEL.marcados();
    if (!sel.length || !inpImg.files.length) { aviso('err', 'Marca al menos un curso y elige la imagen.'); return; }
    var pk = actual.dataset.pk, url = cfg.dataset.urlPublicar.replace('/0/', '/' + pk + '/'), img = inpImg.files[0];
    publicando = true; btn.disabled = true;
    MU_SELECTOR.publicarEnSerie(sel, function (cursoId) {
      var fd = new FormData(); fd.append('curso', cursoId); fd.append('imagen', img);
      return fetch(url, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': cfg.dataset.csrf } })
        .then(function (r) { return r.json(); });
    }, function (i, total, nombre) {
      aviso('info', '<i class="ti ti-loader-2 mda-gira"></i> Publicando ' + i + ' de ' + total + ': <b>' + esc(nombre) + '</b>…');
    }, function (r) {
      publicando = false; btn.disabled = false;
      if (r.ultimo) {
        var p = PUB[pk] || { ncursos: 0 };
        PUB[pk] = { fecha: r.ultimo.fecha, curso: r.ultimo.curso, ncursos: Math.max(p.ncursos || 0, r.ok) };
        pintar();
      }
      var s = MU_SELECTOR.resumen(r);
      aviso(s.tipo, s.html);
    });
  });

  window.AGENDA_MOODLE = { publicadas: PUB };
})();
