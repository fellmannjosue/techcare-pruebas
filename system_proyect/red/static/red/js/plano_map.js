/* <--- hecho por claude code: mapa de campus interactivo.
   Colocar / arrastrar / editar marcadores (figura de red, color, tamaño, giro)
   + dibujar líneas entre marcadores. Las líneas siguen a los marcadores al moverlos. */
(function () {
  var cfg = document.getElementById('plano-cfg');
  if (!cfg) return;
  var CSRF = cfg.dataset.csrf;
  var URL_ADD = cfg.dataset.add, URL_MOVE = cfg.dataset.move, URL_DEL = cfg.dataset.del,
      URL_LINK = cfg.dataset.link, URL_EDIT = cfg.dataset.edit,
      URL_LADD = cfg.dataset.lineaAdd, URL_LDEL = cfg.dataset.lineaDel,
      URL_LEDIT = cfg.dataset.lineaEdit, URL_BULK = cfg.dataset.bulk;
  function J(v) { try { return JSON.parse(v || '[]'); } catch (e) { return []; } }
  var CATS = { gabinete: J(cfg.dataset.gabinetes), dispositivo: J(cfg.dataset.dispositivos), switch: J(cfg.dataset.switches) };
  var RACKS = (function () { try { return JSON.parse(cfg.dataset.racks || '{}'); } catch (e) { return {}; } })();

  // ── Figuras de red → ícono Tabler (ti-*) ──
  var ICONOS = {
    pin: 'ti-map-pin', router: 'ti-router', switch: 'ti-topology-star-3',
    servidor: 'ti-server-2', ap: 'ti-access-point', firewall: 'ti-shield-lock',
    camara: 'ti-device-cctv', pc: 'ti-device-desktop', impresora: 'ti-printer',
    gabinete: 'ti-versions', nube: 'ti-cloud', telefono: 'ti-device-landline-phone',
    reloj: 'ti-clock-hour-4', acceso: 'ti-door-enter'
  };
  function iconoDe(f) { return ICONOS[f] || ICONOS.pin; }
  var SVGNS = 'http://www.w3.org/2000/svg';

  var wrap = document.getElementById('plano-wrap');
  var marks = document.getElementById('plano-marks');
  var svg = document.getElementById('plano-lines');
  var img = document.getElementById('plano-img');
  var colocando = false, modoLinea = false, selOrigen = null, modoSelect = false;
  var viewZoom = 1, viewRot = 0, viewPanX = 0, viewPanY = 0;   // zoom / orientación / paneo del plano

  // convierte un punto de pantalla a % del plano, considerando zoom, rotación y paneo
  function screenToPct(cx, cy) {
    var rect = wrap.getBoundingClientRect();
    var ccx = rect.left + rect.width / 2, ccy = rect.top + rect.height / 2;
    var dx = cx - ccx, dy = cy - ccy;
    var rad = -viewRot * Math.PI / 180, co = Math.cos(rad), si = Math.sin(rad);
    var rx = (dx * co - dy * si) / viewZoom, ry = (dx * si + dy * co) / viewZoom;
    var w = wrap.offsetWidth, h = wrap.offsetHeight;
    return { x: Math.min(100, Math.max(0, (rx + w / 2) / w * 100)),
             y: Math.min(100, Math.max(0, (ry + h / 2) / h * 100)) };
  }

  var MARK = {};   // id -> {x, y, el}
  var LINES = [];  // {id, o, d, line, hit}

  function post(url, data) {
    return fetch(url, { method: 'POST', headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/x-www-form-urlencoded' }, body: new URLSearchParams(data) })
      .then(function (r) { return r.json(); });
  }

  // <--- hecho por claude code: enlaza un deslizador con un campo numérico (ambas vías) + callback
  function linkRange(range, num, cb) {
    function apply(v, from) {
      if (isNaN(v)) return;
      if (from !== 'range') range.value = Math.max(+range.min, Math.min(+range.max, v));
      if (from !== 'num') num.value = v;
      if (cb) cb(v);
    }
    range.addEventListener('input', function () { apply(parseInt(range.value, 10), 'range'); });
    num.addEventListener('input', function () { apply(parseInt(num.value, 10), 'num'); });
  }

  // ── Panel colocación ──
  var selTipo = document.getElementById('mk-tipo');
  var tw = document.getElementById('mk-target-wrap');
  var selTarget = document.getElementById('mk-target');
  function optionsFor(t) {
    return '<option value="">—</option>' + (CATS[t] || []).map(function (o) {
      return '<option value="' + o.id + '">' + o.t + '</option>';
    }).join('');
  }
  function refreshTarget() {
    if (CATS[selTipo.value]) { tw.style.display = ''; selTarget.innerHTML = optionsFor(selTipo.value); }
    else { tw.style.display = 'none'; }
  }
  selTipo.addEventListener('change', refreshTarget); refreshTarget();

  var mkTam = document.getElementById('mk-tam'), mkTamNum = document.getElementById('mk-tam-num');
  linkRange(mkTam, mkTamNum, null);

  var btnModo = document.getElementById('mk-modo');
  btnModo.addEventListener('click', function () {
    colocando = !colocando; if (colocando) { setLinea(false); setSelect(false); }
    wrap.classList.toggle('colocando', colocando);
    btnModo.className = 'btn btn-sm w-100 ' + (colocando ? 'btn-danger' : 'btn-primary');
    btnModo.innerHTML = colocando ? '<i class="ti ti-x me-1"></i>Colocación activa (clic en el plano)' : '<i class="ti ti-map-pin-plus me-1"></i>Activar colocación';
  });

  var btnLinea = document.getElementById('mk-modo-linea');
  function setLinea(on) {
    modoLinea = on; selOrigen = null;
    wrap.classList.toggle('modo-linea', modoLinea);
    Array.prototype.forEach.call(marks.children, function (c) { c.classList.remove('sel'); });
    if (!on) cerrarLineaEditor();
    btnLinea.className = 'btn btn-sm w-100 mt-2 ' + (modoLinea ? 'btn-danger' : 'btn-outline-primary');
    btnLinea.innerHTML = modoLinea ? '<i class="ti ti-x me-1"></i>Terminar líneas' : '<i class="ti ti-line me-1"></i>Dibujar líneas';
  }
  btnLinea.addEventListener('click', function () {
    setLinea(!modoLinea);
    if (modoLinea) {   // apagar los otros modos
      setSelect(false);
      if (colocando) {
        colocando = false; wrap.classList.remove('colocando');
        btnModo.className = 'btn btn-sm w-100 btn-primary';
        btnModo.innerHTML = '<i class="ti ti-map-pin-plus me-1"></i>Activar colocación';
      }
    }
  });

  // ── Selección múltiple: aplicar tamaño/giro a varios marcadores ──
  var SEL = {};   // id -> el
  var msBtn = document.getElementById('ms-modo'), msPanel = document.getElementById('ms-panel');
  var msCount = document.getElementById('ms-count');
  var msTam = document.getElementById('ms-tam'), msTamNum = document.getElementById('ms-tam-num');
  var msRot = document.getElementById('ms-rot'), msRotNum = document.getElementById('ms-rot-num');
  var msAplicar = document.getElementById('ms-aplicar'), msLimpiar = document.getElementById('ms-limpiar');
  var msBorrar = document.getElementById('ms-borrar');
  var tamTocado = false, rotTocado = false;
  linkRange(msTam, msTamNum, function (v) { tamTocado = true; Object.keys(SEL).forEach(function (id) { setTam(SEL[id], v); }); });
  linkRange(msRot, msRotNum, function (v) { rotTocado = true; Object.keys(SEL).forEach(function (id) { setRot(SEL[id], v); }); });

  function selCount() { return Object.keys(SEL).length + Object.keys(SELL).length; }
  function limpiarSel() {
    Object.keys(SEL).forEach(function (id) { if (SEL[id]) SEL[id].classList.remove('msel'); });
    Object.keys(SELL).forEach(function (id) { if (SELL[id]) SELL[id].poly.classList.remove('pl-msel'); });
    SEL = {}; SELL = {}; if (msCount) msCount.textContent = '0';
  }
  function resetSliders() {
    tamTocado = false; rotTocado = false;
    msTam.value = 30; msTamNum.value = 30;
    msRot.value = 0; msRotNum.value = 0;
  }
  function setSelect(on) {
    modoSelect = on;
    wrap.classList.toggle('modo-select', on);
    msPanel.style.display = on ? '' : 'none';
    msBtn.className = 'btn btn-sm w-100 ' + (on ? 'btn-danger' : 'btn-outline-primary');
    msBtn.innerHTML = on ? '<i class="ti ti-x me-1"></i>Terminar selección' : '<i class="ti ti-select me-1"></i>Seleccionar varios';
    if (!on) { limpiarSel(); resetSliders(); }
  }
  function toggleSel(el) {
    var id = el.dataset.id;
    if (SEL[id]) { delete SEL[id]; el.classList.remove('msel'); }
    else {
      SEL[id] = el; el.classList.add('msel');
      if (tamTocado) setTam(el, msTam.value);   // hereda la previsualización activa
      if (rotTocado) setRot(el, msRot.value);
    }
    msCount.textContent = String(selCount());
  }
  msBtn.addEventListener('click', function () {
    setSelect(!modoSelect);
    if (modoSelect) {   // apagar los otros modos
      setLinea(false);
      if (colocando) {
        colocando = false; wrap.classList.remove('colocando');
        btnModo.className = 'btn btn-sm w-100 btn-primary';
        btnModo.innerHTML = '<i class="ti ti-map-pin-plus me-1"></i>Activar colocación';
      }
    }
  });
  msLimpiar.addEventListener('click', function () { limpiarSel(); });
  msAplicar.addEventListener('click', function () {
    if (!Object.keys(SEL).length) { alert('Selecciona al menos un marcador para cambiar tamaño/giro.'); return; }
    if (!tamTocado && !rotTocado) { alert('Mueve el deslizador de tamaño o de giro.'); return; }
    var data = { ids: Object.keys(SEL).join(',') };
    if (tamTocado) data.tamano = msTamNum.value;
    if (rotTocado) data.rotacion = msRotNum.value;
    post(URL_BULK, data).then(function (d) {
      if (d.ok) { limpiarSel(); resetSliders(); }
      else alert(d.error || 'No se pudo aplicar.');
    });
  });
  if (msBorrar) msBorrar.addEventListener('click', function () {
    var mIds = Object.keys(SEL), lIds = Object.keys(SELL);
    if (!mIds.length && !lIds.length) { alert('Selecciona marcadores o líneas.'); return; }
    if (!confirm('¿Eliminar ' + (mIds.length + lIds.length) + ' elemento(s)?')) return;
    var proms = [];
    mIds.forEach(function (id) {
      proms.push(post(URL_DEL.replace('/0/', '/' + id + '/'), {}).then(function () {
        borrarLineasDe(id); if (MARK[id]) { MARK[id].el.remove(); delete MARK[id]; }
      }));
    });
    lIds.forEach(function (id) {
      var l = SELL[id];
      proms.push(post(URL_LDEL.replace('/0/', '/' + id + '/'), {}).then(function () { quitarLinea(l); }));
    });
    Promise.all(proms).then(function () { limpiarSel(); });
  });

  // ── Render de un marcador ──
  function render(m) {
    var el = document.createElement('div');
    el.className = 'mk mk-fig'; el.dataset.id = m.id;
    el.style.left = m.x + '%'; el.style.top = m.y + '%';
    el.dataset.x = m.x; el.dataset.y = m.y;
    MARK[m.id] = { x: m.x, y: m.y, el: el };
    aplica(el, m);
    marks.appendChild(el);
    hookDrag(el, m);
    return el;
  }
  function aplica(el, m) {
    var tam = parseInt(m.tamano || 30, 10);
    var rot = parseInt(m.rotacion || 0, 10);
    el.dataset.forma = m.forma || 'pin';
    el.dataset.color = m.color || '#206bc4';
    el.dataset.etiqueta = m.etiqueta || '';
    el.dataset.tipo = m.tipo || 'nota';
    el.dataset.ref = m.ref_pk || '';
    el.dataset.tamano = tam;
    el.dataset.rotacion = rot;
    el.innerHTML =
      '<span class="mk-badge" style="background:' + (m.color || '#206bc4') + ';width:' + tam + 'px;height:' + tam + 'px">' +
        '<i class="ti ' + iconoDe(m.forma) + '" style="font-size:' + Math.round(tam * 0.56) + 'px"></i>' +
      '</span>' +
      '<span class="mk-lbl">' + (m.etiqueta || '') + '</span>';
    setTam(el, tam);   // escala ícono + texto
    setRot(el, rot);   // la rotación gira TODO el marcador (ícono + texto)
  }
  // helpers que cambian tamaño/giro sin reconstruir el marcador (para vista previa)
  function setTam(el, tam) {
    tam = parseInt(tam, 10); el.dataset.tamano = tam;
    var b = el.querySelector('.mk-badge'); if (b) { b.style.width = tam + 'px'; b.style.height = tam + 'px'; }
    var ic = el.querySelector('.mk-badge .ti'); if (ic) ic.style.fontSize = Math.round(tam * 0.56) + 'px';
    // <--- hecho por claude code: el texto también escala con el tamaño
    var lb = el.querySelector('.mk-lbl'); if (lb) lb.style.fontSize = Math.max(8, Math.round(tam * 0.40)) + 'px';
  }
  function setRot(el, rot) {
    rot = parseInt(rot, 10); el.dataset.rotacion = rot;
    el.style.transform = 'translate(-50%, -50%) rotate(' + rot + 'deg)';
  }

  // ── Líneas (polilíneas: recta u ortogonal, con punto de referencia) ──
  var lineui = document.getElementById('plano-lineui');
  var SELL = {};       // id -> línea (selección múltiple)
  var lnSel = null;    // línea en edición individual
  var lnOrig = null, lnGuardado = false;

  function centro(id) { var mk = MARK[id]; return mk ? { x: mk.x, y: mk.y } : null; }
  function ptsCalc(l) {
    var a = centro(l.o), b = centro(l.d); if (!a || !b) return null;
    var mx = (l.mx == null ? (a.x + b.x) / 2 : l.mx);
    var my = (l.my == null ? (a.y + b.y) / 2 : l.my);
    if (l.estilo === 'orto') return { pts: [[a.x, a.y], [mx, a.y], [mx, b.y], [b.x, b.y]], hx: mx, hy: (a.y + b.y) / 2 };
    return { pts: [[a.x, a.y], [mx, my], [b.x, b.y]], hx: mx, hy: my };
  }
  function pintarLinea(l) {
    var c = ptsCalc(l); if (!c) return;
    var s = c.pts.map(function (p) { return p[0] + ',' + p[1]; }).join(' ');
    l.poly.setAttribute('points', s); l.hit.setAttribute('points', s);
    l.poly.setAttribute('stroke', l.color);
    if (l.etiqueta) { l.lbl.style.display = ''; l.lbl.textContent = l.etiqueta; l.lbl.style.left = c.hx + '%'; l.lbl.style.top = c.hy + '%'; }
    else l.lbl.style.display = 'none';
    l.handle.style.left = c.hx + '%'; l.handle.style.top = c.hy + '%';
  }
  function crearLinea(d) {
    var poly = document.createElementNS(SVGNS, 'polyline'); poly.setAttribute('class', 'pl-line');
    var hit = document.createElementNS(SVGNS, 'polyline'); hit.setAttribute('class', 'pl-hit');
    var lbl = document.createElement('div'); lbl.className = 'pl-lbl'; lbl.style.display = 'none';
    var handle = document.createElement('div'); handle.className = 'pl-handle'; handle.style.display = 'none';
    var l = { id: d.id, o: d.origen_id, d: d.destino_id, color: d.color || '#495057',
      etiqueta: d.etiqueta || '', estilo: d.estilo || 'recta',
      mx: (d.mx == null ? null : +d.mx), my: (d.my == null ? null : +d.my),
      eqo: (d.equipo_origen || d.equipo_origen_id || ''), eqd: (d.equipo_destino || d.equipo_destino_id || ''),
      poly: poly, hit: hit, lbl: lbl, handle: handle };
    hit.addEventListener('click', function (ev) {
      if (modoLinea) { ev.stopPropagation(); seleccionarLinea(l); }
      else if (modoSelect) { ev.stopPropagation(); toggleSelLinea(l); }
    });
    hookHandle(l);
    svg.appendChild(poly); svg.appendChild(hit);
    lineui.appendChild(lbl); lineui.appendChild(handle);
    LINES.push(l); pintarLinea(l);
  }
  function quitarLinea(l) {
    if (!l) return;
    l.poly.remove(); l.hit.remove(); l.lbl.remove(); l.handle.remove();
    LINES = LINES.filter(function (x) { return x !== l; });
    delete SELL[l.id];
  }
  function lineasDe(markId) {
    LINES.forEach(function (l) { if (l.o == markId || l.d == markId) pintarLinea(l); });
  }
  function borrarLineasDe(markId) {
    LINES.filter(function (l) { return l.o == markId || l.d == markId; }).forEach(quitarLinea);
  }
  function ocultarHandles() {
    LINES.forEach(function (x) { x.handle.style.display = 'none'; x.poly.classList.remove('pl-sel'); });
  }
  function toggleSelLinea(l) {
    if (SELL[l.id]) { delete SELL[l.id]; l.poly.classList.remove('pl-msel'); }
    else { SELL[l.id] = l; l.poly.classList.add('pl-msel'); }
    msCount.textContent = String(selCount());
  }
  // arrastrar el punto de referencia (codo) de una línea
  function hookHandle(l) {
    var dragging = false;
    l.handle.addEventListener('mousedown', function (e) { dragging = true; e.preventDefault(); e.stopPropagation(); });
    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      var pc = screenToPct(e.clientX, e.clientY);
      l.mx = pc.x; l.my = pc.y;
      pintarLinea(l);
    });
    document.addEventListener('mouseup', function () {
      if (!dragging) return; dragging = false;
      post(URL_LEDIT.replace('/0/', '/' + l.id + '/'), { mx: l.mx, my: l.my });
    });
  }

  // ── Editor individual de línea (panel flotante) ──
  var lnEl = document.getElementById('lnEdit');
  var lneLabel = document.getElementById('lne-label'), lneColor = document.getElementById('lne-color');
  var lneEstilo = document.getElementById('lne-estilo');
  var lneDel = document.getElementById('lne-del'), lneSave = document.getElementById('lne-save'), lneClose = document.getElementById('lne-close');
  var lneEqo = document.getElementById('lne-eqo'), lneEqd = document.getElementById('lne-eqd');
  var lneEqoW = document.getElementById('lne-eqo-wrap'), lneEqdW = document.getElementById('lne-eqd-wrap');
  // gabinete vinculado por un marcador (tipo gabinete → su ref es el id del gabinete)
  function gabineteDe(markId) {
    var mk = MARK[markId]; if (!mk) return null;
    return (mk.el.dataset.tipo === 'gabinete' && mk.el.dataset.ref) ? mk.el.dataset.ref : null;
  }
  function llenaEquipo(sel, wrap, gabId, presel) {
    var items = gabId ? (RACKS[gabId] || []) : [];
    if (!items.length) { wrap.style.display = 'none'; sel.innerHTML = ''; return; }
    wrap.style.display = '';
    sel.innerHTML = '<option value="">— Ninguno —</option>' + items.map(function (it) {
      return '<option value="' + it.id + '">' + it.nombre + '</option>';
    }).join('');
    if (presel) sel.value = presel;
  }
  function seleccionarLinea(l) {
    ocultarHandles();
    if (modalEl) modalEl.hidden = true;      // cerrar panel de marcador si estaba
    lnSel = l; lnGuardado = false; lnOrig = { etiqueta: l.etiqueta, color: l.color, estilo: l.estilo };
    l.handle.style.display = ''; l.poly.classList.add('pl-sel');
    lneLabel.value = l.etiqueta || ''; lneColor.value = l.color || '#495057'; lneEstilo.value = l.estilo || 'recta';
    llenaEquipo(lneEqo, lneEqoW, gabineteDe(l.o), l.eqo);
    llenaEquipo(lneEqd, lneEqdW, gabineteDe(l.d), l.eqd);
    lnEl.hidden = false;
  }
  function cerrarLineaEditor() {
    if (!lnGuardado && lnSel) { lnSel.etiqueta = lnOrig.etiqueta; lnSel.color = lnOrig.color; lnSel.estilo = lnOrig.estilo; pintarLinea(lnSel); }
    lnEl.hidden = true; ocultarHandles(); lnSel = null;
  }
  if (lneClose) lneClose.addEventListener('click', cerrarLineaEditor);
  if (lneEstilo) lneEstilo.addEventListener('change', function () { if (lnSel) { lnSel.estilo = lneEstilo.value; pintarLinea(lnSel); } });
  if (lneColor) lneColor.addEventListener('input', function () { if (lnSel) { lnSel.color = lneColor.value; pintarLinea(lnSel); } });
  if (lneSave) lneSave.addEventListener('click', function () {
    if (!lnSel) return; var l = lnSel;
    var eqo = (lneEqoW.style.display !== 'none') ? lneEqo.value : '';
    var eqd = (lneEqdW.style.display !== 'none') ? lneEqd.value : '';
    post(URL_LEDIT.replace('/0/', '/' + l.id + '/'),
      { etiqueta: lneLabel.value, color: lneColor.value, estilo: lneEstilo.value, equipo_origen: eqo, equipo_destino: eqd })
      .then(function (d) {
        if (d.ok) { l.etiqueta = lneLabel.value; l.color = lneColor.value; l.estilo = lneEstilo.value; l.eqo = eqo; l.eqd = eqd; lnGuardado = true; pintarLinea(l); cerrarLineaEditor(); }
      });
  });
  if (lneDel) lneDel.addEventListener('click', function () {
    if (!lnSel) return; if (!confirm('¿Eliminar esta línea?')) return; var l = lnSel;
    post(URL_LDEL.replace('/0/', '/' + l.id + '/'), {}).then(function () { lnGuardado = true; quitarLinea(l); cerrarLineaEditor(); });
  });

  // ── Panel flotante de edición (no es un modal; deja ver el plano) ──
  var modalEl = document.getElementById('mkEdit');
  var eLabel = document.getElementById('mke-label'), eTipo = document.getElementById('mke-tipo');
  var eTw = document.getElementById('mke-target-wrap'), eTarget = document.getElementById('mke-target');
  var eColor = document.getElementById('mke-color'), eForma = document.getElementById('mke-forma');
  var eTam = document.getElementById('mke-tam'), eTamNum = document.getElementById('mke-tam-num');
  var eRot = document.getElementById('mke-rot'), eRotNum = document.getElementById('mke-rot-num');
  var eDel = document.getElementById('mke-del'), eSave = document.getElementById('mke-save'), eOpen = document.getElementById('mke-open');
  var editId = null, editEl = null, origTam = 30, origRot = 0, guardado = false;

  // vista previa en vivo: al mover tamaño/giro se ve el marcador cambiar sobre el plano
  linkRange(eTam, eTamNum, function (v) { if (editEl) setTam(editEl, v); });
  linkRange(eRot, eRotNum, function (v) { if (editEl) setRot(editEl, v); });
  // cerrar el panel: si no se guardó, revierte la vista previa
  function cerrarPanel() {
    if (!guardado && editEl) { setTam(editEl, origTam); setRot(editEl, origRot); }
    modalEl.hidden = true; editEl = null;
  }
  var eClose = document.getElementById('mke-close');
  if (eClose) eClose.addEventListener('click', cerrarPanel);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !modalEl.hidden) cerrarPanel(); });
  function refreshETarget(presel) {
    if (CATS[eTipo.value]) { eTw.style.display = ''; eTarget.innerHTML = optionsFor(eTipo.value); if (presel) eTarget.value = presel; }
    else { eTw.style.display = 'none'; }
  }
  eTipo.addEventListener('change', function () { refreshETarget(''); });

  function abrirEdicion(el) {
    cerrarLineaEditor();                     // cerrar editor de línea si estaba abierto
    editId = el.dataset.id; editEl = el;
    eLabel.value = el.dataset.etiqueta || '';
    eTipo.value = el.dataset.tipo || 'nota';
    eColor.value = el.dataset.color || '#206bc4';
    eForma.value = el.dataset.forma || 'pin';
    origTam = el.dataset.tamano || 30; origRot = el.dataset.rotacion || 0; guardado = false;
    eTam.value = origTam; eTamNum.value = origTam;
    eRot.value = origRot; eRotNum.value = origRot;
    refreshETarget(el.dataset.ref || '');
    eOpen.style.display = (el.dataset.ref ? '' : 'none');
    modalEl.hidden = false;
  }
  if (eSave) eSave.addEventListener('click', function () {
    if (!editId) return;
    post(URL_EDIT.replace('/0/', '/' + editId + '/'), {
      etiqueta: eLabel.value, tipo: eTipo.value, color: eColor.value, forma: eForma.value,
      tamano: eTamNum.value, rotacion: eRotNum.value,
      ref_pk: (CATS[eTipo.value] ? eTarget.value : '')
    }).then(function (d) {
      if (d.ok && editEl) { guardado = true; aplica(editEl, d.m); cerrarPanel(); }
    });
  });
  if (eDel) eDel.addEventListener('click', function () {
    if (!editId) return;
    if (!confirm('¿Eliminar este marcador?')) return;
    post(URL_DEL.replace('/0/', '/' + editId + '/'), {}).then(function () {
      guardado = true; borrarLineasDe(editId);
      if (editEl) editEl.remove(); delete MARK[editId]; cerrarPanel();
    });
  });
  if (eOpen) eOpen.addEventListener('click', function () {
    if (!editId) return;
    fetch(URL_LINK.replace('/0/', '/' + editId + '/')).then(function (r) { return r.json(); })
      .then(function (d) { if (d.url) window.location = d.url; });
  });

  // ── Selección de extremos en modo línea ──
  function pickEndpoint(el) {
    var id = el.dataset.id;
    if (!selOrigen) { selOrigen = id; el.classList.add('sel'); return; }
    if (selOrigen == id) { el.classList.remove('sel'); selOrigen = null; return; }
    var color = document.getElementById('mk-linea-color').value || '#495057';
    post(URL_LADD, { origen: selOrigen, destino: id, color: color }).then(function (d) {
      if (d.ok) crearLinea(d.l);
    });
    var prev = marks.querySelector('.mk.sel'); if (prev) prev.classList.remove('sel');
    selOrigen = null;
  }

  // ── Arrastrar / clic ──
  function hookDrag(el, m) {
    var dragging = false, moved = false, sx, sy;
    el.addEventListener('mousedown', function (e) {
      if (modoLinea || modoSelect) return;   // en esos modos no se arrastra
      dragging = true; moved = false; sx = e.clientX; sy = e.clientY; e.preventDefault();
    });
    document.addEventListener('mousemove', function (e) {
      if (!dragging) return;
      if (Math.abs(e.clientX - sx) > 3 || Math.abs(e.clientY - sy) > 3) moved = true;
      var pc = screenToPct(e.clientX, e.clientY);
      var x = pc.x, y = pc.y;
      el.style.left = x + '%'; el.style.top = y + '%'; el.dataset.x = x; el.dataset.y = y;
      if (MARK[el.dataset.id]) { MARK[el.dataset.id].x = x; MARK[el.dataset.id].y = y; }
      lineasDe(el.dataset.id);
    });
    document.addEventListener('mouseup', function () {
      if (!dragging) return; dragging = false;
      if (moved) post(URL_MOVE.replace('/0/', '/' + el.dataset.id + '/'), { x: el.dataset.x, y: el.dataset.y });
    });
    // clic (sin arrastre) → editar; en modo línea → seleccionar extremo
    el.addEventListener('click', function (e) {
      if (modoLinea) { e.stopPropagation(); pickEndpoint(el); return; }
      if (modoSelect) { e.stopPropagation(); toggleSel(el); return; }
      if (!moved) abrirEdicion(el);
    });
  }

  // ── Colocar nuevo al hacer clic en el plano ──
  img.addEventListener('click', function (e) {
    if (!colocando) return;
    var pc = screenToPct(e.clientX, e.clientY);
    var x = pc.x, y = pc.y;
    post(URL_ADD, {
      etiqueta: document.getElementById('mk-label').value || 'Marcador',
      tipo: selTipo.value, color: document.getElementById('mk-color').value,
      forma: document.getElementById('mk-forma').value, tamano: mkTamNum.value,
      x: x, y: y, ref_pk: (CATS[selTipo.value] ? selTarget.value : '')
    }).then(function (d) { if (d.ok) render(d.m); });
  });

  // ── Zoom / orientación / paneo del plano ──
  var PLID = cfg.dataset.planoId || '0';
  var VKEY = 'red_plano_view_' + PLID;
  var zRange = document.getElementById('zoom-range'), zVal = document.getElementById('zoom-val');
  var zIn = document.getElementById('zoom-in'), zOut = document.getElementById('zoom-out');
  var rRange = document.getElementById('rot-range'), rVal = document.getElementById('rot-val');
  var rLeft = document.getElementById('rot-left'), rRight = document.getElementById('rot-right');
  var vReset = document.getElementById('view-reset');

  function applyView() {
    wrap.style.transformOrigin = 'center center';
    wrap.style.transform = 'translate(' + viewPanX + 'px,' + viewPanY + 'px) scale(' + viewZoom + ') rotate(' + viewRot + 'deg)';
  }
  function persistView() {
    try { localStorage.setItem(VKEY, JSON.stringify({ z: viewZoom, r: viewRot, px: viewPanX, py: viewPanY })); } catch (e) {}
  }
  function setZoom(z) {
    viewZoom = Math.max(0.3, Math.min(3, z));
    zRange.value = Math.round(viewZoom * 100); zVal.textContent = Math.round(viewZoom * 100) + '%';
    applyView(); persistView();
  }
  function setOrient(d) {
    viewRot = ((Math.round(d) % 360) + 360) % 360;
    rRange.value = viewRot; rVal.textContent = viewRot + '°';
    applyView(); persistView();
  }
  zRange.addEventListener('input', function () { setZoom(zRange.value / 100); });
  zIn.addEventListener('click', function () { setZoom(viewZoom + 0.1); });
  zOut.addEventListener('click', function () { setZoom(viewZoom - 0.1); });
  rRange.addEventListener('input', function () { setOrient(rRange.value); });
  rLeft.addEventListener('click', function () { setOrient(viewRot - 15); });
  rRight.addEventListener('click', function () { setOrient(viewRot + 15); });
  vReset.addEventListener('click', function () { viewPanX = 0; viewPanY = 0; setZoom(1); setOrient(0); });

  // paneo: arrastrar el fondo del plano cuando NO se está colocando/uniendo/seleccionando
  (function () {
    var panning = false, sx, sy, ox, oy;
    img.addEventListener('mousedown', function (e) {
      if (colocando || modoLinea || modoSelect) return;
      panning = true; sx = e.clientX; sy = e.clientY; ox = viewPanX; oy = viewPanY;
      wrap.classList.add('paneando'); e.preventDefault();
    });
    document.addEventListener('mousemove', function (e) {
      if (!panning) return;
      viewPanX = ox + (e.clientX - sx); viewPanY = oy + (e.clientY - sy); applyView();
    });
    document.addEventListener('mouseup', function () {
      if (!panning) return; panning = false; wrap.classList.remove('paneando'); persistView();
    });
  })();

  // rueda del ratón con Ctrl = zoom
  wrap.addEventListener('wheel', function (e) {
    if (!e.ctrlKey) return; e.preventDefault();
    setZoom(viewZoom + (e.deltaY < 0 ? 0.1 : -0.1));
  }, { passive: false });

  function initView() {
    try {
      var v = JSON.parse(localStorage.getItem(VKEY) || '{}');
      if (v.z) viewZoom = v.z; if (v.r) viewRot = v.r;
      if (v.px) viewPanX = v.px; if (v.py) viewPanY = v.py;
    } catch (e) {}
    zRange.value = Math.round(viewZoom * 100); zVal.textContent = Math.round(viewZoom * 100) + '%';
    rRange.value = viewRot; rVal.textContent = viewRot + '°';
    applyView();
  }

  // ── Carga inicial ──
  J(cfg.dataset.marcadores).forEach(render);
  J(cfg.dataset.lineas).forEach(crearLinea);
  window.addEventListener('resize', function () { LINES.forEach(pintarLinea); });
  initView();
})();
