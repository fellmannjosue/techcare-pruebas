const CSRF_TOKEN          = window._PAGE.csrf;
const ADD_URL             = window._PAGE.addUrl;
const DELETE_BASE         = window._PAGE.deleteBase;
const URL_PERM_SAVE       = window._PAGE.urlPermSave;
const URL_PERM_DELETE     = window._PAGE.urlPermDelete;
const URL_VAC_BALANCE     = window._PAGE.urlVacBalance;
const PERMISOS_MAP        = window._PAGE.permisosMap;
const CAN_EDIT_PERMISOS   = window._PAGE.canEditPermisos;
const CAN_DELETE_PERMISOS = window._PAGE.canDeletePermisos;

$(function(){
  var table = $('#tablaAsistencia').DataTable({
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' },
    pageLength: 25, orderCellsTop: true, fixedHeader: true,
    order: [[1,'asc'],[4,'asc']],
    columnDefs: [{ orderable: false, targets: [3, 7, 8] }]
  });

  $('#tablaAsistencia thead tr:eq(1) th').each(function(i){
    $('input', this).on('keyup change', function(){
      if (table.column(i).search() !== this.value) table.column(i).search(this.value).draw();
    });
  });

  if ($.fn.select2) {
    $('#emp_code').select2({ width:'100%', placeholder:'Todos', allowClear:true });
  }

  function actualizarLimite($wrap){
    const count = $wrap.find('.cmts-list li').length;
    $wrap.find('.cmt-limit').text(count + '/5');
    const lleno = count >= 5;
    $wrap.find('.input-new-cmt').prop('disabled', lleno);
    $wrap.find('.btn-add-cmt').prop('disabled', lleno);
  }

  function agregarComentario($wrap){
    const $input = $wrap.find('.input-new-cmt');
    const texto  = $input.val().trim();
    if (!texto) return;
    const emp   = $wrap.data('emp');
    const fecha = $wrap.data('fecha');

    $wrap.find('.btn-add-cmt').prop('disabled', true);
    $.ajax({
      url: ADD_URL, method: 'POST',
      headers: {'X-CSRFToken': CSRF_TOKEN},
      data: { emp_code: emp, fecha: fecha, texto: texto },
      success: function(res){
        if (res.ok){
          $wrap.find('.cmts-list').append(
            `<li data-pk="${res.pk}"><span>${$('<div>').text(res.texto).html()}</span>` +
            `<button class="btn-del-cmt" title="Eliminar"><i class="ti ti-x" style="font-size:.75rem;"></i></button></li>`
          );
          $input.val('');
          actualizarLimite($wrap);
        } else {
          Swal.fire({icon:'warning', title:'Aviso', text: res.error || 'No se pudo agregar.'});
          $wrap.find('.btn-add-cmt').prop('disabled', false);
        }
      },
      error: function(){
        Swal.fire({icon:'error', title:'Error', text:'Error de red.'});
        $wrap.find('.btn-add-cmt').prop('disabled', false);
      }
    });
  }

  $(document).on('click', '.btn-add-cmt', function(){
    agregarComentario($(this).closest('.cmts-wrap'));
  });

  $(document).on('keydown', '.input-new-cmt', function(e){
    if (e.key === 'Enter'){ e.preventDefault(); agregarComentario($(this).closest('.cmts-wrap')); }
  });

  $(document).on('click', '.btn-del-cmt', function(){
    const $li   = $(this).closest('li');
    const pk    = $li.data('pk');
    const $wrap = $li.closest('.cmts-wrap');
    $.ajax({
      url: DELETE_BASE.replace('99999', pk), method: 'POST',
      headers: {'X-CSRFToken': CSRF_TOKEN},
      success: function(res){
        if (res.ok){ $li.remove(); actualizarLimite($wrap); }
      }
    });
  });

  // ── Renderizar badges de permisos en columna Permiso ──
  const TIPO_LABELS = window._PAGE.tipoLabels;
  // Prefijo parent/subtipo para badge
  const TIPO_BADGE_LABEL = {
    'otro_pagado_dias':   'Otro Pagado/Otro Pagado',
    'compensatorio_dias': 'Otro Pagado/Compensatorio',
  };

  function renderPermisoCells() {
    $('.permiso-cell').each(function(){
      const emp   = String($(this).data('emp')).trim();
      const fecha = $(this).data('fecha');
      const key   = emp + '|' + fecha;
      const lista = PERMISOS_MAP[key] || [];
      const $td   = $(this);
      $td.empty();
      if (lista.length > 0) {
        lista.forEach(function(p){
          const info = TIPO_LABELS[p.tipo] || {label: p.tipo, color: '#ccc'};
          const $wrap = $('<span class="d-inline-flex align-items-center gap-1 me-1 mb-1">');
          const esPrimerDia = fecha === p.fecha;
          const badgeLabel = TIPO_BADGE_LABEL[p.tipo] || info.label;
          const badgeTexto = esPrimerDia
            ? badgeLabel + ' ' + (p.horas != null ? parseFloat(p.horas) + 'h' : parseFloat(p.dias) + 'd')
            : badgeLabel;
          const $badge = $('<span class="badge badge-permiso">')
            .css('background-color', info.color)
            .css('color', '#333')
            .text(badgeTexto)
            .attr('title', p.razon || '');
          if (CAN_EDIT_PERMISOS) {
            const $btnEdit = $('<button class="btn btn-xs btn-outline-secondary btn-edit-permiso p-0" title="Editar" style="width:18px;height:18px;line-height:1">')
              .html('<i class="ti ti-pencil" style="font-size:.65rem"></i>')
              .data('permiso', p).data('emp', emp).data('nombre', $td.data('nombre')).data('fecha', fecha);
            $wrap.append($btnEdit);
          }
          if (CAN_DELETE_PERMISOS) {
            const $btnDel = $('<button class="btn btn-xs btn-outline-danger btn-del-permiso p-0" title="Eliminar" style="width:18px;height:18px;line-height:1">')
              .html('<i class="ti ti-trash" style="font-size:.65rem"></i>')
              .data('pk', p.pk).data('emp', emp).data('fecha', fecha).data('tipo', p.tipo);
            $wrap.append($btnDel);
          }
          $wrap.prepend($badge);
          $td.append($wrap);
        });
      }
      const bloqueado = String($td.data('bloqueado')) === '1';
      if (bloqueado) {
        // Cierre de mes: ya no se pueden ingresar permisos (último día hábil 16:35)
        if (lista.length === 0) {
          $td.append($('<span class="text-muted small" title="Permisos cerrados para este mes (último día hábil 16:35)"><i class="ti ti-lock me-1"></i>Cerrado</span>'));
        }
      } else if (CAN_EDIT_PERMISOS) {
        const $addBtn = $('<button class="btn btn-sm btn-secondary btn-reg-permiso" title="Registrar permiso">')
          .html('<i class="ti ti-license me-1"></i>Permiso')
          .data('emp', emp).data('nombre', $td.data('nombre')).data('fecha', fecha);
        $td.append($addBtn);
      }
    });
  }
  renderPermisoCells();

  // Cargar balance de vacaciones
  function fetchVacBalance(empCode) {
    $('#perm-vac-loading').removeClass('d-none');
    $('#perm-vac-sin-cfg, #perm-vac-cards').addClass('d-none');
    fetch(URL_VAC_BALANCE + '?emp_code=' + encodeURIComponent(empCode))
      .then(function(r){ return r.json(); })
      .then(function(data){
        $('#perm-vac-loading').addClass('d-none');
        if (!data.ok) return;
        if (!data.tiene_config) { $('#perm-vac-sin-cfg').removeClass('d-none'); return; }
        $('#perm-vac-cards').removeClass('d-none');
        const disp = data.dias_disponibles;
        const cls  = disp <= 0 ? 'text-danger' : disp <= 5 ? 'text-warning' : 'text-success';
        $('#perm-vac-disponibles').text(disp).attr('class', 'fw-bold ' + cls).css('font-size','1.4rem');
      })
      .catch(function(){ $('#perm-vac-loading').addClass('d-none'); });
  }

  // Mostrar/ocultar subtipos, balance vacaciones y auto-calcular días
  $(document).on('change', '#perm-tipo', function(){
    const v = $(this).val();
    $('#perm-subtipo-enf-wrap').toggleClass('d-none', v !== 'enfermedad_dias');
    $('#perm-subtipo-otro-wrap').toggleClass('d-none', v !== 'otro_pagado_dias');
    const esVac = v === 'vacaciones_dias';
    $('#perm-vac-balance').toggleClass('d-none', !esVac);
    if (esVac) fetchVacBalance($('#perm-emp-code').val());
  });

  function diasHabiles(fi, ff) {
    let count = 0;
    const d = new Date(fi + 'T00:00:00');
    const e = new Date(ff + 'T00:00:00');
    while (d <= e) {
      const dow = d.getDay();
      if (dow !== 0 && dow !== 6) count++;
      d.setDate(d.getDate() + 1);
    }
    return count;
  }

  function diasCalendario(fi, ff) {
    const d = new Date(fi + 'T00:00:00');
    const e = new Date(ff + 'T00:00:00');
    return Math.round((e - d) / 86400000) + 1;
  }

  function usarCalendario() {
    const subtipo = $('#perm-subtipo-enf').val();
    if (subtipo === 'enfermedad_maternidad') return true;
    if (subtipo === 'enfermedad_incapacidad') {
      const fi = $('#perm-fecha').val();
      const ff = $('#perm-fecha-fin').val();
      if (fi && ff && ff >= fi) return diasCalendario(fi, ff) > 10;
    }
    return false;
  }

  function modoActual() {
    return $('#modo-horas').is(':checked') ? 'horas' : 'dias';
  }

  function calcularDias() {
    const fi = $('#perm-fecha').val();
    const ff = $('#perm-fecha-fin').val();
    if (fi && ff && ff >= fi) {
      const calendario = usarCalendario();
      const dias = calendario ? diasCalendario(fi, ff) : diasHabiles(fi, ff);
      const etiqueta = calendario ? 'día(s) calendario' : 'día(s) hábil(es)';
      if (modoActual() === 'horas') {
        $('#perm-horas').val(dias * 8);
        $('#perm-dias-hint').text('Calculado: ' + (dias * 8) + ' hora(s) — ' + etiqueta);
      } else {
        $('#perm-dias').val(dias);
        $('#perm-dias-hint').text('Calculado: ' + dias + ' ' + etiqueta);
      }
    } else {
      $('#perm-dias-hint').text('');
    }
  }
  $(document).on('change', '#perm-fecha, #perm-fecha-fin, #perm-subtipo-enf, #perm-subtipo-otro', calcularDias);

  $(document).on('change', 'input[name="perm-modo"]', function(){
    const modo = modoActual();
    $('#wrap-dias').toggleClass('d-none', modo === 'horas');
    $('#wrap-horas').toggleClass('d-none', modo === 'dias');
    $('#perm-dias-hint').text('');
  });

  function abrirModalPermiso(emp, nombre, fecha, permiso) {
    const tipoActual = permiso ? permiso.tipo : '';
    const ENFER_SUBTYPES = ['enfermedad_dias','enfermedad_incapacidad','enfermedad_maternidad',
                            'enfermedad_citamedica','enfermedad_consulta'];
    const OTRO_SUBTYPES  = ['compensatorio_dias', 'otro_pagado_dias'];
    const esEnfermedad   = ENFER_SUBTYPES.includes(tipoActual);
    const esOtroPagado   = OTRO_SUBTYPES.includes(tipoActual);
    // When editing, use the permiso's original start date (not the clicked cell date)
    const fechaInicio = permiso && permiso.fecha ? permiso.fecha : fecha;

    $('#perm-pk').val(permiso ? permiso.pk : '');
    $('#perm-emp-code').val(emp);
    $('#perm-nombre-display').text(nombre);
    $('#perm-fecha').val(fechaInicio);
    $('#perm-fecha-fin').val(permiso && permiso.fecha_fin ? permiso.fecha_fin : fechaInicio);
    $('#perm-dias-hint').text('');

    // Tipo: si es subtipo enfermedad → seleccionar enfermedad_dias; si es subtipo otro_pagado → otro_pagado_dias
    $('#perm-subtipo-enf-wrap').addClass('d-none');
    $('#perm-subtipo-otro-wrap').addClass('d-none');
    if (esEnfermedad) {
      $('#perm-tipo').val('enfermedad_dias');
      $('#perm-subtipo-enf-wrap').removeClass('d-none');
      $('#perm-subtipo-enf').val(tipoActual === 'enfermedad_dias' ? 'enfermedad_incapacidad' : tipoActual);
    } else if (esOtroPagado) {
      $('#perm-tipo').val('otro_pagado_dias');
      $('#perm-subtipo-otro-wrap').removeClass('d-none');
      $('#perm-subtipo-otro').val(tipoActual);
    } else {
      $('#perm-tipo').val(tipoActual || $('#perm-tipo option:first').val());
    }

    // Razón: select con catálogo + opción "Agregar otra"
    const razonActual = permiso ? (permiso.razon || '') : '';
    $('#perm-razon').val(razonActual);
    const $rzSel = $('#perm-razon-sel'), $rzNueva = $('#perm-razon-nueva');
    $rzNueva.addClass('d-none').val('');
    if (razonActual && $rzSel.find('option[value="' + razonActual.replace(/"/g, '\\"') + '"]').length) {
      $rzSel.val(razonActual);
    } else if (razonActual) {
      $rzSel.val('__nueva__'); $rzNueva.removeClass('d-none').val(razonActual);
    } else {
      $rzSel.val('');
    }

    // Detectar modo según cómo fue guardado
    const usaHoras = permiso && permiso.horas != null;
    if (usaHoras) {
      $('#modo-horas').prop('checked', true);
      $('#wrap-dias').addClass('d-none');
      $('#wrap-horas').removeClass('d-none');
      $('#perm-horas').val(parseFloat(permiso.horas));
    } else {
      $('#modo-dias').prop('checked', true);
      $('#wrap-dias').removeClass('d-none');
      $('#wrap-horas').addClass('d-none');
      $('#perm-dias').val(permiso ? parseFloat(permiso.dias) : 1);
    }
    $('#perm-modal-title').text(permiso ? 'Editar Permiso' : 'Registrar Permiso');
    $('#btn-eliminar-permiso').toggleClass('d-none', !permiso);

    // Balance vacaciones al abrir modal
    const tipoSeleccionado = $('#perm-tipo').val();
    const esVacAlAbrir = tipoSeleccionado === 'vacaciones_dias';
    $('#perm-vac-balance').toggleClass('d-none', !esVacAlAbrir);
    if (esVacAlAbrir) fetchVacBalance(emp);

    new bootstrap.Modal(document.getElementById('modalPermiso')).show();
  }

  // Razón: mostrar campo "nueva" al elegir "Agregar otra…"
  $(document).on('change', '#perm-razon-sel', function(){
    $('#perm-razon-nueva').toggleClass('d-none', $(this).val() !== '__nueva__');
    if ($(this).val() === '__nueva__') $('#perm-razon-nueva').focus();
  });

  $(document).on('click', '.btn-reg-permiso', function(){
    abrirModalPermiso($(this).data('emp'), $(this).data('nombre'), $(this).data('fecha'), null);
  });

  $(document).on('click', '.btn-edit-permiso', function(){
    const p = $(this).data('permiso');
    abrirModalPermiso($(this).data('emp'), $(this).data('nombre'), $(this).data('fecha'), p);
  });

  $(document).on('click', '.btn-del-permiso', function(){
    const pk    = $(this).data('pk');
    const emp   = String($(this).data('emp')).trim();
    const fecha = $(this).data('fecha');
    const tipo  = $(this).data('tipo');
    Swal.fire({icon:'warning', title:'¿Eliminar permiso?', showCancelButton:true,
               confirmButtonText:'Sí, eliminar', cancelButtonText:'Cancelar',
               confirmButtonColor:'#d33'}).then(r => {
      if (!r.isConfirmed) return;
      $.ajax({
        url: URL_PERM_DELETE.replace('99999', pk), method: 'POST',
        headers: {'X-CSRFToken': CSRF_TOKEN},
        success: function(res){
          if (res.ok){
            const empKey = String(emp).trim();
            Object.keys(PERMISOS_MAP).forEach(function(k){
              if (k.startsWith(empKey + '|')) {
                PERMISOS_MAP[k] = PERMISOS_MAP[k].filter(function(p){ return p.pk != pk; });
                if (!PERMISOS_MAP[k].length) delete PERMISOS_MAP[k];
              }
            });
            renderPermisoCells();
            Swal.fire({icon:'success', title:'Eliminado', timer:1000, showConfirmButton:false});
          } else {
            Swal.fire({icon:'error', title:'Error', text: res.error});
          }
        },
        error: function(){ Swal.fire({icon:'error', title:'Error de red'}); }
      });
    });
  });

  $('#btn-guardar-permiso').on('click', function(){
    const emp      = $('#perm-emp-code').val();
    const fecha    = $('#perm-fecha').val();
    const fechaFin = $('#perm-fecha-fin').val() || fecha;
    // Razón desde el select (o el campo "nueva" si eligió "Agregar otra…")
    let razon = $('#perm-razon-sel').val() || '';
    if (razon === '__nueva__') razon = $('#perm-razon-nueva').val().trim();
    $('#perm-razon').val(razon);
    const modo     = modoActual();
    const dias     = modo === 'dias'  ? $('#perm-dias').val()  : '';
    const horas    = modo === 'horas' ? $('#perm-horas').val() : '';
    const pk       = $('#perm-pk').val();
    const nombre   = $('#perm-nombre-display').text();

    // Si es enfermedad o subgrupo de otro_pagado, usar el subtipo seleccionado
    const tipoBase = $('#perm-tipo').val();
    let tipo = tipoBase;
    if (tipoBase === 'enfermedad_dias')   tipo = $('#perm-subtipo-enf').val();
    else if (tipoBase === 'otro_pagado_dias') tipo = $('#perm-subtipo-otro').val();

    const valorCantidad = modo === 'horas' ? horas : dias;
    if (!fecha || !tipo || valorCantidad === '') {
      Swal.fire({icon:'warning', title:'Campos requeridos', text:'Complete fecha, tipo y ' + (modo === 'horas' ? 'horas' : 'días') + '.'});
      return;
    }
    const $btn = $(this).prop('disabled', true);
    $.ajax({
      url: URL_PERM_SAVE, method: 'POST',
      headers: {'X-CSRFToken': CSRF_TOKEN},
      data: { pk, emp_code: emp, nombre, fecha, fecha_fin: fechaFin, tipo, dias, horas, razon },
      success: function(res){
        $btn.prop('disabled', false);
        if (res.ok){
          // Si la razón es nueva, dejarla en el select para la próxima vez
          if (razon && !$('#perm-razon-sel option[value="' + razon.replace(/"/g, '\\"') + '"]').length) {
            $('<option>').val(razon).text(razon).insertBefore($('#perm-razon-sel option[value="__nueva__"]'));
          }
          const empKey      = String(emp).trim();
          const newFechaFin = res.fecha_fin || fechaFin || fecha;
          const newFecha    = res.fecha || fecha;
          const entry       = {pk: res.pk, tipo, dias: res.dias, horas: res.horas, razon,
                               fecha: newFecha, fecha_fin: newFechaFin};
          // Remove permiso from all days (handles range shrink / change)
          Object.keys(PERMISOS_MAP).forEach(function(k){
            if (k.startsWith(empKey + '|')) {
              PERMISOS_MAP[k] = PERMISOS_MAP[k].filter(function(p){ return p.pk != res.pk; });
              if (!PERMISOS_MAP[k].length) delete PERMISOS_MAP[k];
            }
          });
          // Add for every day in the new fecha..fecha_fin range
          const d1 = new Date(fecha + 'T00:00:00');
          const d2 = new Date(newFechaFin + 'T00:00:00');
          for (var d = new Date(d1); d <= d2; d.setDate(d.getDate() + 1)) {
            const dayKey = empKey + '|' + d.toISOString().slice(0, 10);
            if (!PERMISOS_MAP[dayKey]) PERMISOS_MAP[dayKey] = [];
            PERMISOS_MAP[dayKey].push(entry);
          }
          renderPermisoCells();
          bootstrap.Modal.getInstance(document.getElementById('modalPermiso')).hide();
          Swal.fire({icon:'success', title:'Guardado', timer:1200, showConfirmButton:false});
        } else {
          Swal.fire({icon:'error', title:'Error', text: res.error || 'No se pudo guardar.'});
        }
      },
      error: function(){ $btn.prop('disabled', false); Swal.fire({icon:'error', title:'Error de red'}); }
    });
  });

  $('#btn-eliminar-permiso').on('click', function(){
    const pk    = $('#perm-pk').val();
    const emp   = $('#perm-emp-code').val();
    const fecha = $('#perm-fecha').val();
    const tipo  = $('#perm-tipo').val();
    if (!pk) return;
    Swal.fire({icon:'warning', title:'¿Eliminar permiso?', showCancelButton:true,
               confirmButtonText:'Sí, eliminar', cancelButtonText:'Cancelar',
               confirmButtonColor:'#d33'}).then(r => {
      if (!r.isConfirmed) return;
      $.ajax({
        url: URL_PERM_DELETE.replace('99999', pk), method: 'POST',
        headers: {'X-CSRFToken': CSRF_TOKEN},
        success: function(res){
          if (res.ok){
            const empKey = String(emp).trim();
            Object.keys(PERMISOS_MAP).forEach(function(k){
              if (k.startsWith(empKey + '|')) {
                PERMISOS_MAP[k] = PERMISOS_MAP[k].filter(function(p){ return p.pk != pk; });
                if (!PERMISOS_MAP[k].length) delete PERMISOS_MAP[k];
              }
            });
            renderPermisoCells();
            bootstrap.Modal.getInstance(document.getElementById('modalPermiso')).hide();
            Swal.fire({icon:'success', title:'Eliminado', timer:1200, showConfirmButton:false});
          } else {
            Swal.fire({icon:'error', title:'Error', text: res.error});
          }
        },
        error: function(){ Swal.fire({icon:'error', title:'Error de red'}); }
      });
    });
  });
});
