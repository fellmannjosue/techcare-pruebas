/* <--- hecho por claude code: Ingreso de Notas — rejilla estilo CFP.
   Desplegables en cascada (grado -> clase) y autoguardado por celda: cada casilla
   escribe UNA columna en el sistema académico al salir del campo. */
const CFG_INGRESOS_NOTAS = (function () {
  var d = document.getElementById('notas-config').dataset;
  return { urlClases: d.v0, urlAlumnos: d.v1, urlGuardar: d.v2, area: d.v3, csrf: d.v4 };
})();

(function () {
  var C = CFG_INGRESOS_NOTAS;
  var selGrado   = document.getElementById('sel-grado');
  var selClase   = document.getElementById('sel-clase');
  var selParcial = document.getElementById('sel-parcial');
  var selCuadros = document.getElementById('sel-cuadros');
  var cont       = document.getElementById('rejilla-cont');
  var titulo     = document.getElementById('rejilla-titulo');
  var estado     = document.getElementById('tc-estado');
  if (!selGrado || !cont) return;

  var columnas = [];

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
  // <--- hecho por claude code: las etiquetas y CUÁNTAS columnas las manda el
  // servidor: cada clase usa una cantidad distinta de cuadros (de 2 a 19).
  function cargando(msg) {
    cont.innerHTML = '<div class="card-body text-center text-muted py-5">' +
      '<span class="spinner-border spinner-border-sm me-2"></span>' + msg + '</div>';
  }

  // ── Cascada: al elegir grado se piden sus clases ──
  selGrado.addEventListener('change', function () {
    var g = partesGrado();
    selClase.innerHTML = '<option value="">Cargando…</option>';
    selClase.disabled = true;
    vaciarRejilla('Elige la clase para ver a los alumnos.');
    if (!g.grado) { selClase.innerHTML = '<option value="">— Elige primero el grado —</option>'; return; }

    fetch(C.urlClases + '?area=' + encodeURIComponent(C.area) +
          '&grado=' + encodeURIComponent(g.grado) + '&grupo=' + encodeURIComponent(g.grupo))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { selClase.innerHTML = '<option value="">' + esc(d.error) + '</option>'; return; }
        var h = '<option value="">— Seleccionar —</option>';
        d.clases.forEach(function (cl) {
          h += '<option value="' + esc(cl.id) + '">' + esc(cl.nombre) +
               ' (' + cl.alumnos + ')</option>';
        });
        selClase.innerHTML = h;
        selClase.disabled = false;
      })
      .catch(function () { selClase.innerHTML = '<option value="">Error de conexión</option>'; });
  });

  function vaciarRejilla(msg) {
    cont.innerHTML = '<div class="card-body text-center text-muted py-5">' +
      '<i class="ti ti-hand-click" style="font-size:2rem"></i><div class="mt-2">' + msg + '</div></div>';
    titulo.textContent = 'Participantes';
  }

  // ── Rejilla ──
  function cargarAlumnos() {
    var g = partesGrado();
    if (!g.grado || !selClase.value) { vaciarRejilla('Elige grado y clase para ver a los alumnos.'); return; }
    cargando('Cargando alumnos…');
    var qs = '?area=' + encodeURIComponent(C.area) +
             '&grado=' + encodeURIComponent(g.grado) + '&grupo=' + encodeURIComponent(g.grupo) +
             '&materia=' + encodeURIComponent(selClase.value) +
             '&parcial=' + encodeURIComponent(selParcial.value) +
             '&cuadros=' + encodeURIComponent(selCuadros.value || '');
    fetch(C.urlAlumnos + qs)
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) {
          cont.innerHTML = '<div class="card-body"><div class="alert alert-warning mb-0">' +
            esc(d.error) + '</div></div>';
          return;
        }
        columnas = d.columnas;
        // Si el usuario no forzó un número, se muestra el que decidió la clase.
        if (!selCuadros.value) selCuadros.placeholder = 'auto (' + d.n_cuadros_auto + ')';
        pintarRejilla(d.alumnos);
      })
      .catch(function () {
        cont.innerHTML = '<div class="card-body"><div class="alert alert-danger mb-0">Error de conexión.</div></div>';
      });
  }

  function pintarRejilla(alumnos) {
    var clase = selClase.options[selClase.selectedIndex].text.replace(/\s*\(\d+\)$/, '');
    titulo.textContent = clase + ' · Parcial ' + selParcial.value + ' · ' + alumnos.length + ' alumno(s)';

    if (!alumnos.length) {
      vaciarRejilla('No hay alumnos en esa clase.');
      return;
    }
    var h = '<div class="table-responsive"><table class="table table-vcenter table-sm mb-0 tabla-notas">' +
      '<thead><tr><th class="col-no">No</th><th class="col-alumno">Participante</th>';
    columnas.forEach(function (col) {
      // La evaluación continua se resalta para que no se confunda con un cuadro más
      var ec = /^ExamenFinal[234]$/.test(col.key) ? ' col-evalconti' : '';
      h += '<th class="text-center col-nota' + ec + '" title="' + esc(col.key) + '">' +
           esc(col.label) + '</th>';
    });
    h += '</tr></thead><tbody>';

    alumnos.forEach(function (a, i) {
      h += '<tr' + (a.no_participa ? ' class="fila-no-participa" title="Marcado como No Participa"' : '') + '>' +
        '<td class="text-muted">' + (i + 1) + '</td>' +
        '<td><div class="fw-medium">' + esc(a.nombre) + '</div>' +
          '<div class="text-muted small font-monospace">' + esc(a.identidad) + '</div></td>';
      columnas.forEach(function (col) {
        var v = a.notas[col.key];
        var ec = /^ExamenFinal[234]$/.test(col.key) ? ' celda-evalconti' : '';
        h += '<td class="p-1"><input type="text" inputmode="decimal" class="form-control form-control-sm text-center celda-nota' + ec + '"' +
             ' value="' + (v === '' || v == null ? '' : v) + '"' +
             ' data-materia="' + a.materia_id + '" data-col="' + esc(col.key) + '"' +
             ' data-alumno="' + esc(a.nombre) + '"></td>';
      });
      h += '</tr>';
    });
    h += '</tbody></table></div>';
    cont.innerHTML = h;
  }

  // ── Autoguardado por celda ──
  cont.addEventListener('focusin', function (e) {
    if (e.target.classList && e.target.classList.contains('celda-nota')) {
      e.target.dataset.antes = e.target.value.trim();
      e.target.select();
    }
  });

  cont.addEventListener('focusout', function (e) {
    var inp = e.target;
    if (!inp.classList || !inp.classList.contains('celda-nota')) return;
    var actual = inp.value.trim();
    if (actual === (inp.dataset.antes || '')) return;    // no cambió: no se escribe

    inp.classList.remove('celda-ok', 'celda-error');
    inp.classList.add('celda-guardando');
    pinta('<i class="ti ti-loader-2 me-1"></i>Guardando…');

    fetch(C.urlGuardar, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': C.csrf },
      credentials: 'same-origin',
      body: JSON.stringify({
        area: C.area, materia_id: inp.dataset.materia, parcial: selParcial.value,
        columna: inp.dataset.col, valor: actual, alumno: inp.dataset.alumno
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        inp.classList.remove('celda-guardando');
        if (!d.ok) {
          inp.classList.add('celda-error');
          inp.value = inp.dataset.antes || '';           // se revierte lo escrito
          pinta('<i class="ti ti-alert-triangle me-1"></i>' + esc(d.error), 'text-danger');
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

  // Enter baja a la misma columna de la fila siguiente (como una hoja de cálculo)
  cont.addEventListener('keydown', function (e) {
    if (e.key !== 'Enter' || !e.target.classList.contains('celda-nota')) return;
    e.preventDefault();
    var td = e.target.closest('td');
    var fila = td.closest('tr');
    var idx = Array.prototype.indexOf.call(fila.children, td);
    var sig = fila.nextElementSibling;
    if (sig && sig.children[idx]) {
      var inp = sig.children[idx].querySelector('.celda-nota');
      if (inp) inp.focus();
    }
  });

  selClase.addEventListener('change', cargarAlumnos);
  selParcial.addEventListener('change', cargarAlumnos);
  selCuadros.addEventListener('change', cargarAlumnos);
})();
