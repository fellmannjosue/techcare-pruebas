/* diseno_agenda.js — <--- hecho por claude code (15-oct-2026): editor de diseño de la agenda.
   Dibuja la hoja (réplica del PowerPoint BL o del Word de Colegio) a partir de la isla #dz-datos, aplica los ajustes
   del panel, guarda solo (debounce) y genera el PNG con html2canvas, que además se guarda como imagen final.
   Un solo global: DISENO_AGENDA. */
(function () {
  'use strict';
  var isla = document.getElementById('dz-datos'), cfg = document.getElementById('dz-config');
  if (!isla || !cfg) return;
  var D = JSON.parse(isla.textContent);
  var BL = D.tipo === 'bl';
  var PX_IN = 96, PX_CM = 96 / 2.54, PX_PT = 96 / 72;
  var HOJA = BL ? { w: 1280, h: 720 } : { w: 1122.5, h: 793.7 };
  var DIAS = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes'];
  var CAB = BL ? ['Clase/Día', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Nota']
               : ['ASIGNATURA', 'LUNES', 'MARTES', 'MIÉRCOLES', 'JUEVES', 'VIERNES'];
  var dz = JSON.parse(JSON.stringify(D.diseno));
  var hoja = document.getElementById('dz-hoja'), esc = document.getElementById('dz-escenario');
  var estado = document.getElementById('dz-estado'), aviso = document.getElementById('dz-aviso');
  var panelCelda = document.getElementById('dz-celda'), chkEditar = document.getElementById('dz-editar');
  var sel = null, tGuardar = null, guardando = null, pendiente = false;

  function h(t) { var e = document.createElement('div'); e.textContent = t == null ? '' : String(t); return e.innerHTML; }
  function pt(n) { return (n * PX_PT).toFixed(2) + 'px'; }
  function vacia(f) { return !DIAS.some(function (d) { return (f[d] || '').trim(); }); }
  function filasVisibles() { return D.filas.filter(function (f) { return !(dz.ocultar_vacias && vacia(f)); }); }
  function letraDe(clave, base) { return dz.celdas[clave] != null ? dz.celdas[clave] : base; }

  /* ── Dibujo ─────────────────────────────────────────────────── */
  function celda(tag, clave, texto, base, clases, editable, extra) {
    var size = letraDe(clave, base);
    return '<' + tag + ' data-c="' + h(clave) + '" class="' + clases + (dz.celdas[clave] != null ? ' dz-ajustada' : '') +
      (editable ? ' dz-editable' : '') + (sel === clave ? ' dz-sel' : '') + '" style="font-size:' + pt(size) + '"' + (extra || '') +
      (editable && chkEditar.checked ? ' contenteditable="true"' : '') + '>' + h(texto) + '</' + tag + '>';
  }

  function dibujar() {
    var filas = filasVisibles();
    var unidad = BL ? PX_IN : PX_CM;
    var anchos = dz.anchos.map(function (w) { return w * unidad; });
    var total = anchos.reduce(function (a, b) { return a + b; }, 0);
    var col = '<colgroup>' + anchos.map(function (w) { return '<col style="width:' + w.toFixed(1) + 'px">'; }).join('') + '</colgroup>';
    var cab = '<tr>' + CAB.map(function (t, i) {
      return celda('th', 'cab|' + i, t, dz.letra_encabezado, '', false);
    }).join('') + '</tr>';
    var cuerpo = filas.map(function (f, i) {
      var tds = celda('td', f.materia + '|materia', f.materia, dz.letra_clase, 'dz-clase', false);
      DIAS.forEach(function (d) { tds += celda('td', f.materia + '|' + d, f[d] || '', dz.letra_celda, 'dz-dia', true, ' data-m="' + h(f.materia) + '" data-d="' + d + '"'); });
      if (BL && i === 0) tds += celda('td', 'nota', D.nota, dz.letra_nota, 'dz-nota', true, ' rowspan="' + filas.length + '" data-d="nota"');
      return '<tr>' + tds + '</tr>';
    }).join('');
    var tabla = '<table class="dz-tabla" style="width:' + total.toFixed(1) + 'px">' + col + '<thead>' + cab + '</thead><tbody>' + cuerpo + '</tbody></table>';
    if (BL) {
      hoja.style.backgroundImage = 'url("' + D.fondo + '")';   // static() ya la entrega codificada
      hoja.innerHTML = '<div class="dz-caja dz-bl-titulo">Agenda\nSemanal</div>' +
        '<div class="dz-caja dz-bl-semana"><u>Semana:</u>\n' + h(D.semana) + '</div>' +
        '<div class="dz-caja dz-bl-grado">Grado: ' + h(D.grado) + '</div>' + tabla;
    } else {
      hoja.innerHTML = '<div class="dz-col-cuerpo"><div class="dz-col-l1">C. E. M. N. G. NUEVO AMANECER</div>' +
        '<div class="dz-col-l2">AGENDA SEMANAL DE TAREAS</div>' +
        '<div class="dz-col-info"><span>Grado: ' + h(D.grado) + '</span><span>' + h(D.semana_col) + '</span></div>' + tabla + '</div>';
    }
    altos(filas.length);
    escalar();
  }

  /* Alto de filas: "Ajustar a la hoja" reparte el espacio libre; si no, el alto fijo en cm. Avisa si no cabe. */
  function altos(n) {
    var tabla = hoja.querySelector('.dz-tabla');
    var top = BL ? 4.8 : tabla.getBoundingClientRect().top / escala() - hoja.getBoundingClientRect().top / escala();
    var libre = HOJA.h - top - (BL ? 4.8 : 37.8);
    var alto = dz.auto_alto ? libre / (n + 1) : dz.alto_fila * PX_CM;
    tabla.querySelectorAll('tr').forEach(function (tr) { tr.style.height = alto.toFixed(1) + 'px'; });
    var sobra = (tabla.offsetHeight - libre) / PX_CM;
    var ancho = (tabla.offsetWidth - (BL ? HOJA.w - 225.6 - 4 : HOJA.w - 113.4)) / PX_CM;
    var msgs = [];
    if (sobra > 0.05) msgs.push('La tabla se sale de la hoja por <b>' + sobra.toFixed(1) + ' cm</b> de alto: baja la letra, el alto de las filas u oculta clases vacías.');
    if (ancho > 0.05) msgs.push('La tabla es <b>' + ancho.toFixed(1) + ' cm</b> más ancha que la hoja: reduce el ancho de alguna columna.');
    aviso.innerHTML = msgs.join('<br>');
    aviso.classList.toggle('d-none', !msgs.length);
  }

  function escala() { return parseFloat(hoja.dataset.escala || '1'); }
  function escalar() {
    var s = Math.min(1, esc.clientWidth / HOJA.w);
    hoja.dataset.escala = s;
    hoja.style.transform = 'scale(' + s + ')';
    esc.style.height = (HOJA.h * s) + 'px';
  }
  window.addEventListener('resize', function () { escalar(); });

  /* ── Panel ──────────────────────────────────────────────────── */
  var campos = document.querySelectorAll('[data-k]');
  var cont = document.getElementById('dz-anchos');
  cont.innerHTML = CAB.map(function (t, i) {
    return '<label>' + h(t.charAt(0) + t.slice(1).toLowerCase()) + '<input type="number" class="form-control form-control-sm" step="0.05" min="0.3" max="12" data-col="' + i + '"></label>';
  }).join('');

  function aPanel() {
    campos.forEach(function (c) {
      if (c.type === 'checkbox') c.checked = !!dz[c.dataset.k]; else c.value = dz[c.dataset.k];
    });
    document.querySelector('[data-k="alto_fila"]').disabled = !!dz.auto_alto;
    cont.querySelectorAll('[data-col]').forEach(function (c) { c.value = dz.anchos[+c.dataset.col]; });
    pintarCelda();
  }
  campos.forEach(function (c) {
    c.addEventListener(c.type === 'checkbox' ? 'change' : 'input', function () {
      if (c.type === 'checkbox') dz[c.dataset.k] = c.checked;
      else { var v = parseFloat(c.value); if (isNaN(v)) return; dz[c.dataset.k] = v; }
      if (c.dataset.k === 'auto_alto') document.querySelector('[data-k="alto_fila"]').disabled = c.checked;
      dibujar(); cambio();
    });
  });
  cont.addEventListener('input', function (e) {
    var v = parseFloat(e.target.value);
    if (isNaN(v)) return;
    dz.anchos[+e.target.dataset.col] = v; dibujar(); cambio();
  });

  function nombreCelda(c) {
    if (c === 'nota') return 'Nota';
    var p = c.split('|');
    if (p[0] === 'cab') return 'Encabezado «' + CAB[+p[1]] + '»';
    return p[0] + ' · ' + (p[1] === 'materia' ? 'nombre de la clase' : CAB[DIAS.indexOf(p[1]) + 1]);
  }
  function baseDe(c) {
    if (c === 'nota') return dz.letra_nota;
    if (c.indexOf('cab|') === 0) return dz.letra_encabezado;
    return c.slice(-8) === '|materia' ? dz.letra_clase : dz.letra_celda;
  }
  function pintarCelda() {
    if (!sel) { panelCelda.innerHTML = '<span class="text-muted small">Haz clic en una celda de la hoja para darle su propio tamaño de letra.</span>'; return; }
    var v = letraDe(sel, baseDe(sel)), propio = dz.celdas[sel] != null;
    panelCelda.innerHTML = '<div class="dz-celda-nombre">' + h(nombreCelda(sel)) + '</div><div class="dz-celda-ctrl">' +
      '<button type="button" class="btn btn-sm btn-icon" data-a="-1" title="Más pequeña"><i class="ti ti-minus"></i></button><b>' + v + ' pt</b>' +
      '<button type="button" class="btn btn-sm btn-icon" data-a="1" title="Más grande"><i class="ti ti-plus"></i></button>' +
      (propio ? '<button type="button" class="btn btn-sm btn-ghost-secondary" data-a="0">Quitar ajuste</button>' : '') + '</div>';
  }
  panelCelda.addEventListener('click', function (e) {
    var b = e.target.closest('[data-a]');
    if (!b || !sel) return;
    var a = +b.dataset.a;
    if (a === 0) delete dz.celdas[sel];
    else dz.celdas[sel] = Math.max(5, Math.min(40, letraDe(sel, baseDe(sel)) + a * 0.5));
    dibujar(); pintarCelda(); cambio();
  });

  hoja.addEventListener('click', function (e) {
    var c = e.target.closest('[data-c]');
    if (!c) return;
    sel = c.dataset.c;
    hoja.querySelectorAll('.dz-sel').forEach(function (x) { x.classList.remove('dz-sel'); });
    c.classList.add('dz-sel');
    pintarCelda();
  });

  /* Edición de textos dentro de la hoja (sin redibujar mientras escribe, para no perder el cursor) */
  chkEditar.addEventListener('change', function () { hoja.classList.toggle('dz-editando', chkEditar.checked); dibujar(); });
  hoja.addEventListener('input', function (e) {
    var c = e.target.closest('.dz-editable');
    if (!c) return;
    var txt = c.innerText.replace(/\n$/, '');
    if (c.dataset.d === 'nota') D.nota = txt.slice(0, 200);
    else D.filas.forEach(function (f) { if (f.materia === c.dataset.m) f[c.dataset.d] = txt; });
    altos(filasVisibles().length); cambio();
  });

  /* ── Guardado ───────────────────────────────────────────────── */
  function marcar(tipo, txt) { estado.className = 'dz-estado dz-estado--' + tipo; estado.innerHTML = txt; }
  function cambio() {
    pendiente = true; marcar('guardando', '<i class="ti ti-pencil"></i> Cambios sin guardar…');
    clearTimeout(tGuardar); tGuardar = setTimeout(guardar, 1200);
  }
  function guardar() {
    clearTimeout(tGuardar);
    if (!pendiente) return Promise.resolve(true);
    if (guardando) return guardando.then(guardar);
    pendiente = false; marcar('guardando', '<i class="ti ti-loader-2"></i> Guardando…');
    guardando = fetch(cfg.dataset.urlGuardar, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': cfg.dataset.csrf },
      body: JSON.stringify({ diseno: dz, filas: D.filas, nota: D.nota })
    }).then(function (r) { return r.json(); }).then(function (d) {
      guardando = null;
      if (!d.ok) { pendiente = true; marcar('err', '<i class="ti ti-alert-triangle"></i> ' + h(d.error || 'No se guardó')); return false; }
      marcar('ok', '<i class="ti ti-circle-check"></i> Guardado ' + h(d.hora)); return true;
    }).catch(function () { guardando = null; pendiente = true; marcar('err', '<i class="ti ti-alert-triangle"></i> Sin conexión: no se guardó'); return false; });
    return guardando;
  }
  window.addEventListener('beforeunload', function (e) { if (pendiente) { e.preventDefault(); e.returnValue = ''; } });

  document.getElementById('dz-reset').addEventListener('click', function () {
    dz = JSON.parse(JSON.stringify(D.base)); sel = null; aPanel(); dibujar(); cambio();
  });
  document.querySelectorAll('.dz-descarga-office').forEach(function (a) {
    a.addEventListener('click', function (e) {   // el PowerPoint/Word se genera con los ajustes ya guardados
      if (!pendiente && !guardando) return;
      e.preventDefault(); guardar().then(function () { window.location.href = a.href; });
    });
  });

  /* ── PNG: html2canvas sobre la hoja sin escala, descarga + imagen final ─── */
  var btnPng = document.getElementById('dz-png'), finalTxt = document.getElementById('dz-final');
  btnPng.addEventListener('click', function () {
    if (!window.html2canvas) { finalTxt.textContent = 'No cargó el generador de imágenes (html2canvas). Revisa la conexión a internet.'; return; }
    btnPng.disabled = true; btnPng.innerHTML = '<i class="ti ti-loader-2"></i> Generando…';
    var editando = chkEditar.checked;
    guardar().then(function () {
      return (document.fonts && document.fonts.ready) || Promise.resolve();
    }).then(function () {
      hoja.classList.add('dz-captura'); hoja.classList.remove('dz-editando');
      hoja.querySelectorAll('[contenteditable]').forEach(function (c) { c.removeAttribute('contenteditable'); });
      var t = hoja.style.transform; hoja.style.transform = 'none';
      var p = window.html2canvas(hoja, { scale: BL ? 1.5 : 2, backgroundColor: BL ? null : '#ffffff', useCORS: true, logging: false,
                                         width: Math.round(HOJA.w), height: Math.round(HOJA.h), windowWidth: Math.round(HOJA.w) + 40 });
      return p.then(function (canvas) { hoja.style.transform = t; return canvas; }, function (err) { hoja.style.transform = t; throw err; });
    }).then(function (canvas) {
      hoja.classList.remove('dz-captura');
      if (editando) { hoja.classList.add('dz-editando'); dibujar(); }
      return new Promise(function (res) { canvas.toBlob(res, 'image/png'); });
    }).then(function (blob) {
      var a = document.createElement('a');
      a.href = URL.createObjectURL(blob); a.download = D.archivo;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      var fd = new FormData(); fd.append('imagen', blob, D.archivo);
      return fetch(cfg.dataset.urlFinal, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': cfg.dataset.csrf } })
        .then(function (r) { return r.json(); });
    }).then(function (d) {
      finalTxt.innerHTML = d.ok ? '<i class="ti ti-photo-check text-purple"></i> Descargado y guardado como imagen final (' + h(d.fecha) + ').'
                                : 'Se descargó, pero no se guardó como final: ' + h(d.error);
    }).catch(function () {
      hoja.classList.remove('dz-captura');
      finalTxt.textContent = 'No se pudo generar la imagen. Intenta de nuevo.';
    }).then(function () { btnPng.disabled = false; btnPng.innerHTML = '<i class="ti ti-photo-down me-1"></i>Descargar PNG'; });
  });

  aPanel(); dibujar();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { dibujar(); });
  window.DISENO_AGENDA = { datos: D, diseno: function () { return dz; }, guardar: guardar };
})();
