/* <--- hecho por claude code: Ingreso de Notas — tab Tareas.
   (06-nov-2026, diseño A «Planilla»): las tareas del día son COLUMNAS (Tarea 1, Tarea 2…) con promedio por alumno
   y promedio del grupo por tarea. «＋ Nueva tarea» abre la siguiente columna en blanco.

   Regla del legacy que se respeta: no guarda identificador de tarea (solo Fecha, Puntos y Comentario), así que dos
   tareas del mismo día se distinguen por el orden de inserción. El servidor rechaza la Tarea N de un alumno si le
   falta la anterior: por eso se llena de izquierda a derecha y solo hay UNA columna nueva a la vez. */
(function () {
  var d = document.getElementById('notas-config');
  if (!d) return;
  var C = {
    urlClases:  d.dataset.v0,
    area:       d.dataset.v3,
    csrf:       d.dataset.v4,
    urlTareas:  d.dataset.v5,
    urlGuardar: d.dataset.v6
  };

  var selGrado = document.getElementById('tr-grado');
  var selClase = document.getElementById('tr-clase');
  var inpFecha = document.getElementById('tr-fecha');
  var selTarea = document.getElementById('tr-tarea');
  var btnNueva = document.getElementById('tr-nueva');
  var cont     = document.getElementById('tr-cont');
  var titulo   = document.getElementById('tr-titulo');
  var estado   = document.getElementById('tr-estado');
  var aviso    = document.getElementById('tr-aviso');
  if (!selGrado || !cont) return;
  // el selector de tarea ya no hace falta: todas las tareas del día van como columnas
  if (selTarea) { var wrapSel = selTarea.closest('[class*="col-"]'); if (wrapSel) wrapSel.hidden = true; }

  var nTareas = 0, nColumnas = 1, puntosMax = 10, alumnos = [], conComentarios = false;
  var MINIMO = 6;

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function pinta(txt, clase) { estado.className = 'small ' + (clase || 'text-muted'); estado.innerHTML = txt; }
  function avisar(txt, tipo) {
    aviso.innerHTML = txt ? '<div class="alert alert-' + (tipo || 'warning') + ' py-2 mb-0 small">' + txt + '</div>' : '';
  }
  function partesGrado() { var v = (selGrado.value || '').split('|'); return { grado: v[0] || '', grupo: v[1] || '' }; }
  function vaciar(msg) {
    cont.innerHTML = '<div class="card-body text-center text-muted py-5"><i class="ti ti-hand-click" style="font-size:2rem"></i><div class="mt-2">' + msg + '</div></div>';
    titulo.textContent = 'Participantes';
  }
  function cargando(msg) { cont.innerHTML = '<div class="card-body text-center text-muted py-5"><span class="spinner-border spinner-border-sm me-2"></span>' + msg + '</div>'; }

  // ── Cascada grado -> clase ──
  selGrado.addEventListener('change', function () {
    var g = partesGrado();
    selClase.innerHTML = '<option value="">Cargando…</option>';
    selClase.disabled = true; btnNueva.disabled = true;
    vaciar('Elige la clase para registrar tareas.');
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

  function urlTarea(n) {
    var g = partesGrado();
    return C.urlTareas + '?area=' + encodeURIComponent(C.area) + '&grado=' + encodeURIComponent(g.grado) +
      '&grupo=' + encodeURIComponent(g.grupo) + '&materia=' + encodeURIComponent(selClase.value) +
      '&fecha=' + encodeURIComponent(inpFecha.value) + '&tarea=' + n;
  }
  function pedir(n) { return fetch(urlTarea(n)).then(function (r) { return r.json(); }); }

  // ── Carga: la Tarea 1 trae cuántas hay; luego se piden las demás en paralelo ──
  function cargar() {
    var g = partesGrado();
    if (!g.grado || !selClase.value) { vaciar('Elige grado y clase para registrar tareas.'); return; }
    if (!inpFecha.value) { avisar('Elige una fecha.'); return; }
    avisar(''); cargando('Cargando alumnos…');
    pedir(1).then(function (d1) {
      if (!d1.ok) { cont.innerHTML = '<div class="card-body"><div class="alert alert-warning mb-0">' + esc(d1.error) + '</div></div>'; return; }
      nTareas = d1.n_tareas; puntosMax = d1.puntos_max || 10;
      nColumnas = Math.max(1, nTareas);
      var resto = []; for (var k = 2; k <= nTareas; k++) resto.push(pedir(k));
      return Promise.all(resto).then(function (otras) {
        var todas = [d1].concat(otras);
        alumnos = d1.alumnos.map(function (a) {
          return { nombre: a.nombre, identidad: a.identidad, materia_id: a.materia_id, t: {} };
        });
        todas.forEach(function (dd, k) {
          if (!dd || !dd.ok) return;
          dd.alumnos.forEach(function (a, i) {
            var al = alumnos[i];
            if (al && al.nombre === a.nombre) al.t[k + 1] = { puntos: a.puntos, comentario: a.comentario, rec: !!a.rec_id };
          });
        });
        if (d1.desiguales) avisar('<i class="ti ti-alert-triangle me-1"></i>Ese día no todos los alumnos tienen la misma cantidad de tareas. Revisa que no falte ninguna antes de seguir.');
        btnNueva.disabled = false;
        pintar();
      });
    }).catch(function () {
      cont.innerHTML = '<div class="card-body"><div class="alert alert-danger mb-0">Error de conexión.</div></div>';
    });
  }

  function pintar() {
    var clase = selClase.options[selClase.selectedIndex].text.replace(/\s*\(\d+\)$/, '');
    titulo.innerHTML = esc(clase) + ' · ' + esc(inpFecha.value.split('-').reverse().join('/')) + ' · ' + alumnos.length + ' alumno(s) ' +
      '<label class="tr-toggle ms-2"><input type="checkbox" id="tr-coms"' + (conComentarios ? ' checked' : '') + '> Comentarios</label>';
    if (!alumnos.length) { vaciar('No hay alumnos en esa clase.'); return; }

    var h = '<div class="table-responsive"><table class="table table-vcenter table-sm mb-0 tabla-notas planilla-tareas' + (conComentarios ? ' con-coms' : '') + '">' +
      '<thead><tr><th class="col-no">No</th><th class="col-alumno">Participante</th>';
    for (var k = 1; k <= nColumnas; k++) {
      h += '<th class="text-center col-tarea' + (k > nTareas ? ' col-nueva' : '') + '">Tarea ' + k + (k > nTareas ? ' <small>(nueva)</small>' : '') + '</th>';
    }
    h += '<th class="text-center col-prom">Promedio</th></tr></thead><tbody>';
    alumnos.forEach(function (a, i) {
      var com = ' data-materia="' + a.materia_id + '" data-alumno="' + esc(a.nombre) + '"';
      h += '<tr><td class="text-muted">' + (i + 1) + '</td><td><div class="fw-medium">' + esc(a.nombre) + '</div>' +
        '<div class="text-muted small font-monospace">' + esc(a.identidad) + '</div></td>';
      for (var k = 1; k <= nColumnas; k++) {
        var t = a.t[k] || { puntos: '', comentario: '', rec: false };
        // <--- hecho por claude code (06-nov-2026): la Tarea k se bloquea mientras al alumno le falte la k-1 (el servidor la rechazaría)
        var bloq = k > 1 && !t.rec && !(a.t[k - 1] && a.t[k - 1].rec);
        var dis = bloq ? ' disabled title="Primero la Tarea ' + (k - 1) + ' de este alumno"' : '';
        h += '<td class="p-1 td-tarea"><input type="text" inputmode="numeric" class="form-control form-control-sm text-center celda-tarea" data-campo="puntos" data-tarea="' + k + '"' +
          com + dis + ' value="' + esc(t.puntos) + '"' + (bloq ? ' placeholder="falta T' + (k - 1) + '"' : '') + ' aria-label="Tarea ' + k + ' de ' + esc(a.nombre) + '">' +
          '<input type="text" class="form-control form-control-sm celda-tarea celda-com" data-campo="comentario" data-tarea="' + k + '"' +
          com + dis + ' value="' + esc(t.comentario) + '"' + (t.rec ? '' : ' placeholder="Primero los puntos"') + ' aria-label="Comentario tarea ' + k + '"></td>';
      }
      h += '<td class="text-center td-prom">—</td></tr>';
    });
    h += '</tbody><tfoot><tr><td></td><td class="tf-lbl">Promedio del grupo</td>';
    for (var k2 = 1; k2 <= nColumnas; k2++) h += '<td class="text-center tf-col" data-tarea="' + k2 + '">—</td>';
    h += '<td class="text-center tf-prom">—</td></tr></tfoot></table></div>' +
      '<div class="tr-pie small text-muted"><i class="ti ti-info-circle me-1"></i>Puntos enteros de 1 a ' + puntosMax + '. Se guardan solos al salir de cada casilla · Tab avanza · Enter baja en la misma columna. Llena las tareas de izquierda a derecha.</div>';
    cont.innerHTML = h;
    recalcular();
  }

  // lo que hay en las casillas pasa a los datos antes de volver a dibujar
  function sincronizar() {
    cont.querySelectorAll('tbody tr').forEach(function (tr, i) {
      var a = alumnos[i]; if (!a) return;
      tr.querySelectorAll('.celda-tarea').forEach(function (inp) {
        var k = inp.dataset.tarea, t = a.t[k] || (a.t[k] = { puntos: '', comentario: '', rec: false });
        t[inp.dataset.campo] = inp.value;
        if (inp.dataset.campo === 'puntos' && inp.classList.contains('celda-ok')) t.rec = true;
      });
    });
  }

  function recalcular() {
    var P = TC_PLANILLA, todos = [];
    cont.querySelectorAll('tbody tr').forEach(function (tr) {
      var p = P.prom([].map.call(tr.querySelectorAll('.celda-tarea[data-campo="puntos"]'), function (i) { return P.num(i.value); }));
      var td = tr.querySelector('.td-prom'); if (!td) return;
      td.textContent = P.fmt(p); td.classList.toggle('prom-baja', p !== null && p < MINIMO);
      if (p !== null) todos.push(p);
    });
    cont.querySelectorAll('tfoot .tf-col').forEach(function (td) {
      var p = P.prom([].map.call(cont.querySelectorAll('.celda-tarea[data-campo="puntos"][data-tarea="' + td.dataset.tarea + '"]'), function (i) { return P.num(i.value); }));
      td.textContent = P.fmt(p);
    });
    var tp = cont.querySelector('.tf-prom'); if (tp) tp.textContent = P.fmt(P.prom(todos));
    P.marcarBajas(cont, '.celda-tarea[data-campo="puntos"]', MINIMO);
  }

  // ── Autoguardado por celda (mismo endpoint de siempre, con la tarea de la columna) ──
  cont.addEventListener('focusin', function (e) {
    if (e.target.classList && e.target.classList.contains('celda-tarea')) {
      e.target.dataset.antes = e.target.value.trim();
      if (e.target.dataset.campo === 'puntos') e.target.select();
    }
  });
  cont.addEventListener('input', function (e) { if (e.target.classList.contains('celda-tarea')) recalcular(); });
  titulo.addEventListener('change', function (e) {
    if (e.target.id !== 'tr-coms') return;
    conComentarios = e.target.checked;
    var t = cont.querySelector('.planilla-tareas'); if (t) t.classList.toggle('con-coms', conComentarios);
  });

  cont.addEventListener('focusout', function (e) {
    var inp = e.target;
    if (!inp.classList || !inp.classList.contains('celda-tarea')) return;
    var actual = inp.value.trim();
    if (actual === (inp.dataset.antes || '')) return;
    inp.classList.remove('celda-ok', 'celda-error');
    inp.classList.add('celda-guardando');
    pinta('<i class="ti ti-loader-2 me-1"></i>Guardando…');
    fetch(C.urlGuardar, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': C.csrf },
      credentials: 'same-origin',
      body: JSON.stringify({
        area: C.area, materia_id: inp.dataset.materia, fecha: inpFecha.value,
        tarea: inp.dataset.tarea, campo: inp.dataset.campo, valor: actual, alumno: inp.dataset.alumno
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        inp.classList.remove('celda-guardando');
        if (!dd.ok) {
          TC_PLANILLA.rechazo(inp, dd.error || 'error');
          recalcular();
          pinta('<i class="ti ti-alert-triangle me-1"></i>' + esc(dd.error), 'text-danger');
          return;
        }
        inp.classList.add('celda-ok'); inp.removeAttribute('title');
        inp.dataset.antes = actual;
        TC_PLANILLA.burbuja(inp);
        if (dd.accion === 'insert') {
          var td = inp.closest('td'), comI = td ? td.querySelector('[data-campo="comentario"]') : null;
          if (comI) comI.placeholder = '';
          // ya existe esta tarea: se desbloquea la siguiente de este alumno
          var fila = inp.closest('tr'), sigT = parseInt(inp.dataset.tarea, 10) + 1;
          if (fila) fila.querySelectorAll('.celda-tarea[data-tarea="' + sigT + '"]').forEach(function (x) {
            x.disabled = false; x.removeAttribute('title'); if (x.dataset.campo === 'puntos') x.placeholder = '';
          });
          var k = parseInt(inp.dataset.tarea, 10);
          if (k > nTareas) {   // la columna nueva ya existe en el sistema académico
            nTareas = k;
            var th = cont.querySelectorAll('thead .col-tarea')[k - 1];
            if (th) { th.classList.remove('col-nueva'); th.innerHTML = 'Tarea ' + k; }
          }
        }
        pinta('<i class="ti ti-check me-1"></i>Guardado', 'text-green');
      })
      .catch(function () {
        TC_PLANILLA.rechazo(inp, 'sin conexión');
        recalcular();
        pinta('<i class="ti ti-cloud-off me-1"></i>Sin conexión — no se guardó', 'text-danger');
      });
  });

  // Enter baja a la misma casilla de la fila siguiente
  cont.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || !e.target.classList.contains('celda-tarea')) return;
    e.preventDefault();
    var fila = e.target.closest('tr'), sig = fila && fila.nextElementSibling;
    if (!sig) return;
    var inp = sig.querySelector('.celda-tarea[data-campo="' + e.target.dataset.campo + '"][data-tarea="' + e.target.dataset.tarea + '"]');
    if (inp) inp.focus();
  });

  // ── Nueva tarea: una sola columna en blanco a la vez (la siguiente del día) ──
  btnNueva.addEventListener('click', function () {
    if (!selClase.value || !alumnos.length) { avisar('Elige primero la clase.'); return; }
    if (nColumnas > nTareas) { avisar('Ya está abierta la Tarea ' + nColumnas + ': llénala antes de abrir otra.', 'info'); return; }
    sincronizar(); nColumnas = nTareas + 1; avisar(''); pintar();
    var primera = cont.querySelector('.celda-tarea[data-campo="puntos"][data-tarea="' + nColumnas + '"]');
    if (primera) primera.focus();
  });

  selClase.addEventListener('change', cargar);
  inpFecha.addEventListener('change', cargar);
})();
