/* <--- hecho por claude code (06-nov-2026): Dashboard del Coordinador — diseño B «Lista + detalle».
   La tabla de siempre (DataTables, agrupado, filtros, selección y borrado en lote) queda a la izquierda en modo lista
   y a la derecha un panel con el reporte elegido. Los botones del panel son COPIAS de los de la fila: sus manejadores
   ya están delegados en el documento (editar, historial, WhatsApp, evidencias, eliminar, coordinador), así funcionan igual. */
(function () {
  var CFG_CB = document.getElementById('cb-cfg'); if (!CFG_CB) return;
  var URL_ESTADO = CFG_CB.dataset.urlEstado, CSRF_CB = CFG_CB.dataset.csrf, PUEDE = CFG_CB.dataset.editar === '1';
  var TABS = ['academicos', 'conductuales', 'progress'];
  var OCULTAS = ['#', 'Tipo', 'Fecha', 'Grado', 'Docente', 'Maestro', 'Coord.', 'Estado', 'Evidencias', 'Acciones'];
  var EST = ['enviado', 'revisado', 'aprobado'], EL = { enviado: 'Enviado', revisado: 'Revisado', aprobado: 'Aprobado' };
  var COLS = ['#2563eb', '#7c3aed', '#0ca678', '#f76707', '#d6336c', '#0d9488', '#4263eb'];

  function esc(x) { return String(x == null ? '' : x).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function iniciales(n) { return String(n || '?').trim().split(/\s+/).slice(0, 2).map(function (p) { return p[0] || ''; }).join('').toUpperCase(); }
  function filasDe(tabla) {
    try { if ($.fn.DataTable && $.fn.DataTable.isDataTable(tabla)) return $(tabla).DataTable().rows().nodes().toArray(); } catch (e) {}
    return [].slice.call(tabla.querySelectorAll('tbody tr[data-pk]'));
  }

  // marca las columnas que se esconden en modo lista y las que el panel copia
  function marcarColumnas(tabla) {
    var ths = [].slice.call(tabla.querySelectorAll('thead th'));
    var idx = {};
    ths.forEach(function (th, i) {
      var t = th.textContent.trim();
      if (OCULTAS.indexOf(t) > -1) th.classList.add('cb-x');
      if (t === 'Alumno') th.classList.add('cb-al');
      if (t === 'Evidencias') idx.ev = i; if (t === 'Acciones') idx.ac = i; if (t === 'Coord.') idx.co = i; if (t === 'Estado') idx.es = i;
    });
    filasDe(tabla).forEach(function (tr) {
      var tds = tr.children;
      ths.forEach(function (th, i) { if (tds[i] && th.classList.contains('cb-x')) tds[i].classList.add('cb-x'); });
      if (tds[idx.ev]) tds[idx.ev].classList.add('cb-evid');
      if (tds[idx.ac]) tds[idx.ac].classList.add('cb-acc');
      if (idx.co !== undefined && tds[idx.co]) tds[idx.co].classList.add('cb-coord');
      if (tds[idx.es]) tds[idx.es].classList.add('cb-est');
      pintarFila(tr);
    });
  }
  // la celda del alumno lleva debajo: grado · materia/docente, y a la derecha el estado
  function pintarFila(tr) {
    var d = tr.dataset, al = tr.querySelector('td:not(.cb-x):not(:first-child)') || tr.children[2];
    if (!al || !d.pk) return;
    if (!al.dataset.cbNom) al.dataset.cbNom = al.textContent.trim();
    var e = d.estado === 'revisando' ? 'enviado' : (d.estado || 'enviado');
    al.innerHTML = '<div class="cb-it"><span class="cb-av" style="background:' + COLS[(+d.pk) % COLS.length] + '">' + esc(iniciales(al.dataset.cbNom)) + '</span>' +
      '<span class="cb-it__t"><b>' + esc(al.dataset.cbNom) + '</b><small>' + esc(d.grado || '') + (d.materia ? ' · ' + esc(d.materia) : '') + (d.docente ? ' · ' + esc(d.docente) : '') + '</small></span>' +
      '<span class="cb-est cb-est--' + e + '">' + (EL[e] || esc(d.estado)) + '</span></div>';
  }

  function panelVacio(aside) { aside.innerHTML = '<div class="cb-vacio"><i class="ti ti-pointer"></i><b>Elige un reporte</b><span>Haz clic en un reporte de la lista para verlo completo aquí.</span></div>'; }

  function pintarPanel(aside, tr) {
    var d = tr.dataset, e = d.estado === 'revisando' ? 'enviado' : (d.estado || 'enviado'), k = EST.indexOf(e);
    var nom = (tr.querySelector('[data-cb-nom]') || {}).dataset ? (tr.querySelector('[data-cb-nom]').dataset.cbNom) : '';
    var ev = tr.querySelector('.cb-evid'), ac = tr.querySelector('.cb-acc'), co = tr.querySelector('.cb-coord');
    var h = '<div class="cb-det__h"><span class="cb-av cb-av--lg" style="background:' + COLS[(+d.pk) % COLS.length] + '">' + esc(iniciales(nom)) + '</span>' +
      '<div class="cb-det__tit"><h3>' + esc(nom) + '</h3><span>Reporte #' + esc(d.pk) + ' · ' + esc(d.fecha || '') + '</span></div>' +
      '<span class="cb-est cb-est--' + e + '">' + (EL[e] || esc(d.estado)) + '</span></div>';
    if (d.estado === 'borrador') h += '<div class="cb-aviso">Borrador del maestro: todavía no lo envió.</div>';
    else h += '<div class="cb-step">' + EST.map(function (x, i) { return '<span class="' + (i <= k ? 'ok' : '') + '">' + EL[x] + '</span>'; }).join('') + '</div>';
    h += '<div class="cb-meta"><div><small>Grado</small><b>' + esc(d.grado || '—') + '</b></div><div><small>' + (d.tipo === 'progress' ? 'Semana' : 'Materia') + '</small><b>' + esc(d.materia || '—') + '</b></div>' +
      '<div><small>' + (d.tipo === 'progress' ? 'Maestro' : 'Docente') + '</small><b>' + esc(d.docente || '—') + '</b></div><div><small>Coordinación</small><b class="cb-coord-slot">' + esc(d.coord || '—') + '</b></div></div>';
    h += '<div class="cb-lbl">' + (d.tipo === 'progress' ? 'Comentario general' : 'Comentario del docente') + '</div><div class="cb-com">' + (d.comentario ? esc(d.comentario) : '<span class="text-secondary">Sin comentario.</span>') + '</div>';
    if (d.comcoord || d.firma) h += '<div class="cb-lbl">Coordinación</div><div class="cb-com cb-com--coord">' + (d.comcoord ? esc(d.comcoord) : '') + (d.firma ? '<div class="cb-firma"><i class="ti ti-signature"></i> ' + esc(d.firma) + '</div>' : '') + '</div>';
    h += '<div class="cb-lbl">Evidencias</div><div class="cb-ev"></div>';
    h += '<div class="cb-btns">';
    if (PUEDE && d.estado !== 'borrador') {
      if (e === 'enviado') h += '<button type="button" class="btn btn-primary cb-estado" data-estado="revisado"><i class="ti ti-eye-check me-1"></i>Marcar revisado</button>';
      if (e !== 'aprobado') h += '<button type="button" class="btn btn-success cb-estado" data-estado="aprobado"><i class="ti ti-circle-check me-1"></i>Aprobar</button>';
      else h += '<button type="button" class="btn btn-outline-secondary cb-estado" data-estado="revisado"><i class="ti ti-arrow-back-up me-1"></i>Quitar aprobación</button>';
    }
    h += '<span class="cb-acc-slot"></span></div><div class="cb-msg" hidden></div>';
    aside.innerHTML = h;
    if (ev) aside.querySelector('.cb-ev').innerHTML = ev.innerHTML;
    if (ac) aside.querySelector('.cb-acc-slot').innerHTML = ac.innerHTML;
    if (co && co.querySelector('select')) aside.querySelector('.cb-coord-slot').innerHTML = co.innerHTML;
    aside.dataset.pk = d.pk; aside.dataset.tipo = d.tipo;
  }

  function seleccionar(lista, aside, tr) {
    [].forEach.call(lista.querySelectorAll('tr.cb-sel'), function (x) { x.classList.remove('cb-sel'); });
    if (!tr) { panelVacio(aside); return; }
    tr.classList.add('cb-sel'); pintarPanel(aside, tr);
  }

  function montar(tab) {
    var pane = document.getElementById('tab-' + tab), tabla = document.getElementById('tabla-' + tab);
    if (!pane || !tabla || pane.querySelector('.cb-md')) return;
    var cont = tabla.closest('.table-responsive') || tabla.parentNode;
    var md = document.createElement('div'); md.className = 'cb-md';
    var lista = document.createElement('div'); lista.className = 'cb-lista';
    var aside = document.createElement('aside'); aside.className = 'cb-det';
    cont.parentNode.insertBefore(md, cont); lista.appendChild(cont); md.appendChild(lista); md.appendChild(aside);
    marcarColumnas(tabla); panelVacio(aside);
    var primera = tabla.querySelector('tbody tr[data-pk]'); if (primera) seleccionar(lista, aside, primera);
    // filas nuevas al paginar/filtrar: volver a marcar
    try { $(tabla).on('draw.dt', function () { marcarColumnas(tabla); }); } catch (e) {}
    lista.addEventListener('click', function (ev) {
      if (ev.target.closest('input, button, select, a, .ev-thumb-wrap')) return;
      var tr = ev.target.closest('tbody tr[data-pk]'); if (tr) seleccionar(lista, aside, tr);
    });
    // botones de estado
    aside.addEventListener('click', function (ev) {
      var b = ev.target.closest('.cb-estado'); if (!b) return;
      var fd = new FormData(); fd.append('pk', aside.dataset.pk); fd.append('tipo', aside.dataset.tipo); fd.append('estado', b.dataset.estado);
      b.disabled = true;
      fetch(URL_ESTADO, { method: 'POST', body: fd, headers: { 'X-CSRFToken': CSRF_CB }, credentials: 'same-origin' })
        .then(function (r) { return r.json().catch(function () { return { ok: false, error: 'Respuesta inválida.' }; }); })
        .then(function (j) {
          var tr = lista.querySelector('tr.cb-sel');
          if (j.ok && tr) {
            tr.dataset.estado = j.estado; pintarFila(tr);
            var badge = tr.querySelector('.cb-est.cb-x .badge, td.cb-est .badge');
            if (badge) { var m = { enviado: ['bg-secondary-lt', 'text-secondary'], revisado: ['bg-blue-lt', 'text-blue'], aprobado: ['bg-success-lt', 'text-success'] }[j.estado]; badge.className = 'badge ' + m[0] + ' ' + m[1]; badge.textContent = EL[j.estado]; }
            pintarPanel(aside, tr);
          } else {
            b.disabled = false; var msg = aside.querySelector('.cb-msg'); msg.hidden = false; msg.textContent = j.error || 'No se pudo cambiar el estado.';
          }
        });
    });
  }

  function iniciar() { TABS.forEach(montar); }
  // después de que coordinador.js inicializa DataTables
  if (document.readyState === 'complete') setTimeout(iniciar, 0); else window.addEventListener('load', function () { setTimeout(iniciar, 0); });
  // al editar en la ventana, refrescar el panel con lo que quedó en la fila
  document.addEventListener('hidden.bs.modal', function () {
    document.querySelectorAll('.cb-md').forEach(function (md) {
      var tr = md.querySelector('tr.cb-sel'), aside = md.querySelector('.cb-det'); if (tr && aside) pintarPanel(aside, tr);
    });
  });
})();
