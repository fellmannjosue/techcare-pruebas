/* <--- hecho por claude code: Ingreso de Notas — tab Asistencias.

   Se elige clase y fecha, y la rejilla lista a todos los alumnos con tres
   campos: Tipo (los 4 del catálogo), Razón y Otros. Autoguardado por celda.

   Solo se registra a quien FALTÓ: dejar el Tipo vacío significa "asistió", y si
   ya había una ausencia la quita. Estas filas alimentan los recargos por no
   asistencia, así que la de "quitar" pide confirmación. */
(function () {
  var d = document.getElementById('notas-config');
  if (!d) return;
  var C = {
    urlClases:    d.dataset.v0,
    area:         d.dataset.v3,
    csrf:         d.dataset.v4,
    urlAusencias: d.dataset.v7,
    urlGuardar:   d.dataset.v8
  };

  var selGrado = document.getElementById('as-grado');
  var selClase = document.getElementById('as-clase');
  var inpFecha = document.getElementById('as-fecha');
  var cont     = document.getElementById('as-cont');
  var titulo   = document.getElementById('as-titulo');
  var estado   = document.getElementById('as-estado');
  if (!selGrado || !cont) return;

  var tipos = [], razones = [], razonPendiente = null, tipoDefecto = null;

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
    vaciar('Elige la clase para pasar asistencia.');
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
    if (!g.grado || !selClase.value) { vaciar('Elige grado y clase para pasar asistencia.'); return; }
    if (!inpFecha.value) return;
    cont.innerHTML = '<div class="card-body text-center text-muted py-5">' +
      '<span class="spinner-border spinner-border-sm me-2"></span>Cargando alumnos…</div>';

    var qs = '?area=' + encodeURIComponent(C.area) +
             '&grado=' + encodeURIComponent(g.grado) + '&grupo=' + encodeURIComponent(g.grupo) +
             '&materia=' + encodeURIComponent(selClase.value) +
             '&fecha=' + encodeURIComponent(inpFecha.value);

    fetch(C.urlAusencias + qs)
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        if (!dd.ok) {
          cont.innerHTML = '<div class="card-body"><div class="alert alert-warning mb-0">' +
            esc(dd.error) + '</div></div>';
          return;
        }
        tipos = dd.tipos; razones = dd.razones;
        razonPendiente = dd.razon_pendiente; tipoDefecto = dd.tipo_defecto;
        pintar(dd.alumnos, dd.ausentes);
      })
      .catch(function () {
        cont.innerHTML = '<div class="card-body"><div class="alert alert-danger mb-0">' +
          'Error de conexión.</div></div>';
      });
  }

  function opciones(lista, sel, vacio) {
    var h = '<option value="">' + vacio + '</option>';
    lista.forEach(function (o) {
      h += '<option value="' + o.id + '"' + (String(o.id) === String(sel) ? ' selected' : '') +
           '>' + esc(o.label) + '</option>';
    });
    return h;
  }

  function pintar(alumnos, ausentes) {
    var clase = selClase.options[selClase.selectedIndex].text.replace(/\s*\(\d+\)$/, '');
    titulo.innerHTML = esc(clase) + ' · ' + inpFecha.value.split('-').reverse().join('/') +
      ' · ' + alumnos.length + ' alumno(s) ' +
      '<span class="badge bg-orange-lt ms-2" id="as-cuenta">' + ausentes + ' con falta</span>';

    if (!alumnos.length) { vaciar('No hay alumnos en esa clase.'); return; }

    var h = '<div class="table-responsive"><table class="table table-vcenter table-sm mb-0 tabla-notas">' +
      '<thead><tr><th class="col-no">No</th><th class="col-alumno">Participante</th>' +
      '<th style="width:190px">Tipo</th><th style="width:280px">Razón</th>' +
      '<th>Otros</th></tr></thead><tbody>';

    alumnos.forEach(function (a, i) {
      var com = ' data-materia="' + a.materia_id + '" data-alumno="' + esc(a.nombre) + '"';
      var falto = !!a.tipo;
      h += '<tr' + (falto ? ' class="fila-falta"' : '') + '>' +
        '<td class="text-muted">' + (i + 1) + '</td>' +
        '<td><div class="fw-medium">' + esc(a.nombre) + '</div>' +
          '<div class="text-muted small font-monospace">' + esc(a.identidad) + '</div></td>' +
        '<td class="p-1"><select class="form-select form-select-sm celda-asis" data-campo="tipo"' + com + '>' +
          opciones(tipos, a.tipo, '— Asistió —') + '</select></td>' +
        '<td class="p-1"><select class="form-select form-select-sm celda-asis" data-campo="razon"' + com +
          (falto ? '' : ' disabled') + '>' +
          opciones(razones, a.razon || razonPendiente, '—') + '</select></td>' +
        '<td class="p-1"><input type="text" class="form-control form-control-sm celda-asis"' +
          ' data-campo="otros"' + com + ' value="' + esc(a.otros) + '"' +
          (falto ? '' : ' disabled') + ' placeholder="Detalle opcional"></td></tr>';
    });
    cont.innerHTML = h + '</tbody></table></div>';
  }

  function recontar() {
    var n = 0;
    cont.querySelectorAll('[data-campo="tipo"]').forEach(function (s) { if (s.value) n++; });
    var b = document.getElementById('as-cuenta');
    if (b) b.textContent = n + ' con falta';
  }

  // ── Guardado ──
  function guardar(fila, disparador) {
    var tipo  = fila.querySelector('[data-campo="tipo"]');
    var razon = fila.querySelector('[data-campo="razon"]');
    var otros = fila.querySelector('[data-campo="otros"]');

    pinta('<i class="ti ti-loader-2 me-1"></i>Guardando…');
    disparador.classList.remove('celda-ok', 'celda-error');
    disparador.classList.add('celda-guardando');

    fetch(C.urlGuardar, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': C.csrf },
      credentials: 'same-origin',
      body: JSON.stringify({
        area: C.area, materia_id: tipo.dataset.materia, fecha: inpFecha.value,
        tipo: tipo.value, razon: razon.value, otros: otros.value.trim(),
        alumno: tipo.dataset.alumno
      })
    })
      .then(function (r) { return r.json(); })
      .then(function (dd) {
        disparador.classList.remove('celda-guardando');
        if (!dd.ok) {
          disparador.classList.add('celda-error');
          pinta('<i class="ti ti-alert-triangle me-1"></i>' + esc(dd.error), 'text-danger');
          cargar();   // se recarga para no dejar la pantalla mintiendo
          return;
        }
        disparador.classList.add('celda-ok');
        var msg = dd.accion === 'delete' ? 'Falta quitada'
                : dd.accion === 'insert' ? 'Falta registrada' : 'Guardado';
        pinta('<i class="ti ti-check me-1"></i>' + msg, 'text-green');
      })
      .catch(function () {
        disparador.classList.remove('celda-guardando');
        disparador.classList.add('celda-error');
        pinta('<i class="ti ti-cloud-off me-1"></i>Sin conexión — no se guardó', 'text-danger');
      });
  }

  cont.addEventListener('change', function (e) {
    var el = e.target;
    if (!el.classList || !el.classList.contains('celda-asis')) return;
    var fila  = el.closest('tr');
    var tipo  = fila.querySelector('[data-campo="tipo"]');
    var razon = fila.querySelector('[data-campo="razon"]');
    var otros = fila.querySelector('[data-campo="otros"]');

    if (el.dataset.campo === 'tipo') {
      var habia = fila.classList.contains('fila-falta');
      // Quitar una falta ya registrada tiene efecto económico: se confirma
      if (!el.value && habia) {
        if (!confirm('¿Quitar la falta de ' + tipo.dataset.alumno + '?\n\n' +
                     'Se borra del sistema académico y deja de contar para los recargos.')) {
          el.value = String(tipo.dataset.previo || '');
          return;
        }
      }
      var falto = !!el.value;
      fila.classList.toggle('fila-falta', falto);
      razon.disabled = !falto;
      otros.disabled = !falto;
      if (falto && !razon.value) razon.value = String(razonPendiente);
      recontar();
    }
    tipo.dataset.previo = tipo.value;
    guardar(fila, el);
  });

  // "Otros" es texto: se guarda al salir del campo, no en cada tecla
  cont.addEventListener('focusout', function (e) {
    var el = e.target;
    if (!el.classList || el.dataset.campo !== 'otros') return;
    var v = el.value.trim();
    if (v === (el.dataset.antes || '')) return;
    el.dataset.antes = v;
    guardar(el.closest('tr'), el);
  });
  cont.addEventListener('focusin', function (e) {
    if (e.target.dataset && e.target.dataset.campo === 'otros') {
      e.target.dataset.antes = e.target.value.trim();
    }
  });

  selClase.addEventListener('change', cargar);
  inpFecha.addEventListener('change', cargar);
})();
