/* directorio_cards.js — <--- hecho por claude code (04-nov-2026): Directorio «Tarjetas por alumno» (Opción B).
   Lee la isla JSON #dir-data y pinta tarjetas con buscador + paginación propios. Un solo global: DIR_CARDS. */
(function () {
  'use strict';
  var dataEl = document.getElementById('dir-data');
  var grid = document.getElementById('dir-grid');
  if (!dataEl || !grid) return;

  var ALUMNOS = [];
  try { ALUMNOS = JSON.parse(dataEl.textContent) || []; } catch (e) { ALUMNOS = []; }

  var qEl = document.getElementById('dir-q');
  var countEl = document.getElementById('dir-count');
  var emptyEl = document.getElementById('dir-empty');
  var pagerEl = document.getElementById('dir-pager');
  var sizeEl = document.getElementById('dir-size');

  var pageSize = 24, page = 1, filtered = ALUMNOS;

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }

  function prog(grado) {
    var g = (grado || '').toLowerCase();
    if (g.indexOf('bachillerato') === 0) return 'bachillerato';
    if (g.indexOf('colegio') === 0) return 'colegio';
    if (g.indexOf('primaria') === 0) return 'primaria';
    if (g.indexOf('preescolar') === 0 || g.indexOf('prepa') === 0 || g.indexOf('kinder') === 0) return 'preescolar';
    return 'otro';
  }
  function iniciales(nombre) {
    var n = (nombre || '').trim();
    var ap = n, no = '';
    var i = n.indexOf(',');
    if (i >= 0) { ap = n.slice(0, i).trim(); no = n.slice(i + 1).trim(); }
    var a = (ap.split(/\s+/)[0] || '')[0] || '';
    var b = (no.split(/\s+/)[0] || '')[0] || '';
    return ((no ? b : '') + a).toUpperCase() || (a + '').toUpperCase() || '·';
  }
  var WA_SVG = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/></svg>';

  function cardHtml(a, idx) {
    var p = prog(a.grado);
    var phones = (a.moviles && a.moviles.length) ? a.moviles.map(function (m) {
      return '<div class="dir-phone">' +
        (m.label ? '<span class="dir-phone__label">' + esc(m.label) + '</span>' : '') +
        '<span class="dir-phone__num">' + esc(m.num) + '</span>' +
        '<a class="dir-wa" href="' + esc(m.wa) + '" target="_blank" rel="noopener">' + WA_SVG + 'WA</a></div>';
    }).join('') : '<div class="dir-nophone">Sin móvil registrado</div>';
    return '<div class="dir-card dir-prog-' + p + '">' +
      '<div class="dir-card__top"><span class="dir-av">' + esc(iniciales(a.nombre)) + '</span>' +
      '<span class="dir-card__id"><span class="dir-card__name">' + esc(a.nombre) + '</span>' +
      '<span class="dir-chip">' + esc(a.grado) + '</span></span>' +
      '<span class="dir-num">#' + (idx + 1) + '</span></div>' +
      '<div class="dir-phones">' + phones + '</div></div>';
  }

  function aplicarFiltro() {
    var q = (qEl && qEl.value || '').trim().toLowerCase();
    if (!q) { filtered = ALUMNOS; return; }
    filtered = ALUMNOS.filter(function (a) {
      if ((a.nombre || '').toLowerCase().indexOf(q) >= 0) return true;
      if ((a.grado || '').toLowerCase().indexOf(q) >= 0) return true;
      return (a.moviles || []).some(function (m) {
        return (m.num || '').toLowerCase().indexOf(q) >= 0 || (m.label || '').toLowerCase().indexOf(q) >= 0;
      });
    });
  }

  function render() {
    var total = filtered.length;
    var pages = Math.max(1, Math.ceil(total / pageSize));
    if (page > pages) page = pages;
    var ini = (page - 1) * pageSize, fin = Math.min(ini + pageSize, total);
    grid.innerHTML = filtered.slice(ini, fin).map(function (a, k) { return cardHtml(a, ini + k); }).join('');
    if (emptyEl) emptyEl.hidden = total !== 0;
    if (countEl) countEl.textContent = total ? ('Mostrando ' + (ini + 1) + '–' + fin + ' de ' + total) : '0 alumnos';
    if (pagerEl) {
      pagerEl.innerHTML = total > pageSize
        ? '<button type="button" data-pg="prev"' + (page <= 1 ? ' disabled' : '') + '>‹ Anterior</button>' +
          '<span class="dir-pager__info">Página ' + page + ' de ' + pages + '</span>' +
          '<button type="button" data-pg="next"' + (page >= pages ? ' disabled' : '') + '>Siguiente ›</button>'
        : '';
    }
  }

  var t = null;
  if (qEl) qEl.addEventListener('input', function () {
    clearTimeout(t); t = setTimeout(function () { page = 1; aplicarFiltro(); render(); }, 180);
  });
  if (sizeEl) sizeEl.addEventListener('change', function () { pageSize = parseInt(sizeEl.value, 10) || 24; page = 1; render(); });
  if (pagerEl) pagerEl.addEventListener('click', function (e) {
    var b = e.target.closest('[data-pg]'); if (!b) return;
    if (b.dataset.pg === 'prev' && page > 1) page--;
    else if (b.dataset.pg === 'next') page++;
    render(); window.scrollTo({ top: 0, behavior: 'smooth' });
  });

  aplicarFiltro(); render();
  window.DIR_CARDS = { render: render };
})();
