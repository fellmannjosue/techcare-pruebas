/* mu_publicar.js — <--- hecho por claude code (15-oct-2026): pestaña Publicar de Moodle · Agendas.
   Cursos agrupados por grado-sección (MU_SELECTOR) y publicación curso por curso con avance. Un solo global: MU_PUBLICAR. */
(function () {
  'use strict';
  var cfg = document.getElementById('mu-config'), root = document.getElementById('mu-selector');
  if (!cfg || !root || !window.MU_SELECTOR) return;
  var esc = MU_SELECTOR.esc;
  var form = document.getElementById('mu-form'), btn = document.getElementById('mu-btn'), msg = document.getElementById('mu-msg');
  var inpImg = document.getElementById('mu-imagen'), alt = document.getElementById('mu-alt');
  var publicando = false;
  function aviso(tipo, html) { msg.className = 'mda-msg mda-msg--' + tipo; msg.innerHTML = html; }

  var SEL = MU_SELECTOR.montar(root, function (n) {
    btn.innerHTML = '<i class="ti ti-send me-1"></i>' + (n > 1 ? 'Publicar en ' + n + ' cursos' : 'Publicar en Moodle');
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
      return fetch(cfg.dataset.urlPublicar, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': cfg.dataset.csrf } })
        .then(function (r) { return r.json(); });
    }, function (i, total, nombre) {
      aviso('info', '<i class="ti ti-loader-2 mda-gira"></i> Publicando ' + i + ' de ' + total + ': <b>' + esc(nombre) + '</b>…');
    }, function (r) {
      publicando = false; btn.disabled = false;
      var s = MU_SELECTOR.resumen(r);
      aviso(s.tipo, s.html + (r.ok ? ' <a href="?tab=historial">Ver historial</a>' : ''));
    });
  });

  window.MU_PUBLICAR = { selector: SEL };
})();
