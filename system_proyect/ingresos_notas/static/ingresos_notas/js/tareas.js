/* <--- hecho por claude code: Ingreso de Notas — tab Tareas.

   Una tarea a la vez: se elige clase y fecha, y la rejilla muestra a TODOS los
   alumnos con sus puntos (0-10) y comentario. Autoguardado por celda.

   Por qué "una a la vez": el legacy no guarda ningún identificador de tarea
   (solo Fecha, Puntos y Comentario), así que dos tareas del mismo día solo se
   distinguen por el orden de inserción. Llenando una completa antes de crear la
   siguiente, la posición N es la misma tarea para todos los alumnos. */
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

  var nTareas = 0;      // cuántas hay ya ese día
  var puntosMax = 10;

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function pinta(txt, clase) {
    estado.className = 'small ' + (clase || 'text-muted');
    estado.innerHTML = txt;
  }
  function avisar(txt, tipo) {
    aviso.innerHTML = txt
      ? '<div class="alert alert-' + (tipo || 'warning') + ' py-2 mb-0 small">' + txt + '</div>'
      : '';
  }
  function partesGrado() {
    var v = (selGrado.value || '').split('|');
    return { grado: v[0] || '', grupo: v[1] || '' };
  }
  function vaciar(msg) {
    cont.innerHTML = '<div class="card-body text-center text-muted py-5">' +
      '<i class="ti ti-hand-click" style="font-size:2rem"></i><div class="mt-2">' + msg + '</div></div>';
    titulo.textContent = 'Participantes';
  }
  function cargando(msg) {
    cont.innerHTML = '<div class="card-body text-center text-muted py-5">' +
      '<span class="spinner-border spinner-border-sm me-2"></span>' + msg + '</div>';
  }

  // ── Cascada grado -> clase (independiente de la del tab de notas) ──
  selGrado.addEventListener('change', function () {
    var g = partesGrado();
    selClase.innerHTML = '<option value="">Cargando…</option>';
    selClase.disabled = true;
    vaciar('Elige la clase para registrar tareas.');
    if (!g.grado) {
      selClase.innerHTML = '<option value="">— Elige primero el grado —</option>';
      return;
    }
    fetch(C.urlClases + '?area=' + encodeURIComponent(C.area) +
          '&grado=' + encodeURIComponent(g.grado) + '&grupo=' + encodeURIComponent(g.grupo))
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        if (!dd.ok) { selClase.innerHTML = '<option value="">' + esc(dd.error) + '</option>'; return; }
        var h = '<option value="">— Seleccionar —</option>';
        dd.clases.forEach(function (cl) {
          h += '<option value="' + esc(cl.id) + '">' + esc(cl.nombre) + ' (' + cl.alumnos + ')</option>';
        });
        selClase.innerHTML = h;
        selClase.disabled = false;
      })
      .catch(function () { selClase.innerHTML = '<option value="">Error de conexión</option>'; });
  });

  // ── Carga de la rejilla ──
  function cargar(tareaPedida) {
    var g = partesGrado();
    if (!g.grado || !selClase.value) { vaciar('Elige grado y clase para registrar tareas.'); return; }
    if (!inpFecha.value) { avisar('Elige una fecha.'); return; }
    avisar('');
    cargando('Cargando alumnos…');

    var qs = '?area=' + encodeURIComponent(C.area) +
             '&grado=' + encodeURIComponent(g.grado) + '&grupo=' + encodeURIComponent(g.grupo) +
             '&materia=' + encodeURIComponent(selClase.value) +
             '&fecha=' + encodeURIComponent(inpFecha.value) +
             '&tarea=' + encodeURIComponent(tareaPedida || 0);

    fetch(C.urlTareas + qs)
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        if (!dd.ok) {
          cont.innerHTML = '<div class="card-body"><div class="alert alert-warning mb-0">' +
            esc(dd.error) + '</div></div>';
          return;
        }
        nTareas = dd.n_tareas;
        puntosMax = dd.puntos_max;
        llenarSelectorTareas(dd.tarea);
        if (dd.desiguales) {
          avisar('<i class="ti ti-alert-triangle me-1"></i>Ese día no todos los alumnos ' +
                 'tienen la misma cantidad de tareas. Revisa que no falte ninguna antes de seguir.');
        }
        pintar(dd.alumnos, dd.tarea);
      })
      .catch(function () {
        cont.innerHTML = '<div class="card-body"><div class="alert alert-danger mb-0">' +
          'Error de conexión.</div></div>';
      });
  }

  // El selector ofrece las tareas del día; si no hay ninguna, la primera a crear
  function llenarSelectorTareas(actual) {
    var total = Math.max(nTareas, 1);
    var h = '';
    for (var i = 1; i <= total; i++) {
      h += '<option value="' + i + '"' + (i === actual ? ' selected' : '') + '>Tarea ' + i +
           (i > nTareas ? ' (nueva)' : '') + '</option>';
    }
    selTarea.innerHTML = h;
    selTarea.disabled = false;
    btnNueva.disabled = false;
  }

  function pintar(alumnos, tarea) {
    var clase = selClase.options[selClase.selectedIndex].text.replace(/\s*\(\d+\)$/, '');
    titulo.textContent = clase + ' · Tarea ' + tarea + ' del ' +
      inpFecha.value.split('-').reverse().join('/') + ' · ' + alumnos.length + ' alumno(s)';

    if (!alumnos.length) { vaciar('No hay alumnos en esa clase.'); return; }

    var h = '<div class="table-responsive"><table class="table table-vcenter table-sm mb-0 tabla-notas">' +
      '<thead><tr><th class="col-no">No</th><th class="col-alumno">Participante</th>' +
      '<th class="text-center" style="width:110px">Puntos</th>' +
      '<th>Comentario</th></tr></thead><tbody>';

    alumnos.forEach(function (a, i) {
      var comunes = ' data-materia="' + a.materia_id + '" data-alumno="' + esc(a.nombre) + '"';
      h += '<tr><td class="text-muted">' + (i + 1) + '</td>' +
        '<td><div class="fw-medium">' + esc(a.nombre) + '</div>' +
          '<div class="text-muted small font-monospace">' + esc(a.identidad) + '</div></td>' +
        '<td class="p-1"><input type="text" inputmode="numeric"' +
          ' class="form-control form-control-sm text-center celda-tarea" data-campo="puntos"' +
          comunes + ' value="' + esc(a.puntos) + '"></td>' +
        '<td class="p-1"><input type="text"' +
          ' class="form-control form-control-sm celda-tarea" data-campo="comentario"' +
          comunes + ' value="' + esc(a.comentario) + '"' +
          (a.rec_id ? '' : ' placeholder="Pon primero los puntos"') + '></td></tr>';
    });
    cont.innerHTML = h + '</tbody></table></div>';
  }

  // ── Autoguardado por celda ──
  cont.addEventListener('focusin', function (e) {
    if (e.target.classList && e.target.classList.contains('celda-tarea')) {
      e.target.dataset.antes = e.target.value.trim();
      if (e.target.dataset.campo === 'puntos') e.target.select();
    }
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
        tarea: selTarea.value, campo: inp.dataset.campo, valor: actual,
        alumno: inp.dataset.alumno
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        inp.classList.remove('celda-guardando');
        if (!dd.ok) {
          inp.classList.add('celda-error');
          inp.value = inp.dataset.antes || '';
          pinta('<i class="ti ti-alert-triangle me-1"></i>' + esc(dd.error), 'text-danger');
          return;
        }
        inp.classList.add('celda-ok');
        inp.dataset.antes = actual;
        // Al crear la primera fila del alumno ya se puede comentar
        if (dd.accion === 'insert') {
          var fila = inp.closest('tr');
          var com = fila ? fila.querySelector('[data-campo="comentario"]') : null;
          if (com) com.placeholder = '';
          if (selTarea.value > nTareas) nTareas = parseInt(selTarea.value, 10);
        }
        pinta('<i class="ti ti-check me-1"></i>Guardado', 'text-green');
      })
      .catch(function () {
        inp.classList.remove('celda-guardando');
        inp.classList.add('celda-error');
        inp.value = inp.dataset.antes || '';
        pinta('<i class="ti ti-cloud-off me-1"></i>Sin conexión — no se guardó', 'text-danger');
      });
  });

  // Enter baja a la misma columna de la fila siguiente
  cont.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || !e.target.classList.contains('celda-tarea')) return;
    e.preventDefault();
    var td = e.target.closest('td');
    var fila = td.closest('tr');
    var idx = Array.prototype.indexOf.call(fila.children, td);
    var sig = fila.nextElementSibling;
    if (sig && sig.children[idx]) {
      var inp = sig.children[idx].querySelector('.celda-tarea');
      if (inp) inp.focus();
    }
  });

  // ── Nueva tarea: se abre la siguiente posición del día, en blanco ──
  btnNueva.addEventListener('click', function () {
    if (!selClase.value) { avisar('Elige primero la clase.'); return; }
    cargar(nTareas + 1);
  });

  selClase.addEventListener('change', function () { cargar(0); });
  inpFecha.addEventListener('change', function () { cargar(0); });
  selTarea.addEventListener('change', function () { cargar(parseInt(selTarea.value, 10)); });
})();
