/* <--- hecho por claude code: Ingreso de Notas — tab Asistencias.
   (06-nov-2026, diseño B «Matriz por fecha»): alumnos en filas y las últimas N clases (días hábiles hasta la fecha
   elegida) en columnas. Clic en una celda alterna — → tipo 1 → tipo 2 → … (los tipos del catálogo del legacy).
   Atajos con la celda enfocada: la letra del tipo, y X / Supr para limpiar. Abajo, el detalle de la celda elegida
   (razón y otros). Contadores del día elegido arriba.

   Se guarda con el MISMO endpoint de siempre, una celda = un alumno + una fecha. Solo se registra a quien FALTÓ;
   dejar la celda vacía borra la ausencia y, como alimenta los recargos por no asistencia, pide confirmación. */
(function () {
  var d = document.getElementById('notas-config');
  if (!d) return;
  var C = { urlClases: d.dataset.v0, area: d.dataset.v3, csrf: d.dataset.v4, urlAusencias: d.dataset.v7, urlGuardar: d.dataset.v8 };

  var selGrado = document.getElementById('as-grado');
  var selClase = document.getElementById('as-clase');
  var inpFecha = document.getElementById('as-fecha');
  var selDias  = document.getElementById('as-dias');
  var cont     = document.getElementById('as-cont');
  var titulo   = document.getElementById('as-titulo');
  var estado   = document.getElementById('as-estado');
  var kpis     = document.getElementById('as-kpis');
  var det      = document.getElementById('as-det');
  if (!selGrado || !cont) return;

  var tipos = [], razones = [], razonPendiente = null, fechas = [], alumnos = [], marcas = {}, letra = {}, sel = null;
  var DIAS = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];

  function esc(s) { return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;'); }
  function pinta(txt, clase) { estado.className = 'small ' + (clase || 'text-muted'); estado.innerHTML = txt; }
  function partesGrado() { var v = (selGrado.value || '').split('|'); return { grado: v[0] || '', grupo: v[1] || '' }; }
  function vaciar(msg) {
    cont.innerHTML = '<div class="card-body text-center text-muted py-5"><i class="ti ti-hand-click" style="font-size:2rem"></i><div class="mt-2">' + msg + '</div></div>';
    titulo.textContent = 'Participantes'; kpis.hidden = true; det.hidden = true;
  }
  function iso(dt) { return dt.getFullYear() + '-' + ('0' + (dt.getMonth() + 1)).slice(-2) + '-' + ('0' + dt.getDate()).slice(-2); }
  function hoyIso() { return iso(new Date()); }

  // últimos N días hábiles (lunes a viernes) hasta la fecha elegida
  function calcularFechas() {
    var p = inpFecha.value.split('-'), dt = new Date(+p[0], +p[1] - 1, +p[2]), out = [], n = parseInt(selDias.value, 10) || 5;
    while (out.length < n) { if (dt.getDay() !== 0 && dt.getDay() !== 6) out.unshift(iso(dt)); dt.setDate(dt.getDate() - 1); }
    return out;
  }
  // letra corta y única para cada tipo del catálogo (F, T, P…)
  function letras() {
    letra = {}; var usadas = {};
    tipos.forEach(function (t) {
      var pal = String(t.label || '?').trim(), l = pal.charAt(0).toUpperCase(), i = 1;
      while (usadas[l] && i < pal.length) { l = pal.charAt(0).toUpperCase() + pal.charAt(i).toLowerCase(); i++; }
      usadas[l] = 1; letra[t.id] = l;
    });
  }

  // ── Cascada grado -> clase ──
  selGrado.addEventListener('change', function () {
    var g = partesGrado();
    selClase.innerHTML = '<option value="">Cargando…</option>'; selClase.disabled = true;
    vaciar('Elige la clase para pasar asistencia.');
    if (!g.grado) { selClase.innerHTML = '<option value="">— Elige primero el grado —</option>'; return; }
    fetch(C.urlClases + '?area=' + encodeURIComponent(C.area) + '&grado=' + encodeURIComponent(g.grado) + '&grupo=' + encodeURIComponent(g.grupo))
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        if (!dd.ok) { selClase.innerHTML = '<option value="">' + esc(dd.error) + '</option>'; return; }
        var h = '<option value="">— Seleccionar —</option>';
        dd.clases.forEach(function (cl) { h += '<option value="' + esc(cl.id) + '">' + esc(cl.nombre) + ' (' + cl.alumnos + ')</option>'; });
        selClase.innerHTML = h; selClase.disabled = false;
      })
      .catch(function () { selClase.innerHTML = '<option value="">Error de conexión</option>'; });
  });

  // ── Carga de la matriz: una consulta por fecha, en paralelo ──
  function cargar() {
    var g = partesGrado();
    if (!g.grado || !selClase.value) { vaciar('Elige grado y clase para pasar asistencia.'); return; }
    if (!inpFecha.value) return;
    fechas = calcularFechas();
    cont.innerHTML = '<div class="card-body text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>Cargando ' + fechas.length + ' días…</div>';
    var base = C.urlAusencias + '?area=' + encodeURIComponent(C.area) + '&grado=' + encodeURIComponent(g.grado) +
      '&grupo=' + encodeURIComponent(g.grupo) + '&materia=' + encodeURIComponent(selClase.value) + '&fecha=';
    Promise.all(fechas.map(function (f) { return fetch(base + f).then(function (r) { return r.json(); }); }))
      .then(function (res) {
        var malo = res.filter(function (x) { return !x.ok; })[0];
        if (malo) { cont.innerHTML = '<div class="card-body"><div class="alert alert-warning mb-0">' + esc(malo.error) + '</div></div>'; return; }
        tipos = res[0].tipos; razones = res[0].razones; razonPendiente = res[0].razon_pendiente; letras();
        alumnos = res[0].alumnos.map(function (a) { return { nombre: a.nombre, identidad: a.identidad, materia_id: a.materia_id }; });
        marcas = {};
        res.forEach(function (dd, k) {
          dd.alumnos.forEach(function (a, i) {
            if (!alumnos[i] || alumnos[i].nombre !== a.nombre) return;
            marcas[i + '|' + fechas[k]] = { tipo: a.tipo || '', razon: a.razon || '', otros: a.otros || '' };
          });
        });
        sel = null; pintar();
      })
      .catch(function () { cont.innerHTML = '<div class="card-body"><div class="alert alert-danger mb-0">Error de conexión.</div></div>'; });
  }

  function marca(i, f) { return marcas[i + '|' + f] || (marcas[i + '|' + f] = { tipo: '', razon: '', otros: '' }); }
  function celdaHtml(i, f) {
    var m = marca(i, f), t = m.tipo ? String(m.tipo) : '';
    return '<button type="button" class="as-cel' + (t ? ' as-t' + (tipos.findIndex(function (x) { return String(x.id) === t; }) + 1) : '') + '"' +
      ' data-i="' + i + '" data-f="' + f + '" aria-label="' + esc(alumnos[i].nombre) + ' ' + f + '">' + (t ? esc(letra[t] || '?') : '·') + '</button>';
  }

  function pintar() {
    var clase = selClase.options[selClase.selectedIndex].text.replace(/\s*\(\d+\)$/, '');
    titulo.innerHTML = esc(clase) + ' · ' + alumnos.length + ' alumno(s) · ' + fechas.length + ' clases';
    if (!alumnos.length) { vaciar('No hay alumnos en esa clase.'); return; }
    var hoy = hoyIso(), ultima = fechas[fechas.length - 1];
    var h = '<div class="table-responsive"><table class="table table-vcenter table-sm mb-0 tabla-notas tabla-asis"><thead><tr><th class="col-no">No</th><th class="col-alumno">Participante</th>';
    fechas.forEach(function (f) {
      var p = f.split('-'), dt = new Date(+p[0], +p[1] - 1, +p[2]);
      h += '<th class="text-center col-dia' + (f === ultima ? ' col-actual' : '') + '">' + DIAS[dt.getDay()] + '<br>' + p[2] + '/' + p[1] + (f === hoy ? '<br><span class="as-hoy">Hoy</span>' : '') + '</th>';
    });
    h += '<th class="text-center">Faltas</th></tr></thead><tbody>';
    alumnos.forEach(function (a, i) {
      h += '<tr data-i="' + i + '"><td class="text-muted">' + (i + 1) + '</td><td><div class="fw-medium">' + esc(a.nombre) + '</div><div class="text-muted small font-monospace">' + esc(a.identidad) + '</div></td>';
      fechas.forEach(function (f) { h += '<td class="text-center p-1' + (f === ultima ? ' col-actual' : '') + '">' + celdaHtml(i, f) + '</td>'; });
      h += '<td class="text-center td-faltas">0</td></tr>';
    });
    h += '</tbody></table></div>';
    cont.innerHTML = h;
    var ley = tipos.map(function (t, k) { return '<span class="as-ley"><b class="as-cel as-t' + (k + 1) + '">' + esc(letra[t.id]) + '</b>' + esc(t.label) + '</span>'; }).join('');
    kpis.hidden = false;
    kpis.dataset.ley = '1';
    contar(ley);
    det.hidden = true;
  }

  // contadores del día elegido (columna resaltada) + faltas por alumno
  function contar(ley) {
    var ultima = fechas[fechas.length - 1], porTipo = {}, presentes = 0;
    alumnos.forEach(function (a, i) {
      var m = marca(i, ultima);
      if (m.tipo) porTipo[m.tipo] = (porTipo[m.tipo] || 0) + 1; else presentes++;
      var n = fechas.filter(function (f) { return marca(i, f).tipo; }).length;
      var td = cont.querySelector('tr[data-i="' + i + '"] .td-faltas'); if (td) { td.textContent = n; td.classList.toggle('prom-baja', n > 0); }
    });
    var p = ultima.split('-');
    var h = '<span class="as-k as-k--ok"><b>' + presentes + '</b>Presentes</span>' +
      tipos.map(function (t, k) { return '<span class="as-k as-k--t' + (k + 1) + '"><b>' + (porTipo[String(t.id)] || 0) + '</b>' + esc(t.label) + '</span>'; }).join('') +
      '<span class="as-k as-k--dia">Día ' + p[2] + '/' + p[1] + '</span>';
    if (ley !== undefined) kpis.dataset.leyHtml = ley;
    kpis.innerHTML = '<div class="as-kpis__fila">' + h + '</div><div class="as-kpis__ley">' + (kpis.dataset.leyHtml || '') +
      '<span class="text-muted">Clic alterna · letra del tipo o X con la celda enfocada · deja vacío si asistió</span></div>';
  }

  // ── Guardado (mismo endpoint de siempre) ──
  function guardar(i, f, nuevo, quitar) {
    var a = alumnos[i], m = marca(i, f);
    pinta('<i class="ti ti-loader-2 me-1"></i>Guardando…');
    return fetch(C.urlGuardar, {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': C.csrf }, credentials: 'same-origin',
      body: JSON.stringify({ area: C.area, materia_id: a.materia_id, fecha: f, tipo: nuevo.tipo, razon: nuevo.razon, otros: nuevo.otros, quitar: quitar === true })
    }).then(function (r) { return r.json(); }).then(function (dd) {
      if (!dd.ok) { pinta('<i class="ti ti-alert-triangle me-1"></i>' + esc(dd.error), 'text-danger'); return false; }
      m.tipo = nuevo.tipo; m.razon = nuevo.razon; m.otros = nuevo.otros;
      var msg = dd.accion === 'delete' ? 'Falta quitada' : dd.accion === 'insert' ? 'Falta registrada' : 'Guardado';
      pinta('<i class="ti ti-check me-1"></i>' + msg + ' · ' + esc(a.nombre), 'text-green');
      return true;
    }).catch(function () { pinta('<i class="ti ti-cloud-off me-1"></i>Sin conexión — no se guardó', 'text-danger'); return false; });
  }

  function poner(btn, tipoNuevo) {
    var i = +btn.dataset.i, f = btn.dataset.f, m = marca(i, f), antes = m.tipo ? String(m.tipo) : '';
    tipoNuevo = tipoNuevo ? String(tipoNuevo) : '';
    if (tipoNuevo === antes) return;
    if (!tipoNuevo && antes) {   // <--- hecho por claude code (06-nov-2026): confirmación en modal (antes confirm() del navegador)
      confirmarQuitar(alumnos[i].nombre, f, antes, function () { aplicar(btn, i, f, m, tipoNuevo, true); });
      return;
    }
    aplicar(btn, i, f, m, tipoNuevo, false);
  }
  function confirmarQuitar(nombre, f, tipoAntes, siAcepta) {
    var el = document.getElementById('as-modal-quitar');
    if (!el || !window.bootstrap) return;
    var t = tipos.find(function (x) { return String(x.id) === String(tipoAntes); });
    el.querySelector('[data-as="alumno"]').textContent = nombre;
    el.querySelector('[data-as="fecha"]').textContent = f.split('-').reverse().join('/');
    el.querySelector('[data-as="tipo"]').textContent = t ? t.label : '';
    var ok = el.querySelector('[data-as="ok"]'), md = bootstrap.Modal.getOrCreateInstance(el), hecho = false;
    var clic = function () { hecho = true; md.hide(); };
    ok.addEventListener('click', clic, { once: true });
    el.addEventListener('hidden.bs.modal', function fin() {
      el.removeEventListener('hidden.bs.modal', fin); ok.removeEventListener('click', clic);
      if (hecho) siAcepta();
      else if (sel) { var b = cont.querySelector('.as-cel[data-i="' + sel.i + '"][data-f="' + sel.f + '"]'); if (b) b.focus(); }
    });
    md.show();
  }
  function aplicar(btn, i, f, m, tipoNuevo, quitar) {
    var nuevo = { tipo: tipoNuevo, razon: tipoNuevo ? (m.razon || String(razonPendiente || '')) : '', otros: tipoNuevo ? m.otros : '' };
    btn.classList.add('as-guardando');
    guardar(i, f, nuevo, quitar).then(function (ok) {
      btn.classList.remove('as-guardando');
      var td = btn.parentNode; td.innerHTML = celdaHtml(i, f);
      var b2 = td.querySelector('.as-cel'); if (ok) { b2.classList.add('as-ok'); setTimeout(function () { b2.classList.remove('as-ok'); }, 900); }
      b2.focus(); contar(); if (sel && sel.i === i && sel.f === f) detalle(i, f);
      if (!ok) cargar();   // para no dejar la pantalla mintiendo
    });
  }
  function siguiente(t) {   // — → tipo1 → tipo2 → … → —
    if (!t) return tipos.length ? String(tipos[0].id) : '';
    var k = tipos.findIndex(function (x) { return String(x.id) === String(t); });
    return k >= 0 && k < tipos.length - 1 ? String(tipos[k + 1].id) : '';
  }

  // detalle de la celda elegida: razón y otros (solo si faltó)
  function detalle(i, f) {
    sel = { i: i, f: f }; var m = marca(i, f);
    cont.querySelectorAll('.as-cel.as-sel').forEach(function (b) { b.classList.remove('as-sel'); });
    var b = cont.querySelector('.as-cel[data-i="' + i + '"][data-f="' + f + '"]'); if (b) b.classList.add('as-sel');
    if (!m.tipo) { det.hidden = false; det.innerHTML = '<span class="text-muted small"><b>' + esc(alumnos[i].nombre) + '</b> · ' + f.split('-').reverse().join('/') + ': asistió.</span>'; return; }
    var opR = razones.map(function (r) { return '<option value="' + r.id + '"' + (String(r.id) === String(m.razon) ? ' selected' : '') + '>' + esc(r.label) + '</option>'; }).join('');
    det.hidden = false;
    det.innerHTML = '<div class="as-det__t"><b>' + esc(alumnos[i].nombre) + '</b> · ' + f.split('-').reverse().join('/') + '</div>' +
      '<div class="as-det__c"><label>Razón<select class="form-select form-select-sm" id="as-det-razon">' + opR + '</select></label>' +
      '<label>Otros<input type="text" maxlength="50" class="form-control form-control-sm" id="as-det-otros" value="' + esc(m.otros) + '" placeholder="Detalle opcional"></label></div>';
  }
  det.addEventListener('change', function (e) {
    if (!sel || e.target.id !== 'as-det-razon') return;
    var m = marca(sel.i, sel.f); guardar(sel.i, sel.f, { tipo: String(m.tipo), razon: e.target.value, otros: m.otros });
  });
  det.addEventListener('focusout', function (e) {
    if (!sel || e.target.id !== 'as-det-otros') return;
    var m = marca(sel.i, sel.f), v = e.target.value.trim(); if (v === (m.otros || '')) return;
    guardar(sel.i, sel.f, { tipo: String(m.tipo), razon: String(m.razon || razonPendiente || ''), otros: v });
  });

  cont.addEventListener('click', function (e) {
    var b = e.target.closest('.as-cel'); if (!b) return;
    detalle(+b.dataset.i, b.dataset.f);
    poner(b, siguiente(marca(+b.dataset.i, b.dataset.f).tipo));
  });
  cont.addEventListener('focusin', function (e) { var b = e.target.closest('.as-cel'); if (b) detalle(+b.dataset.i, b.dataset.f); });
  cont.addEventListener('keydown', function (e) {
    var b = e.target.closest('.as-cel'); if (!b) return;
    var k = e.key, i = +b.dataset.i, f = b.dataset.f, col = fechas.indexOf(f);
    if (k === 'ArrowDown' || k === 'ArrowUp' || k === 'ArrowLeft' || k === 'ArrowRight') {
      e.preventDefault();
      var ni = i + (k === 'ArrowDown' ? 1 : k === 'ArrowUp' ? -1 : 0), nc = col + (k === 'ArrowRight' ? 1 : k === 'ArrowLeft' ? -1 : 0);
      var dest = fechas[nc] && cont.querySelector('.as-cel[data-i="' + ni + '"][data-f="' + fechas[nc] + '"]'); if (dest) dest.focus();
      return;
    }
    if (k === 'x' || k === 'X' || k === 'Delete' || k === 'Backspace') { e.preventDefault(); poner(b, ''); return; }
    var t = tipos.filter(function (x) { return (letra[x.id] || '').charAt(0).toLowerCase() === k.toLowerCase(); })[0];
    if (t) { e.preventDefault(); poner(b, t.id); }
  });

  selClase.addEventListener('change', cargar);
  inpFecha.addEventListener('change', cargar);
  selDias.addEventListener('change', cargar);
})();
