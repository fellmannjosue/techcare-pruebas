/* agenda_moodle.js — <--- hecho por claude code (14-oct-2026): Dashboard de Agendas → "Publicar en Moodle" (pruebas).
   15-oct-2026: cursos AGRUPADOS por grado-sección con selección múltiple (marcar el grado = todas sus clases),
   grupo sugerido según el grado de la agenda y publicación curso por curso con avance.
   Config por data-* (#mda-config) + isla JSON (#mda-publicadas). Un solo global: AGENDA_MOODLE. */
(function () {
  'use strict';
  var cfg = document.getElementById('mda-config');
  if (!cfg) return;
  var PUB = {};
  try { PUB = JSON.parse(document.getElementById('mda-publicadas').textContent) || {}; } catch (e) { PUB = {}; }
  var modalEl = document.getElementById('modalMoodleAgenda');
  var form = document.getElementById('mda-form');
  var cont = document.getElementById('mda-grupos');
  var buscar = document.getElementById('mda-buscar');
  var cuenta = document.getElementById('mda-cuenta');
  var sug = document.getElementById('mda-sug');
  var inpImg = document.getElementById('mda-imagen');
  var prev = document.getElementById('mda-preview');
  var msg = document.getElementById('mda-msg');
  var btn = document.getElementById('mda-btn');
  var actual = null, publicando = false, peticion = 0;

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
      if (badge && p) {
        badge.innerHTML = '<i class="ti ti-check"></i> Moodle' + (p.ncursos > 1 ? ' · ' + p.ncursos : '');
        badge.title = 'Última publicación ' + p.fecha + (p.ncursos > 1 ? ' · en ' + p.ncursos + ' cursos' : ' en ' + p.curso);
      }
    });
  }
  pintar();
  if (window.jQuery) jQuery(document).on('draw.dt', pintar);

  /* ── Lista agrupada ───────────────────────────────────────────── */
  function marcados() { return Array.prototype.slice.call(cont.querySelectorAll('.mda-curso:checked')); }

  function refrescarGrupo(g) {
    var cajas = g.querySelectorAll('.mda-curso'), n = 0;
    cajas.forEach(function (c) { if (c.checked) n++; });
    var gc = g.querySelector('.mda-gchk');
    gc.checked = n > 0 && n === cajas.length;
    gc.indeterminate = n > 0 && n < cajas.length;
    g.querySelector('.mda-gnum').textContent = n ? n + '/' + cajas.length : cajas.length + ' clases';
    g.classList.toggle('mda-grupo--sel', n > 0);
  }
  function refrescarCuenta() {
    var n = marcados().length;
    cuenta.textContent = n === 1 ? '1 curso seleccionado' : n + ' cursos seleccionados';
    btn.innerHTML = '<i class="ti ti-send me-1"></i>' + (n > 1 ? 'Publicar en ' + n + ' cursos' : 'Publicar');
  }

  function construir(grupos, sugerido) {
    var html = '', areaAnt = null;
    grupos.forEach(function (g) {
      var area = g.area_nombre + (g.anio ? ' · ' + g.anio : '');
      if (area !== areaAnt) { if (areaAnt !== null) html += '</div>'; html += '<div class="mda-area"><div class="mda-area-tit">' + esc(area) + '</div>'; areaAnt = area; }
      var id = 'mda-g-' + g.key.replace(/[^A-Za-z0-9]/g, '_');
      html += '<div class="mda-grupo" data-key="' + esc(g.key) + '" data-busca="' + esc((g.area_nombre + ' ' + g.etiqueta).toLowerCase()) + '">' +
        '<div class="mda-ghead"><label class="form-check mb-0"><input type="checkbox" class="form-check-input mda-gchk" id="' + id + '">' +
        '<span class="form-check-label"><b>' + esc(g.etiqueta) + '</b></span></label>' +
        '<span class="mda-gnum">' + g.cursos.length + ' clases</span>' +
        '<button type="button" class="btn btn-sm btn-ghost-secondary btn-icon mda-gtoggle" title="Ver clases" aria-expanded="false"><i class="ti ti-chevron-down"></i></button></div>' +
        '<div class="mda-gbody" hidden>' + g.cursos.map(function (c) {
          return '<label class="form-check mda-cl" data-busca="' + esc(c.clase.toLowerCase()) + '"><input type="checkbox" class="form-check-input mda-curso" value="' + c.id + '" data-nombre="' + esc(c.nombre) + '">' +
            '<span class="form-check-label">' + esc(c.clase) + '</span></label>';
        }).join('') + '</div></div>';
    });
    if (areaAnt !== null) html += '</div>';
    cont.innerHTML = html || '<div class="text-muted small p-2">El usuario de Moodle no ve ningún curso.</div>';
    sug.classList.add('d-none');
    if (sugerido) {
      var g = cont.querySelector('.mda-grupo[data-key="' + sugerido + '"]');
      if (g) {
        g.querySelectorAll('.mda-curso').forEach(function (c) { c.checked = true; });
        abrir(g, true); refrescarGrupo(g);
        sug.innerHTML = '<i class="ti ti-sparkles me-1"></i>Se marcaron las clases de <b>' + esc(g.closest('.mda-area').querySelector('.mda-area-tit').textContent) +
          ' ' + esc(g.querySelector('.mda-ghead b').textContent) + '</b>, según el grado de la agenda. Puedes quitar o agregar.';
        sug.classList.remove('d-none');
        setTimeout(function () { cont.scrollTop = g.offsetTop - cont.offsetTop - 8; }, 50);
      }
    }
    refrescarCuenta();
  }

  function abrir(g, si) {
    g.querySelector('.mda-gbody').hidden = !si;
    var b = g.querySelector('.mda-gtoggle');
    b.setAttribute('aria-expanded', si ? 'true' : 'false');
    b.classList.toggle('mda-abierto', si);
  }

  cont.addEventListener('change', function (e) {
    var g = e.target.closest('.mda-grupo');
    if (!g) return;
    if (e.target.classList.contains('mda-gchk')) {
      g.querySelectorAll('.mda-curso').forEach(function (c) { if (!c.closest('.mda-cl').hidden) c.checked = e.target.checked; });
    }
    refrescarGrupo(g); refrescarCuenta();
  });
  cont.addEventListener('click', function (e) {
    var t = e.target.closest('.mda-gtoggle');
    if (t) { var g = t.closest('.mda-grupo'); abrir(g, g.querySelector('.mda-gbody').hidden); }
  });
  document.getElementById('mda-limpiar').addEventListener('click', function () {
    cont.querySelectorAll('.mda-curso').forEach(function (c) { c.checked = false; });
    cont.querySelectorAll('.mda-grupo').forEach(refrescarGrupo); refrescarCuenta();
  });

  /* Buscar: por grado ("1ero-1", "bach") muestra el grupo entero; por clase ("math") solo esas clases */
  buscar.addEventListener('input', function () {
    var q = buscar.value.trim().toLowerCase();
    cont.querySelectorAll('.mda-area').forEach(function (a) {
      var algo = false;
      a.querySelectorAll('.mda-grupo').forEach(function (g) {
        var porGrupo = !q || g.dataset.busca.indexOf(q) >= 0, alguna = false;
        g.querySelectorAll('.mda-cl').forEach(function (c) {
          var ve = porGrupo || c.dataset.busca.indexOf(q) >= 0;
          c.hidden = !ve; if (ve) alguna = true;
        });
        g.hidden = !alguna; if (alguna) algo = true;
        if (q && !porGrupo && alguna) abrir(g, true);
      });
      a.hidden = !algo;
    });
  });

  function cargarCursos(pk) {
    var yo = ++peticion;
    cont.innerHTML = '<div class="text-muted small p-2"><i class="ti ti-loader-2 mda-gira"></i> Cargando cursos de Moodle…</div>';
    fetch(cfg.dataset.urlCursos + '?agenda=' + encodeURIComponent(pk), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); }).then(function (d) {
        if (yo !== peticion) return;
        if (!d.ok) { cont.innerHTML = '<div class="text-danger small p-2">No se pudo conectar con Moodle.</div>'; aviso('err', esc(d.error)); return; }
        construir(d.grupos || [], d.sugerido || '');
      }).catch(function () { if (yo === peticion) aviso('err', 'Error de conexión al pedir los cursos.'); });
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('.btn-moodle-agenda');
    if (!b || publicando) return;
    actual = b;
    document.getElementById('mda-titulo').textContent = b.dataset.grado + ' · ' + b.dataset.semana;
    form.reset(); prev.classList.add('d-none'); prev.removeAttribute('src'); msg.className = 'mda-msg d-none';
    btn.disabled = false; buscar.value = '';
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

  /* Publica curso por curso (una petición cada uno): avance visible y un fallo no detiene a los demás */
  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (!actual || publicando) return;
    var sel = marcados();
    if (!sel.length || !inpImg.files.length) { aviso('err', 'Marca al menos un curso y elige la imagen.'); return; }
    var pk = actual.dataset.pk, url = cfg.dataset.urlPublicar.replace('/0/', '/' + pk + '/'), img = inpImg.files[0];
    var ok = 0, err = [], i = 0, ultimo = null;
    publicando = true; btn.disabled = true;

    function siguiente() {
      if (i >= sel.length) return fin();
      var c = sel[i++];
      aviso('info', '<i class="ti ti-loader-2 mda-gira"></i> Publicando ' + i + ' de ' + sel.length + ': <b>' + esc(c.dataset.nombre) + '</b>…');
      var fd = new FormData(); fd.append('curso', c.value); fd.append('imagen', img);
      fetch(url, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': cfg.dataset.csrf } })
        .then(function (r) { return r.json(); })
        .then(function (d) { if (d.ok) { ok++; ultimo = d; } else err.push([c.dataset.nombre, d.error]); })
        .catch(function () { err.push([c.dataset.nombre, 'Error de conexión']); })
        .then(siguiente);
    }
    function fin() {
      publicando = false; btn.disabled = false;
      if (ultimo) {
        var p = PUB[pk] || { ncursos: 0 };
        PUB[pk] = { fecha: ultimo.fecha, curso: ultimo.curso, ncursos: Math.max(p.ncursos || 0, ok) };
        pintar();
      }
      var html = ok ? '<b>Agenda publicada en ' + ok + (ok === 1 ? ' curso' : ' cursos') + '.</b>' : '';
      if (err.length) {
        html += (html ? '<br>' : '') + '<b>No se publicó en ' + err.length + ':</b><ul class="mda-errs">' +
          err.map(function (x) { return '<li>' + esc(x[0]) + ' — ' + esc(x[1]) + '</li>'; }).join('') + '</ul>';
      }
      aviso(err.length ? (ok ? 'warn' : 'err') : 'ok', html);
    }
    siguiente();
  });

  window.AGENDA_MOODLE = { publicadas: PUB };
})();
