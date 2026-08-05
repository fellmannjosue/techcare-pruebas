/* <--- hecho por claude code: Ingreso de Notas — tab Record de Hábitos.

   Los 5 hábitos van como COLUMNAS (Espíritu de Trabajo, Orden y Presentación,
   Moralidad, Sociabilidad, ExpresionesADH) porque en la práctica se registran
   juntos el mismo día: verificado que las fechas con datos traen los 5.

   El comentario es uno por alumno y día, no por hábito: apenas se usa (3,4 % en
   bilingüe, 0 % en colegio) y cuando aparece es la misma etiqueta repetida en
   los 5 ("III PARCIAL"), así que al guardarlo se aplica a todos. */
(function () {
  var d = document.getElementById('notas-config');
  if (!d) return;
  var C = {
    urlClases:  d.dataset.v0,
    area:       d.dataset.v3,
    csrf:       d.dataset.v4,
    urlHabitos: d.dataset.v9,
    urlGuardar: d.dataset.v10
  };

  var selGrado = document.getElementById('hb-grado');
  var selClase = document.getElementById('hb-clase');
  var inpFecha = document.getElementById('hb-fecha');
  var cont     = document.getElementById('hb-cont');
  var titulo   = document.getElementById('hb-titulo');
  var estado   = document.getElementById('hb-estado');
  if (!selGrado || !cont) return;

  var habitos = [], puntosMax = 10;

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function pinta(txt, clase) {
    estado.className = 'small ' + (clase || 'text-muted');
    estado.innerHTML = txt;
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

  // ── Cascada grado -> clase ──
  selGrado.addEventListener('change', function () {
    var g = partesGrado();
    selClase.innerHTML = '<option value="">Cargando…</option>';
    selClase.disabled = true;
    vaciar('Elige la clase para registrar los hábitos.');
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

  // ── Rejilla ──
  function cargar() {
    var g = partesGrado();
    if (!g.grado || !selClase.value) { vaciar('Elige grado y clase para registrar los hábitos.'); return; }
    if (!inpFecha.value) return;
    cont.innerHTML = '<div class="card-body text-center text-muted py-5">' +
      '<span class="spinner-border spinner-border-sm me-2"></span>Cargando alumnos…</div>';

    var qs = '?area=' + encodeURIComponent(C.area) +
             '&grado=' + encodeURIComponent(g.grado) + '&grupo=' + encodeURIComponent(g.grupo) +
             '&materia=' + encodeURIComponent(selClase.value) +
             '&fecha=' + encodeURIComponent(inpFecha.value);

    fetch(C.urlHabitos + qs)
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        if (!dd.ok) {
          cont.innerHTML = '<div class="card-body"><div class="alert alert-warning mb-0">' +
            esc(dd.error) + '</div></div>';
          return;
        }
        habitos = dd.habitos; puntosMax = dd.puntos_max;
        pintar(dd.alumnos, dd.con_datos);
      })
      .catch(function () {
        cont.innerHTML = '<div class="card-body"><div class="alert alert-danger mb-0">' +
          'Error de conexión.</div></div>';
      });
  }

  function pintar(alumnos, conDatos) {
    var clase = selClase.options[selClase.selectedIndex].text.replace(/\s*\(\d+\)$/, '');
    titulo.innerHTML = esc(clase) + ' · ' + inpFecha.value.split('-').reverse().join('/') +
      ' · ' + alumnos.length + ' alumno(s) ' +
      '<span class="badge bg-azure-lt ms-2">' + conDatos + ' con registro</span>';

    if (!alumnos.length) { vaciar('No hay alumnos en esa clase.'); return; }

    var h = '<div class="table-responsive"><table class="table table-vcenter table-sm mb-0 tabla-notas">' +
      '<thead><tr><th class="col-no">No</th><th class="col-alumno">Participante</th>';
    habitos.forEach(function (hb) {
      h += '<th class="text-center col-nota" title="' + esc(hb.label) + '">' + esc(hb.label) + '</th>';
    });
    h += '<th>Comentario</th></tr></thead><tbody>';

    alumnos.forEach(function (a, i) {
      var com = ' data-materia="' + a.materia_id + '" data-alumno="' + esc(a.nombre) + '"';
      h += '<tr><td class="text-muted">' + (i + 1) + '</td>' +
        '<td><div class="fw-medium">' + esc(a.nombre) + '</div>' +
          '<div class="text-muted small font-monospace">' + esc(a.identidad) + '</div></td>';
      habitos.forEach(function (hb) {
        h += '<td class="p-1"><input type="text" inputmode="numeric"' +
             ' class="form-control form-control-sm text-center celda-habito" data-campo="puntos"' +
             ' data-habito="' + hb.id + '"' + com +
             ' value="' + esc(a.puntos[String(hb.id)]) + '"></td>';
      });
      h += '<td class="p-1"><input type="text" class="form-control form-control-sm celda-habito"' +
           ' data-campo="comentario"' + com + ' value="' + esc(a.comentario) + '"' +
           ' placeholder="Aplica a los hábitos del día"></td></tr>';
    });
    cont.innerHTML = h + '</tbody></table></div>';
  }

  // ── Autoguardado por celda ──
  cont.addEventListener('focusin', function (e) {
    if (e.target.classList && e.target.classList.contains('celda-habito')) {
      e.target.dataset.antes = e.target.value.trim();
      if (e.target.dataset.campo === 'puntos') e.target.select();
    }
  });

  cont.addEventListener('focusout', function (e) {
    var inp = e.target;
    if (!inp.classList || !inp.classList.contains('celda-habito')) return;
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
        campo: inp.dataset.campo, habito: inp.dataset.habito || null,
        valor: actual, alumno: inp.dataset.alumno
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
    if (e.key !== 'Enter' || !e.target.classList.contains('celda-habito')) return;
    e.preventDefault();
    var td = e.target.closest('td');
    var fila = td.closest('tr');
    var idx = Array.prototype.indexOf.call(fila.children, td);
    var sig = fila.nextElementSibling;
    if (sig && sig.children[idx]) {
      var inp = sig.children[idx].querySelector('.celda-habito');
      if (inp) inp.focus();
    }
  });

  selClase.addEventListener('change', cargar);
  inpFecha.addEventListener('change', cargar);
})();
