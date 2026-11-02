/* mu_publicar.js — <--- hecho por claude code (15-oct-2026): pestaña Publicar de Moodle · Agendas (Upload Moodle).
   Cursos agrupados por grado-sección (MU_SELECTOR) y publicación curso por curso con avance. Un solo global: MU_PUBLICAR.
   v3 (28-oct-2026): panel "elegir qué reemplazar en General" para UNO o VARIOS cursos. Con el grado completo lista
   cada clase que tenga imágenes en su General y se elige por curso (Agregar nueva / Reemplazar «…»). Mapa targetMap
   por curso; cada reemplazo adopta esa imagen como la agenda (luego se reemplaza sola). */
(function () {
  'use strict';
  var cfg = document.getElementById('mu-config'), root = document.getElementById('mu-selector');
  if (!cfg || !root || !window.MU_SELECTOR) return;
  var esc = MU_SELECTOR.esc;
  var form = document.getElementById('mu-form'), btn = document.getElementById('mu-btn'), msg = document.getElementById('mu-msg');
  var inpImg = document.getElementById('mu-imagen'), alt = document.getElementById('mu-alt');
  var panel = document.getElementById('mu-general'), panelBody = document.getElementById('mu-general-body');
  var publicando = false, generalCache = {}, targetMap = {}, renderToken = 0, debTimer = null;
  function aviso(tipo, html) { msg.className = 'mda-msg mda-msg--' + tipo; msg.innerHTML = html; }

  /* Nombre amable del curso a partir de "AAAA-Área-Clase-Grado-Sección" → "Clase · Grado-Sección". */
  function etiquetaCurso(full) {
    var m = /^\d{4}-[^-]+-(.+)-([^-]+)-([^-]+)$/.exec(full || '');
    return m ? (m[1] + ' · ' + m[2] + '-' + m[3]) : (full || '');
  }

  /* Imágenes reemplazables de la sección General de un curso (cacheado). */
  function pedirGeneral(cursoId) {
    if (generalCache[cursoId]) return Promise.resolve(generalCache[cursoId]);
    return fetch(cfg.dataset.urlGeneral + '?curso=' + encodeURIComponent(cursoId), { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = (d.ok && d.items ? d.items : []).filter(function (it) { return it.reemplazable; });
        generalCache[cursoId] = items;
        return items;
      })
      .catch(function () { generalCache[cursoId] = []; return []; });
  }

  function opcion(cursoId, val, visual, titulo, sub, checked) {
    return '<label class="mu-gen-op"><input type="radio" name="mu-target-' + esc(cursoId) + '" value="' + esc(val) + '"' +
      (checked ? ' checked' : '') + '>' +
      '<span class="mu-gen-ico">' + visual + '</span>' +
      '<span class="mu-gen-txt"><b>' + titulo + '</b><small class="text-muted d-block">' + esc(sub) + '</small></span></label>';
  }

  function bloqueOpts(cursoId, items) {
    var html = '<div class="mu-gen-opts">';
    html += opcion(cursoId, '0', '<i class="ti ti-plus"></i>', 'Agregar como agenda nueva',
      'Se coloca la agenda sin tocar lo que ya hay.', (targetMap[cursoId] || '0') === '0');
    items.forEach(function (it) {
      var vis = it.miniatura ? '<img src="' + it.miniatura + '" class="mu-gen-thumb" alt="">'
                             : '<span class="mu-gen-thumb mu-gen-sin"><i class="ti ti-photo"></i></span>';
      var badge = it.esagenda ? ' <span class="badge bg-blue-lt text-blue ms-1">Agenda actual</span>' : '';
      html += opcion(cursoId, String(it.cmid), vis, 'Reemplazar «' + esc(it.nombre) + '»' + badge, it.archivo,
        targetMap[cursoId] === String(it.cmid));
    });
    return html + '</div>';
  }

  function render() {
    var marc = Array.prototype.slice.call(root.querySelectorAll('.mda-curso:checked'));
    if (!marc.length) { panel.hidden = true; panelBody.innerHTML = ''; return; }
    // Limpiar del mapa los cursos que ya no están marcados.
    var ids = marc.map(function (c) { return c.value; });
    Object.keys(targetMap).forEach(function (k) { if (ids.indexOf(k) < 0) delete targetMap[k]; });

    panel.hidden = false;
    panelBody.innerHTML = '<div class="text-muted small"><i class="ti ti-loader-2 mda-gira"></i> Revisando qué hay en General…</div>';
    var token = ++renderToken;
    Promise.all(marc.map(function (c) {
      return pedirGeneral(c.value).then(function (items) { return { id: c.value, nombre: c.dataset.nombre, items: items }; });
    })).then(function (res) {
      if (token !== renderToken) return;   // la selección cambió mientras cargaba
      var conImgs = res.filter(function (r) { return r.items.length; });
      if (!conImgs.length) {
        panelBody.innerHTML = '<div class="text-muted small">Ninguno de los cursos seleccionados tiene imágenes en General para reemplazar. Se agregará la agenda como nueva.</div>';
        return;
      }
      var multi = res.length > 1, html = '';
      conImgs.forEach(function (r) {
        if (multi) {
          html += '<div class="mu-gen-curso"><div class="mu-gen-curso-tit"><i class="ti ti-book me-1"></i>' +
            esc(etiquetaCurso(r.nombre)) + '</div>' + bloqueOpts(r.id, r.items) + '</div>';
        } else {
          html += bloqueOpts(r.id, r.items);
        }
      });
      if (multi) {
        html = '<div class="text-muted small mb-2">' + conImgs.length + ' de ' + res.length +
          ' clases tienen imágenes en General. El resto se agrega como nueva.</div>' + html;
      }
      panelBody.innerHTML = html;
    });
  }

  function programarRender() { clearTimeout(debTimer); debTimer = setTimeout(render, 150); }

  panelBody.addEventListener('change', function (e) {
    var m = /^mu-target-(.+)$/.exec(e.target.name || '');
    if (m) targetMap[m[1]] = e.target.value;
  });

  var SEL = MU_SELECTOR.montar(root, function (n) {
    btn.innerHTML = '<i class="ti ti-send me-1"></i>' + (n > 1 ? 'Publicar en ' + n + ' cursos' : 'Publicar en Moodle');
    programarRender();
  });
  var grupos = [];
  try { grupos = JSON.parse(document.getElementById('mu-grupos').textContent) || []; } catch (e) { grupos = []; }
  SEL.cargar(grupos, '');

  form.addEventListener('submit', function (e) {
    e.preventDefault();
    if (publicando) return;
    var sel = SEL.marcados();
    if (!sel.length || !inpImg.files.length) { aviso('err', 'Marca al menos un curso y elige la imagen.'); return; }
    var img = inpImg.files[0], texto = alt.value;
    publicando = true; btn.disabled = true;
    MU_SELECTOR.publicarEnSerie(sel, function (cursoId) {
      var fd = new FormData(); fd.append('curso', cursoId); fd.append('imagen', img); fd.append('alt', texto);
      var t = targetMap[cursoId];
      if (t && t !== '0') fd.append('target', t);   // reemplazar la imagen elegida de ESE curso
      return fetch(cfg.dataset.urlPublicar, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': cfg.dataset.csrf } })
        .then(function (r) { return r.json(); });
    }, function (i, total, nombre) {
      aviso('info', '<i class="ti ti-loader-2 mda-gira"></i> Publicando ' + i + ' de ' + total + ': <b>' + esc(nombre) + '</b>…');
    }, function (r) {
      publicando = false; btn.disabled = false;
      // Un curso que se reemplazó ya es "agenda actual": limpiar su caché para reflejarlo si se vuelve a abrir.
      generalCache = {};
      var s = MU_SELECTOR.resumen(r);
      aviso(s.tipo, s.html + (r.ok ? ' <a href="?tab=historial">Ver historial</a>' : ''));
    });
  });

  window.MU_PUBLICAR = { selector: SEL };
})();
