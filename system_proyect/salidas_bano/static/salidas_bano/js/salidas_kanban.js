/* salidas_kanban.js — <--- hecho por claude code (04-nov-2026): vista Tablero (Kanban) de Salidas al Baño.
   Reusa window._SB (datos + endpoints de index.js). Un solo global: SB_KANBAN.
   3 columnas: En clase / Afuera / Regresó. Arrastrar o botón:
   En clase/Regresó → Afuera = registra salida (pide clase); Afuera → Regresó = marca regreso.
   La tabla original queda intacta; un interruptor alterna entre ambas vistas. */
(function () {
  'use strict';
  var SB = window._SB; if (!SB) return;
  var board = document.getElementById('sbk-board'); if (!board) return;
  var gradosWrap = document.getElementById('sbk-grados');
  var seccWrap  = document.getElementById('sbk-secciones');
  var secWrapBox = document.getElementById('sbk-sec-wrap');
  var toggle    = document.getElementById('sb-view-toggle');
  var viewTabla = document.getElementById('sb-view-tabla');
  var viewKanban = document.getElementById('sb-view-kanban');

  var alumnosPorGrado = SB.alumnosPorGrado || {};
  var clasesPorGrado  = SB.clasesPorGrado  || {};
  SB.salidasHoy = SB.salidasHoy || {};
  var grados = Object.keys(alumnosPorGrado).sort();
  var gradoSel = grados[0] || '';
  var seccSel  = '';   // '' = todas

  function esc(s) { return String(s == null ? '' : s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }
  function ahora() { var d = new Date(); return ('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2); }
  function salDe(iid) { return SB.salidasHoy[String(iid)] || null; }
  function estadoDe(iid) { var s = salDe(iid); if (!s) return 'clase'; if (!s.last_hora_regreso) return 'afuera'; return 'regreso'; }
  function dotDe(iid) { var s = salDe(iid); return (s && s.semaforo) ? s.semaforo : 'none'; }

  function seccionesDe(grado) {
    var set = {}, out = [];
    (alumnosPorGrado[grado] || []).forEach(function (a) { var g = (a.grupo || '').trim(); if (g && !set[g]) { set[g] = 1; out.push(g); } });
    out.sort(); return out;
  }

  function pintarGrados() {
    gradosWrap.innerHTML = grados.map(function (g) {
      return '<button type="button" class="btn btn-outline-primary' + (g === gradoSel ? ' active' : '') + '" data-g="' + esc(g) + '">' + esc(g) + '</button>';
    }).join('');
  }
  function pintarSecciones() {
    var secs = seccionesDe(gradoSel);
    if (!secs.length) { if (secWrapBox) secWrapBox.style.display = 'none'; return; }
    if (secWrapBox) secWrapBox.style.display = '';
    var html = '<span class="chip' + (seccSel === '' ? ' on' : '') + '" data-s="">Todas</span>';
    html += secs.map(function (s) { return '<span class="chip' + (seccSel === s ? ' on' : '') + '" data-s="' + esc(s) + '">' + esc(s) + '</span>'; }).join('');
    seccWrap.innerHTML = html;
  }

  function cardHtml(a) {
    var iid = a.ingr_egr_id, est = estadoDe(iid), s = salDe(iid), sub = '', act = '';
    if (est === 'afuera') sub = '<div class="sbk-card__sub">Salió <b>' + esc(s.last_hora_salida) + '</b> · ' + esc(s.last_clase) + '</div>';
    else if (est === 'regreso') sub = '<div class="sbk-card__sub">Regresó <b>' + esc(s.last_hora_regreso) + '</b> · ' + (s.count > 1 ? ('<b>' + s.count + '</b> salidas hoy') : '1 salida hoy') + '</div>';

    if (est === 'clase') act = '<button type="button" class="btn btn-sm btn-outline-warning" data-act="salir">Salió →</button>';
    else if (est === 'afuera') act = '<button type="button" class="btn btn-sm btn-outline-success" data-act="regreso"><i class="ti ti-check me-1"></i>Regresó</button>';
    else act = '<button type="button" class="btn btn-sm btn-outline-warning" data-act="salir">Salió otra vez</button>';

    return '<div class="sbk-card" draggable="true" data-iid="' + iid + '" data-est="' + est + '"' +
           ' data-grupo="' + esc(a.grupo || '') + '" data-nombre="' + esc(a.nombre) + '" data-grado="' + esc(a.grado) + '">' +
      '<div class="sbk-card__top"><span class="sbk-dot sbk-dot--' + dotDe(iid) + '"></span>' +
      '<span class="sbk-card__name">' + esc(a.nombre) + (a.grupo ? (' <span class="text-muted" style="font-weight:400">· ' + esc(a.grupo) + '</span>') : '') + '</span></div>' +
      sub + '<div class="sbk-card__act">' + act + '</div></div>';
  }

  function render() {
    var cols = { clase: [], afuera: [], regreso: [] };
    (alumnosPorGrado[gradoSel] || []).forEach(function (a) {
      if (seccSel && (a.grupo || '') !== seccSel) return;
      cols[estadoDe(a.ingr_egr_id)].push(a);
    });
    var defs = [['clase', 'En clase', 'sbk-col--clase'], ['afuera', 'Afuera', 'sbk-col--afuera'], ['regreso', 'Regresó', 'sbk-col--regreso']];
    board.innerHTML = defs.map(function (d) {
      var items = cols[d[0]];
      var body = items.length ? items.map(cardHtml).join('') : '<div class="sbk-empty">—</div>';
      return '<div class="sbk-col ' + d[2] + '" data-col="' + d[0] + '"><div class="sbk-col__h">' + d[1] +
             '<span class="n">' + items.length + '</span></div><div class="sbk-col__body">' + body + '</div></div>';
    }).join('');
  }

  // ── acciones (reusan los endpoints de la tabla) ──
  function headers() { return { 'Content-Type': 'application/json', 'X-CSRFToken': SB.csrfToken }; }

  function abrirPicker(card) {
    if (card.querySelector('.sbk-pick')) return;
    var clases = clasesPorGrado[card.dataset.grado] || [];
    if (!clases.length) { alert('No hay clases/maestros configurados para ' + card.dataset.grado + '. Configúralas en «Maestros – Clases».'); return; }
    var actBox = card.querySelector('.sbk-card__act'); if (actBox) actBox.style.display = 'none';
    var opts = clases.map(function (c) { return '<option value="' + esc(c.value) + '">' + esc(c.label) + '</option>'; }).join('');
    var div = document.createElement('div'); div.className = 'sbk-pick';
    div.innerHTML = '<select class="form-select form-select-sm">' + opts + '</select>' +
      '<div class="sbk-pick__row"><button type="button" class="btn btn-sm btn-warning" data-act="confirmar">Confirmar salida</button>' +
      '<button type="button" class="btn btn-sm btn-ghost-secondary" data-act="cancelar">Cancelar</button></div>';
    card.appendChild(div);
  }

  function guardarSalida(card, clase) {
    var iid = card.dataset.iid;
    card.style.pointerEvents = 'none';
    fetch(SB.urlGuardar, { method: 'POST', headers: headers(), body: JSON.stringify({
      periodo_id: SB.periodoId, ingr_egr_id: iid, alumno: card.dataset.nombre,
      grado: card.dataset.grado, grupo: card.dataset.grupo, area: SB.area,
      clase: clase, hora_salida: ahora(), hora_regreso: '', comentario: ''
    }) }).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { alert(d.error || 'Error al registrar la salida.'); card.style.pointerEvents = ''; return; }
      SB.salidasHoy[String(iid)] = {
        count: d.count, semaforo: d.semaforo, last_id: d.id, last_clase: clase,
        last_maestro: d.maestro || '', last_hora_salida: d.hora_salida || ahora(),
        last_hora_regreso: '', last_comentario: ''
      };
      render();
    }).catch(function () { alert('Error de red.'); card.style.pointerEvents = ''; });
  }

  function marcarRegreso(card) {
    var iid = card.dataset.iid, s = salDe(iid); if (!s) { render(); return; }
    var hr = ahora(); card.style.pointerEvents = 'none';
    fetch(SB.urlRegresoBase.replace('{pk}', s.last_id), { method: 'POST', headers: headers(), body: JSON.stringify({ hora_regreso: hr }) })
      .then(function (r) { return r.json(); }).then(function (d) {
        if (!d.ok) { alert(d.error || 'Error al registrar el regreso.'); card.style.pointerEvents = ''; return; }
        s.last_hora_regreso = hr; render();
      }).catch(function () { alert('Error de red.'); card.style.pointerEvents = ''; });
  }

  // ── clics ──
  board.addEventListener('click', function (e) {
    var btn = e.target.closest('[data-act]'); if (!btn) return;
    var card = btn.closest('.sbk-card'); if (!card) return;
    var act = btn.dataset.act;
    if (act === 'salir') abrirPicker(card);
    else if (act === 'regreso') marcarRegreso(card);
    else if (act === 'cancelar') render();
    else if (act === 'confirmar') { var sel = card.querySelector('.sbk-pick select'); guardarSalida(card, sel ? sel.value : ''); }
  });

  // ── arrastrar ──
  var dragCard = null;
  board.addEventListener('dragstart', function (e) { var c = e.target.closest('.sbk-card'); if (!c) return; dragCard = c; c.classList.add('dragging'); });
  board.addEventListener('dragend', function () { if (dragCard) dragCard.classList.remove('dragging'); dragCard = null;
    board.querySelectorAll('.drag-over').forEach(function (x) { x.classList.remove('drag-over'); }); });
  board.addEventListener('dragover', function (e) { var col = e.target.closest('.sbk-col'); if (col) { e.preventDefault(); col.classList.add('drag-over'); } });
  board.addEventListener('dragleave', function (e) { var col = e.target.closest('.sbk-col'); if (col && !col.contains(e.relatedTarget)) col.classList.remove('drag-over'); });
  board.addEventListener('drop', function (e) {
    e.preventDefault(); var col = e.target.closest('.sbk-col'); if (!col || !dragCard) return;
    col.classList.remove('drag-over');
    var target = col.dataset.col, est = dragCard.dataset.est;
    if (target === est) return;
    if (target === 'afuera' && (est === 'clase' || est === 'regreso')) abrirPicker(dragCard);
    else if (target === 'regreso' && est === 'afuera') marcarRegreso(dragCard);
  });

  // ── selectores grado / sección ──
  gradosWrap.addEventListener('click', function (e) { var b = e.target.closest('[data-g]'); if (!b) return;
    gradoSel = b.dataset.g; seccSel = ''; pintarGrados(); pintarSecciones(); render(); });
  seccWrap.addEventListener('click', function (e) { var c = e.target.closest('[data-s]'); if (!c) return;
    seccSel = c.dataset.s; pintarSecciones(); render(); });

  // ── interruptor Tabla / Tablero ──
  function setView(v) {
    var kb = v === 'kanban';
    if (viewKanban) viewKanban.style.display = kb ? '' : 'none';
    if (viewTabla)  viewTabla.style.display  = kb ? 'none' : '';
    if (toggle) toggle.querySelectorAll('[data-view]').forEach(function (b) { b.classList.toggle('active', b.dataset.view === v); });
    try { localStorage.setItem('sb-view', v); } catch (_) {}
    if (kb) { pintarGrados(); pintarSecciones(); render(); }
  }
  if (toggle) {
    toggle.addEventListener('click', function (e) { var b = e.target.closest('[data-view]'); if (b) setView(b.dataset.view); });
    var saved = 'tabla'; try { saved = localStorage.getItem('sb-view') || 'tabla'; } catch (_) {}
    if (saved === 'kanban') setView('kanban');
  }

  window.SB_KANBAN = { render: render };
})();
