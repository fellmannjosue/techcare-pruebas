/* mu_selector.js — <--- hecho por claude code (15-oct-2026): selector de cursos de Moodle AGRUPADO por grado-sección.
   Marcar el grado = todas sus clases; flecha para ver/quitar clases; buscador por grado o por clase; grupo sugerido.
   Lo usan agenda_moodle.js (Dashboard de Agendas) y mu_publicar.js (pestaña Publicar). Un solo global: MU_SELECTOR. */
window.MU_SELECTOR = (function () {
  'use strict';
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }

  function montar(root, alCambiar) {
    var cont = root.querySelector('.mda-grupos'), buscar = root.querySelector('.mda-buscar'),
        cuenta = root.querySelector('.mda-cuenta-txt'), sug = root.querySelector('.mda-sug');

    function marcados() { return Array.prototype.slice.call(cont.querySelectorAll('.mda-curso:checked')); }
    function refrescarGrupo(g) {
      var cajas = g.querySelectorAll('.mda-curso'), n = 0;
      cajas.forEach(function (c) { if (c.checked) n++; });
      var gc = g.querySelector('.mda-gchk');
      gc.checked = n > 0 && n === cajas.length;
      gc.indeterminate = n > 0 && n < cajas.length;
      g.querySelector('.mda-gnum').textContent = n ? n + '/' + cajas.length : cajas.length + (cajas.length === 1 ? ' clase' : ' clases');
      g.classList.toggle('mda-grupo--sel', n > 0);
    }
    function refrescarCuenta() {
      var n = marcados().length;
      cuenta.textContent = n === 1 ? '1 curso seleccionado' : n + ' cursos seleccionados';
      if (alCambiar) alCambiar(n);
    }
    function abrir(g, si) {
      g.querySelector('.mda-gbody').hidden = !si;
      var b = g.querySelector('.mda-gtoggle');
      b.setAttribute('aria-expanded', si ? 'true' : 'false');
      b.classList.toggle('mda-abierto', si);
    }
    function vaciar(html) { cont.innerHTML = '<div class="small p-2">' + html + '</div>'; sug.classList.add('d-none'); refrescarCuenta(); }

    function cargar(grupos, sugerido) {
      var html = '', areaAnt = null;
      buscar.value = '';
      (grupos || []).forEach(function (g) {
        var area = g.area_nombre + (g.anio ? ' · ' + g.anio : '');
        if (area !== areaAnt) { if (areaAnt !== null) html += '</div>'; html += '<div class="mda-area"><div class="mda-area-tit">' + esc(area) + '</div>'; areaAnt = area; }
        html += '<div class="mda-grupo" data-key="' + esc(g.key) + '" data-busca="' + esc((g.area_nombre + ' ' + g.etiqueta).toLowerCase()) + '">' +
          '<div class="mda-ghead"><label class="form-check mb-0"><input type="checkbox" class="form-check-input mda-gchk">' +
          '<span class="form-check-label"><b>' + esc(g.etiqueta) + '</b></span></label>' +
          '<span class="mda-gnum"></span>' +
          '<button type="button" class="btn btn-sm btn-ghost-secondary btn-icon mda-gtoggle" title="Ver clases" aria-expanded="false"><i class="ti ti-chevron-down"></i></button></div>' +
          '<div class="mda-gbody" hidden>' + g.cursos.map(function (c) {
            return '<label class="form-check mda-cl" data-busca="' + esc(c.clase.toLowerCase()) + '"><input type="checkbox" class="form-check-input mda-curso" value="' + c.id + '" data-nombre="' + esc(c.nombre) + '">' +
              '<span class="form-check-label">' + esc(c.clase) + '</span></label>';
          }).join('') + '</div></div>';
      });
      if (areaAnt !== null) html += '</div>';
      cont.innerHTML = html || '<div class="text-muted small p-2">El usuario de Moodle no ve ningún curso.</div>';
      cont.querySelectorAll('.mda-grupo').forEach(refrescarGrupo);
      sug.classList.add('d-none');
      var g = sugerido ? cont.querySelector('.mda-grupo[data-key="' + sugerido + '"]') : null;
      if (g) {
        g.querySelectorAll('.mda-curso').forEach(function (c) { c.checked = true; });
        abrir(g, true); refrescarGrupo(g);
        sug.innerHTML = '<i class="ti ti-sparkles me-1"></i>Se marcaron las clases de <b>' + esc(g.closest('.mda-area').querySelector('.mda-area-tit').textContent) +
          ' ' + esc(g.querySelector('.mda-ghead b').textContent) + '</b>, según el grado de la agenda. Puedes quitar o agregar.';
        sug.classList.remove('d-none');
        setTimeout(function () { cont.scrollTop = g.offsetTop - cont.offsetTop - 8; }, 50);
      }
      refrescarCuenta();
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
    root.querySelector('.mda-limpiar').addEventListener('click', function () {
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

    return { cargar: cargar, marcados: marcados, vaciar: vaciar };
  }

  /* Publica curso por curso (una petición cada uno): avance visible y un fallo no detiene a los demás.
     enviar(cursoId) → Promise<{ok, error?, ...}>;  avance(i, total, nombre);  fin({ok, err:[[nombre, error]], ultimo}) */
  function publicarEnSerie(cajas, enviar, avance, fin) {
    var ok = 0, err = [], i = 0, ultimo = null;
    (function siguiente() {
      if (i >= cajas.length) return fin({ ok: ok, err: err, ultimo: ultimo });
      var c = cajas[i++];
      avance(i, cajas.length, c.dataset.nombre);
      enviar(c.value).then(function (d) { if (d && d.ok) { ok++; ultimo = d; } else err.push([c.dataset.nombre, (d && d.error) || 'Error']); })
        .catch(function () { err.push([c.dataset.nombre, 'Error de conexión']); })
        .then(siguiente);
    })();
  }

  function resumen(r) {
    var html = r.ok ? '<b>Publicada en ' + r.ok + (r.ok === 1 ? ' curso' : ' cursos') + '.</b>' : '';
    if (r.err.length) {
      html += (html ? '<br>' : '') + '<b>No se publicó en ' + r.err.length + ':</b><ul class="mda-errs">' +
        r.err.map(function (x) { return '<li>' + esc(x[0]) + ' — ' + esc(x[1]) + '</li>'; }).join('') + '</ul>';
    }
    return { tipo: r.err.length ? (r.ok ? 'warn' : 'err') : 'ok', html: html };
  }

  return { montar: montar, publicarEnSerie: publicarEnSerie, resumen: resumen, esc: esc };
})();
