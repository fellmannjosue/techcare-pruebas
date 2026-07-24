/* permiso_ausentes.js — <--- hecho por claude code: tab "Ausentes sin permiso".
   Carga diferida al abrir el tab; datos desde window._PAGE (isla JSON). */
(function () {
  var P = window._PAGE || {};
  var cont  = document.getElementById('pt-ausentes-cont');
  var badge = document.getElementById('pt-ausentes-badge');
  var btnTab = document.getElementById('pt-ausentes-btn');
  if (!cont || !P.urlAusentes) return;
  var cargado = false;

  function fmtFecha(iso) {
    var p = iso.split('-');
    return p[2] + '/' + p[1];   // dd/mm
  }

  function pintar(data) {
    if (!data.ok) {
      cont.innerHTML = '<div class="alert alert-warning mb-0">' +
        (data.error || 'No se pudo cargar.') + '</div>';
      return;
    }
    if (badge) {
      badge.textContent = data.total_empleados;
      badge.classList.toggle('d-none', data.total_empleados === 0);
    }
    if (!data.empleados.length) {
      cont.innerHTML = '<div class="text-center text-muted py-5">' +
        '<i class="ti ti-checks" style="font-size:2rem"></i>' +
        '<div class="mt-2">Sin ausencias pendientes: todos los días laborables tienen marca o permiso.</div></div>';
      return;
    }
    var html = '<div class="text-muted small mb-2">' + data.total_empleados +
      ' empleado(s) · ' + data.total_dias + ' día(s) sin registrar</div>' +
      '<div class="table-responsive"><table class="table table-vcenter card-table">' +
      '<thead><tr><th style="width:70px">Código</th><th>Empleado</th>' +
      '<th class="text-center" style="width:90px">Días</th><th>Fechas sin permiso</th>' +
      '<th style="width:120px"></th></tr></thead><tbody>';
    data.empleados.forEach(function (e) {
      var chips = e.fechas.map(function (f) {
        return '<button type="button" class="badge bg-red-lt text-red me-1 mb-1 border-0 chip-fecha" ' +
               'data-emp="' + e.emp_code + '" data-fecha="' + f + '" ' +
               'data-nombre="' + (e.nombre || '').replace(/"/g, '&quot;') + '" ' +
               'title="Registrar permiso de este día">' + fmtFecha(f) + '</button>';
      }).join('');
      html += '<tr>' +
        '<td class="text-muted">' + e.emp_code + '</td>' +
        '<td><div class="fw-medium">' + e.nombre + '</div>' +
          (e.cargo ? '<div class="text-muted small">' + e.cargo + '</div>' : '') + '</td>' +
        '<td class="text-center"><span class="badge bg-danger">' + e.fechas.length + '</span></td>' +
        '<td>' + chips + '</td>' +
        '<td class="text-end"><button type="button" class="btn btn-sm btn-outline-primary btn-registrar-permiso" ' +
          'data-emp="' + e.emp_code + '" data-fecha="' + e.fechas[0] + '" ' +
          'data-nombre="' + (e.nombre || '').replace(/"/g, '&quot;') + '">' +
          '<i class="ti ti-pencil me-1"></i>Registrar</button></td>' +
        '</tr>';
    });
    html += '</tbody></table></div>';
    cont.innerHTML = html;

    // "Registrar" → abre el modal de permiso ya con empleado y fecha
    cont.querySelectorAll('.btn-registrar-permiso, .chip-fecha').forEach(function (b) {
      b.addEventListener('click', function () {
        abrirModal(this.dataset.emp, this.dataset.nombre, this.dataset.fecha);
      });
    });
  }

  // ── Modal de permiso (el mismo del reporte diario, parcial compartido) ──
  function abrirModal(emp, nombre, fecha) {
    var el = document.getElementById('modalPermiso');
    if (!el || !window.bootstrap) return;
    var $ = function (id) { return document.getElementById(id); };

    if ($('perm-pk'))              $('perm-pk').value = '';
    if ($('perm-emp-code'))        $('perm-emp-code').value = emp;
    if ($('perm-nombre-display'))  $('perm-nombre-display').textContent = nombre;
    if ($('perm-fecha'))           $('perm-fecha').value = fecha;
    if ($('perm-fecha-fin'))       $('perm-fecha-fin').value = fecha;
    if ($('perm-razon'))           $('perm-razon').value = '';
    if ($('perm-razon-sel'))       $('perm-razon-sel').value = '';
    if ($('perm-razon-nueva'))     { $('perm-razon-nueva').value = ''; $('perm-razon-nueva').classList.add('d-none'); }
    if ($('perm-dias'))            $('perm-dias').value = '1';
    if ($('perm-horas'))           $('perm-horas').value = '';
    if ($('modo-dias'))            $('modo-dias').checked = true;
    if ($('wrap-dias'))            $('wrap-dias').classList.remove('d-none');
    if ($('wrap-horas'))           $('wrap-horas').classList.add('d-none');
    if ($('btn-eliminar-permiso')) $('btn-eliminar-permiso').classList.add('d-none');
    if ($('perm-modal-title'))     $('perm-modal-title').textContent = 'Registrar Permiso';
    bootstrap.Modal.getOrCreateInstance(el).show();
  }

  // Razón: "Agregar otra…" muestra el campo de texto
  var razonSel = document.getElementById('perm-razon-sel');
  if (razonSel) razonSel.addEventListener('change', function () {
    var nueva = document.getElementById('perm-razon-nueva');
    if (!nueva) return;
    nueva.classList.toggle('d-none', this.value !== '__nueva__');
    if (this.value !== '__nueva__') nueva.value = '';
  });

  // Días / Horas
  var mDias = document.getElementById('modo-dias'), mHoras = document.getElementById('modo-horas');
  function alternarModo() {
    var wd = document.getElementById('wrap-dias'), wh = document.getElementById('wrap-horas');
    if (!wd || !wh) return;
    var esHoras = mHoras && mHoras.checked;
    wd.classList.toggle('d-none', esHoras);
    wh.classList.toggle('d-none', !esHoras);
  }
  if (mDias)  mDias.addEventListener('change', alternarModo);
  if (mHoras) mHoras.addEventListener('change', alternarModo);

  // Guardar
  var btnGuardar = document.getElementById('btn-guardar-permiso');
  if (btnGuardar) btnGuardar.addEventListener('click', function () {
    // Solo actuar si el modal se abrió desde ESTE tab (el reporte diario tiene su propio JS)
    var paneActivo = document.querySelector('#pt-ausentes.active');
    if (!paneActivo || !P.urlPermSave) return;
    var $ = function (id) { return document.getElementById(id); };
    var sel = $('perm-razon-sel') ? $('perm-razon-sel').value : '';
    var razon = sel === '__nueva__' ? ($('perm-razon-nueva') || {}).value || '' : sel;
    var esHoras = $('modo-horas') && $('modo-horas').checked;

    var tipo = $('perm-tipo') ? $('perm-tipo').value : '';
    if ($('perm-subtipo-enf') && !$('perm-subtipo-enf-wrap').classList.contains('d-none')) tipo = $('perm-subtipo-enf').value;
    if ($('perm-subtipo-otro') && !$('perm-subtipo-otro-wrap').classList.contains('d-none')) tipo = $('perm-subtipo-otro').value;

    var fd = new FormData();
    fd.append('pk', '');
    fd.append('emp_code',  $('perm-emp-code').value);
    fd.append('nombre',    $('perm-nombre-display').textContent);
    fd.append('fecha',     $('perm-fecha').value);
    fd.append('fecha_fin', $('perm-fecha-fin').value);
    fd.append('tipo',      tipo);
    fd.append('dias',      esHoras ? '' : ($('perm-dias').value || '1'));
    fd.append('horas',     esHoras ? ($('perm-horas').value || '') : '');
    fd.append('razon',     razon);
    fd.append('comentario', '');

    btnGuardar.disabled = true;
    fetch(P.urlPermSave, { method: 'POST', headers: { 'X-CSRFToken': P.csrf || '' }, body: fd })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        btnGuardar.disabled = false;
        if (!d.ok) { alert(d.error || 'No se pudo guardar.'); return; }
        var el = document.getElementById('modalPermiso');
        if (el && window.bootstrap) bootstrap.Modal.getOrCreateInstance(el).hide();
        cargar();   // el empleado desaparece de la lista si ya no le faltan días
      })
      .catch(function () { btnGuardar.disabled = false; alert('Error de conexión.'); });
  });

  function cargar() {
    cont.innerHTML = '<p class="text-muted text-center py-4 mb-0">' +
      '<span class="spinner-border spinner-border-sm me-2"></span>Cargando…</p>';
    fetch(P.urlAusentes + '?mes=' + encodeURIComponent(P.mesActual || ''))
      .then(function (r) { return r.json(); })
      .then(pintar)
      .catch(function () {
        cont.innerHTML = '<div class="alert alert-danger mb-0">Error de conexión.</div>';
      });
  }

  // carga la primera vez que se abre el tab
  if (btnTab) btnTab.addEventListener('shown.bs.tab', function () {
    if (!cargado) { cargado = true; cargar(); }
  });
  var reload = document.getElementById('pt-ausentes-reload');
  if (reload) reload.addEventListener('click', cargar);
})();
