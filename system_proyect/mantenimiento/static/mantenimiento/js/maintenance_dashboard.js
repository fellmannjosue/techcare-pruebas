/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #maintenance_dashboard-config (un .js no lo procesa Django). */
const CFG_MAINTENANCE_DASHBOARD = (function(){
  var d = document.getElementById("maintenance_dashboard-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
    v4: d.v4,
  };
})();

window._PAGE = {
  csrf: CFG_MAINTENANCE_DASHBOARD.v0,
  computadorasJson: CFG_MAINTENANCE_DASHBOARD.j2,
  impresorasJson: CFG_MAINTENANCE_DASHBOARD.j3,
  urlTipoFalla: CFG_MAINTENANCE_DASHBOARD.v1,
};

/* <--- hecho por claude code: lógica COMPLETA recuperada de d5d2026. El archivo
   restaurado antes venía de un commit sin el modal de EDITAR, así que editar un
   mantenimiento (firma técnico/maestro, fotos, limpiar firma, tipo de falla nueva)
   no funcionaba. Envuelta en IIFE. Lee window._PAGE definido arriba. */
(function(){
// Datos de computadoras para auto-fill (inyectados desde el bridge window._PAGE)
const COMP_DATA = window._PAGE.computadorasJson;
// <--- hecho por claude code: datos de impresoras para auto-fill
const IMP_DATA = window._PAGE.impresorasJson || {};

$(function () {

  // DataTable (envuelto en try-catch para que un error no detenga el resto del JS)
  // <--- hecho por claude code: una DataTable por pestaña (computadoras / impresoras / control)
  try {
    $.fn.dataTable.ext.errMode = 'none';
    $('.tabla-mant').each(function(){
      const col = parseInt(this.dataset.orderCol || '7', 10);
      const dir = this.dataset.orderDir || 'desc';   // <--- hecho por claude code: control ordena por ID asc fijo
      $(this).DataTable({
        pageLength: 15, order: [[col, dir]], autoWidth: false,   // <--- hecho por claude code (28-sep-2026): autoWidth dejaba la tabla más angosta que la tarjeta
        language: {
          lengthMenu:"Mostrar _MENU_ registros", zeroRecords:"Sin registros",
          info:"Mostrando _START_ a _END_ de _TOTAL_", infoEmpty:"Sin registros",
          infoFiltered:"(de _MAX_ totales)", search:"", searchPlaceholder:"Buscar en esta pestaña…",
          paginate:{first:"«",last:"»",next:"›",previous:"‹"}
        }
      });
    });
    // Al cambiar de pestaña: reajustar columnas (una tabla oculta se inicializa sin anchos) y recordar la pestaña
    $('#tabs-registros a[data-bs-toggle="tab"]').on('shown.bs.tab', function(e){
      $.fn.dataTable.tables({ visible: true, api: true }).columns.adjust();
      try { localStorage.setItem('mant_tab', e.target.getAttribute('href')); } catch(_) {}
    });
    try {
      const ult = localStorage.getItem('mant_tab');
      if (ult && document.querySelector('#tabs-registros a[href="' + ult + '"]')) {
        new bootstrap.Tab(document.querySelector('#tabs-registros a[href="' + ult + '"]')).show();
      }
    } catch(_) {}
  } catch(e) { console.warn('DataTable init:', e); }

  // <--- hecho por claude code: popovers de detalle (Modelo / Observaciones) creados al primer hover.
  // Se inicializan perezosamente porque DataTables pagina y las filas no visibles no existen en el DOM al cargar.
  $(document).on('mouseenter focusin', '.mant-pop', function(){
    if (typeof bootstrap === 'undefined' || !bootstrap.Popover) return;
    if (!bootstrap.Popover.getInstance(this)) {
      bootstrap.Popover.getOrCreateInstance(this, { container: 'body', sanitize: false }).show();
    }
  });
  // <--- hecho por claude code (17-sep-2026): BUG — quedaban DOS recuadros abiertos: el popover abre con hover Y con foco,
  // así que al hacer clic en un Modelo ese quedaba enfocado (abierto) y al pasar el mouse a otra fila se abría el segundo.
  // Ahora al abrirse uno se cierran los demás (y se les quita el foco para que no queden "pegados").
  document.addEventListener('show.bs.popover', function (e) {
    document.querySelectorAll('.mant-pop').forEach(function (el) {
      if (el === e.target) return;
      const i = bootstrap.Popover.getInstance(el);
      if (i) i.hide();
      if (document.activeElement === el) el.blur();
    });
  });
  // Al cambiar de página/orden/búsqueda se cierran los popovers abiertos
  $('.tabla-mant').on('draw.dt', function(){
    document.querySelectorAll('.mant-pop').forEach(function(el){ const i = bootstrap.Popover.getInstance(el); if (i) i.hide(); });
  });

  // ── Tipo de Falla: opción "Agregar nueva" → muestra un campo de texto inline ──
  // Pares de [select, input de nueva falla]
  const TF_PAIRS = [['#id_tipo_falla', '#id_tipo_falla_nueva'], ['#edit-tipo-falla', '#edit-tipo-falla-nueva']];
  TF_PAIRS.forEach(function (p) {
    const $s = $(p[0]);
    if ($s.length && !$s.find('option[value="__nueva__"]').length) {
      $s.append('<option value="__nueva__">➕ Agregar nueva falla…</option>');
    }
    $(document).on('change', p[0], function () {
      const $inp = $(p[1]);
      const nueva = this.value === '__nueva__';
      $inp.toggleClass('d-none', !nueva);
      if (nueva) { $inp.focus(); } else { $inp.val(''); }
    });
  });

  // Al abrir el modal disparar fill si ya hay valor
  $('#modalNuevoRegistro').on('shown.bs.modal', function(){
    const _val = $('#id_computadora').val();
    if (_val) fillFromComputadora(_val);
  });

  // Auto-fill al seleccionar computadora
  function fillFromComputadora(val) {
    const data = COMP_DATA[val] || {};
    $('#id_model').val(data.modelo || '');
    $('#mant-asignado').val(data.asignado || '');
    $('#mant-area').val(data.area || '');
    $('#mant-grado').val(data.grado || '');
    $('#hidden_teacher_name').val(data.asignado || '');
    $('#hidden_grade').val(data.grado || '');
    $('#insp-firma-nombre').text(data.asignado || '—');   // <--- hecho por claude code: firma de la inspección
  }

  $('#id_computadora').on('change', function(){
    fillFromComputadora(this.value);
    const data = COMP_DATA[this.value] || {};
    const serieInput = $('#id_serie');
    const chk = $('#chk-serie-mant');
    if (!chk.is(':checked')) {
      serieInput.val(data.serie || '').addClass('bg-light text-muted').prop('readonly', true);
    }
  });

  // <--- hecho por claude code: toggle Computadora / Impresora ──────────────
  function setEquipo(tipo) {
    $('#id_tipo_equipo').val(tipo);
    // <--- hecho por claude code: control e inspección reutilizan el bloque de computadora.
    // Reset + aplicar: un elemento puede tener varias clases solo-* y los toggles
    // independientes se pisaban entre sí.
    const esCtrl = tipo === 'control', esInsp = tipo === 'inspeccion';
    // <--- hecho por claude code (17-sep-2026): Entrega / Recogida reutilizan el bloque de computadora (parte 1)
    const esMov = tipo === 'entrega' || tipo === 'recogida' || tipo === 'caso_especial';   // <--- hecho por claude code (28-sep-2026): caso especial = recogida
    $('#ce-aviso').toggleClass('d-none', tipo !== 'caso_especial');
    if (tipo !== 'caso_especial') $('#id_control_origen').val('');
    if (tipo !== 'control') $('#chk-caso-especial, #chk-cambio-equipo, #chk-reasignacion, #chk-mantenimiento, #chk-reparacion').prop('checked', false);
    const esPre = tipo === 'prestamo';   // <--- hecho por claude code (16-oct-2026): préstamo de equipo
    $('.equipo-computadora').toggleClass('d-none', !(tipo === 'computadora' || esCtrl || esInsp || esMov || esPre));
    $('.equipo-prestamo').toggleClass('d-none', !esPre);
    $('.equipo-entrega').toggleClass('d-none', !esMov);
    $('.equipo-impresora').toggleClass('d-none', tipo !== 'impresora');
    $('.equipo-control').toggleClass('d-none', !esCtrl);
    $('.equipo-inspeccion').toggleClass('d-none', !esInsp);
    $('.solo-computadora, .solo-control, .solo-inspeccion, .solo-no-control, .solo-no-inspeccion, .solo-entrega, .solo-recogida, .solo-no-entrega, .solo-prestamo, .solo-no-prestamo').removeClass('d-none');
    if (!esPre) $('.solo-prestamo').addClass('d-none');
    if (esPre) { $('.solo-no-prestamo').addClass('d-none'); prestDefectos(); }
    if (tipo !== 'computadora') $('.solo-computadora').addClass('d-none');
    if (!esCtrl) $('.solo-control').addClass('d-none');
    if (!esInsp) $('.solo-inspeccion').addClass('d-none');
    if (esCtrl) $('.solo-no-control').addClass('d-none');
    if (esInsp) $('.solo-no-inspeccion').addClass('d-none');
    if (tipo !== 'entrega') $('.solo-entrega').addClass('d-none');
    if (tipo !== 'recogida' && tipo !== 'caso_especial') $('.solo-recogida').addClass('d-none');
    // <--- hecho por claude code (28-sep-2026): un solo obs_tecnico por POST — se habilita el textarea del bloque visible
    $('#id_obs_tecnico').prop('disabled', esMov);
    $('#id_obs_tecnico_mov').prop('disabled', !esMov);
    if (esMov) {
      $('.solo-no-inspeccion, .solo-no-entrega').addClass('d-none');   // sin estado/solución/pads: firma escrita + fecha y hora
      $('.lbl-mov').each(function(){ $(this).text($(this).data(tipo === 'entrega' ? 'ent' : 'rec')); });
      const fh = $('#id_fecha_hora');
      if (fh.length && !fh.val()) {                                     // por defecto, ahora
        const d = new Date(), p2 = x => String(x).padStart(2, '0');
        fh.val(d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()) + 'T' + p2(d.getHours()) + ':' + p2(d.getMinutes()));
      }
      movDetalleEquipo();
    }
    $('.mant-equipo-btn').each(function(){
      const activo = $(this).data('equipo') === tipo;
      $(this).toggleClass('btn-primary', activo).toggleClass('btn-outline-primary', !activo);
    });
    if (tipo === 'control') { ctrlSwitches(); }
  }

  // <--- hecho por claude code (16-oct-2026): préstamo — fechas por defecto y solicitante/área desde la computadora
  function hoyISO() { const d = new Date(), p2 = x => String(x).padStart(2, '0'); return d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()); }
  function prestDefectos() {
    if (!$('#id_date').val()) $('#id_date').val(hoyISO());
    if (!$('#prest-desde').val()) $('#prest-desde').val(hoyISO());
    prestDesdeComputadora();
  }
  function prestDesdeComputadora() {   // solo pisa lo que esté vacío o lo que se llenó solo antes
    if ($('#id_tipo_equipo').val() !== 'prestamo') return;
    const sel = document.getElementById('id_computadora'), c = sel ? (COMP_DATA[sel.value] || null) : null;
    [['#prest-solicitante', c ? c.asignado : ''], ['#prest-area', c ? c.area : '']].forEach(function (par) {
      const el = $(par[0]);
      if (!el.length) return;
      if (!el.val() || el.attr('data-auto') === '1') el.val(par[1] || '').attr('data-auto', par[1] ? '1' : '0');
    });
  }
  $('#prest-solicitante, #prest-area').on('input', function () { $(this).attr('data-auto', '0'); });
  $('#id_computadora').on('change', prestDesdeComputadora);

  // <--- hecho por claude code (17-sep-2026): Entrega / Recogida — "debe mostrar QUÉ equipo" y QUÉ televisor
  function movDetalleEquipo() {
    const sel = document.getElementById('id_computadora'), out = document.getElementById('ent-equipo-detalle');
    if (!sel || !out) return;
    const c = COMP_DATA[sel.value] || null;
    const id = sel.value && sel.selectedOptions[0] ? sel.selectedOptions[0].textContent.trim() : '';
    out.textContent = c ? [id, c.serie ? 'Serie ' + c.serie : '', c.asignado || ''].filter(Boolean).join(' · ') : '— selecciona la computadora arriba —';
    if (c && c.asignado) movElegirFirmante('#id_firma_nombre', c.asignado);   // firma = asignado del equipo (se puede cambiar)
  }
  // Selecciona un nombre en el select de firma; si no está en la lista, lo agrega
  function movElegirFirmante(selector, nombre) {
    const sel = document.querySelector(selector); if (!sel) return;
    nombre = (nombre || '').trim();
    if (nombre && !Array.from(sel.options).some(o => o.value === nombre)) sel.add(new Option(nombre, nombre));
    sel.value = nombre;
  }
  $('#id_computadora').on('change', movDetalleEquipo);
  $('#id_ent_televisor').on('change', function () {
    $('#ent-televisor-wrap').prop('hidden', !this.checked);
    if (!this.checked) $('#id_televisor').val('');
  });
  $('#edit-ent-televisor').on('change', function () {
    $('#edit-ent-televisor-wrap').prop('hidden', !this.checked);
    if (!this.checked) $('#edit-televisor').val('');
  });
  $('.mant-equipo-btn').on('click', function(){ setEquipo($(this).data('equipo')); });
  // <--- hecho por claude code (28-sep-2026): cada página es de UN tipo: el modal "Nuevo" queda fijo en ese tipo y
  // se ocultan los botones para cambiarlo (data-v4 del div de config).
  (function(){
    const fijo = CFG_MAINTENANCE_DASHBOARD.v4;
    if (!fijo || !document.querySelector('.mant-equipo-btn[data-equipo="' + fijo + '"]')) return;
    $('#equipo-toggle').addClass('d-none');
    setEquipo(fijo);
    $('#modalNuevoRegistro').on('show.bs.modal', function(){ setEquipo(fijo); });
  })();
  // <--- hecho por claude code (22-oct-2026): FORMULARIO ÚNICO de Control — toggles de acción (control/inspección/entrega/recogida).
  // Cada toggle cambia el tipo_equipo (setEquipo) y revela su bloque; el backend crea la ficha de ese tipo y redirige a su tabla.
  (function(){
    if (CFG_MAINTENANCE_DASHBOARD.v4 !== 'control') return;
    $('#acciones-equipo').removeClass('d-none');
    // la 2.ª fila (Caso especial/Cambio/Reasignación/Mantenimiento) solo aplica al Control
    function syncVariantes(){ $('#variantes-control').toggleClass('d-none', !$('#chk-accion-control').is(':checked')); }
    function resetAccion(){ $('.chk-accion').prop('checked', false); $('#chk-accion-control').prop('checked', true); syncVariantes(); }
    resetAccion();
    $('#modalNuevoRegistro').on('show.bs.modal', function(){ resetAccion(); });   // al abrir, vuelve a Control por defecto
    $(document).on('change', '.chk-accion', function(){
      if (this.checked) {
        $('.chk-accion').not(this).prop('checked', false);
        setEquipo($(this).data('accion'));
      } else if (!$('.chk-accion:checked').length) {   // siempre debe haber uno activo
        $('#chk-accion-control').prop('checked', true);
        setEquipo('control');
      }
      syncVariantes();
    });
  })();
  // <--- hecho por claude code (22-oct-2026): abrir el "Nuevo" automáticamente desde el launcher del hub (?nuevo=<switch|1>)
  (function(){
    var nuevo = new URLSearchParams(window.location.search).get('nuevo');
    if (!nuevo) return;
    var modalEl = document.getElementById('modalNuevoRegistro');
    if (!modalEl) return;
    var toggles = { caso_especial: '#chk-caso-especial', cambio_equipo: '#chk-cambio-equipo',
                    reasignacion: '#chk-reasignacion', mantenimiento: '#chk-mantenimiento' };
    setTimeout(function(){
      if (!(window.bootstrap && bootstrap.Modal)) return;
      bootstrap.Modal.getOrCreateInstance(modalEl).show();
      // <--- hecho por claude code (22-oct-2026): acciones del formulario único (tira de toggles)
      if ($('#chk-accion-' + nuevo).length) {
        $('#chk-accion-' + nuevo).prop('checked', true).trigger('change');
      } else if (toggles[nuevo] && $('#id_tipo_equipo').val() === 'control') {
        $(toggles[nuevo]).prop('checked', true).trigger('change');
      }
    }, 200);
  })();
  // <--- hecho por claude code (28-sep-2026): "Caso especial" dentro del CONTROL: reemplaza las dos preguntas por el
  // checklist de recogida (bloque equipo-entrega) y al guardar se crean control + recogida por caso especial juntos.
  function casoEspecialToggle() {
    const on = $('#chk-caso-especial').is(':checked') && $('#id_tipo_equipo').val() === 'control';
    $('.ctrl-preguntas').toggleClass('d-none', on);
    if (on) $('#ctrl-fallas-detalle-wrap').addClass('d-none');
    $('.equipo-entrega').toggleClass('d-none', !on);
    if (on) {
      $('.lbl-mov').each(function(){ $(this).text($(this).data('rec')); });
      $('#id_obs_tecnico_mov').prop('disabled', true);               // el comentario del técnico es el del control
      $('#id_obs_tecnico').prop('disabled', false);
      const fh = $('#id_fecha_hora');
      if (fh.length && !fh.val()) {
        const d = new Date(), p2 = x => String(x).padStart(2, '0');
        fh.val(d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()) + 'T' + p2(d.getHours()) + ':' + p2(d.getMinutes()));
      }
      movDetalleEquipo();
    }
  }
  // <--- hecho por claude code (28-sep-2026): "Cambio de equipo" dentro del CONTROL: reemplaza las dos preguntas por
  // Equipo anterior (la computadora del control) / Equipo nuevo. Excluyente con "Caso especial".
  function cambioEquipoToggle() {
    const on = $('#chk-cambio-equipo').is(':checked') && $('#id_tipo_equipo').val() === 'control';
    $('.ctrl-cambio').toggleClass('d-none', !on);
    if (on) {
      $('.ctrl-preguntas').addClass('d-none'); $('#ctrl-fallas-detalle-wrap').addClass('d-none');
      cambioEquipoAnterior();
    }
  }
  function equipoTexto(d, asset) {
    if (!d) return '—';
    return [asset || d.asset || '', d.modelo || '', d.serie ? 'Serie ' + d.serie : '', d.ip ? 'IP ' + d.ip : ''].filter(Boolean).join(' · ');
  }
  function cambioEquipoAnterior() {
    const id = $('#id_computadora').val(), d = COMP_DATA[id];
    $('#cambio-equipo-anterior').text(id && d ? equipoTexto(d) : '— selecciona la computadora arriba —');
  }
  // Modal "Registrar equipo nuevo": se abre desde el control (nuevo o editar), NO envía nada al servidor:
  // copia modelo/serie/IP/observaciones a los hidden del formulario que lo abrió y vuelve a mostrar ese modal.
  let eqnOrigen = 'nuevo';
  const EQN = { nuevo: { parent: '#modalNuevoRegistro', comp: '#id_computadora', box: '#cambio-equipo-nuevo', m: '#id_modelo_nuevo', s: '#id_serie_nuevo', ip: '#id_ip_nuevo', o: '#id_obs_equipo_nuevo' },
                editar: { parent: '#modalEditarRegistro', comp: '#edit-computadora', box: '#edit-cambio-nuevo', m: '#edit-modelo-nuevo', s: '#edit-serie-nuevo', ip: '#edit-ip-nuevo', o: '#edit-obs-equipo-nuevo' } };
  $(document).on('click', '.btn-equipo-nuevo', function(){
    eqnOrigen = $(this).data('origen') || 'nuevo';
    const k = EQN[eqnOrigen], id = $(k.comp).val(), d = COMP_DATA[id] || {};
    if (!id) { alert('Primero selecciona la computadora del control.'); return; }
    $('#eqn-asset, #eqn-asset-input').text(d.asset || '').val(d.asset || '');
    $('#eqn-modelo').val($(k.m).val() || ''); $('#eqn-serie').val($(k.s).val() || ''); $('#eqn-ip').val($(k.ip).val() || ''); $('#eqn-obs').val($(k.o).val() || '');
    $('#eqn-asignado').val(d.asignado || ''); $('#eqn-area').val(d.area || ''); $('#eqn-grado').val(d.grado || ''); $('#eqn-edificio').val(d.edificio || '');
    $('#eqn-anterior').html('<i class="ti ti-device-desktop-off me-1"></i>Equipo anterior: <strong>' + $('<div>').text(equipoTexto(d)).html() + '</strong>');
    $(k.parent).modal('hide');
    $('#modalEquipoNuevo').modal('show');
  });
  $('#btn-equipo-nuevo-ok').on('click', function(){
    const k = EQN[eqnOrigen];
    const m = $('#eqn-modelo').val().trim(), s = $('#eqn-serie').val().trim().toUpperCase(), ip = $('#eqn-ip').val().trim();
    if (!m && !s) { $('#eqn-modelo').focus(); return; }
    $(k.m).val(m); $(k.s).val(s); $(k.ip).val(ip); $(k.o).val($('#eqn-obs').val().trim());
    $(k.box).removeClass('vacio').text([m, s ? 'Serie ' + s : '', ip ? 'IP ' + ip : ''].filter(Boolean).join(' · '));
    $('#modalEquipoNuevo').modal('hide');
  });
  $('#modalEquipoNuevo').on('hidden.bs.modal', function(){ $(EQN[eqnOrigen].parent).modal('show'); });
  /* <--- hecho por claude code (12-oct-2026): REASIGNACIÓN (maestro A → maestro B). Los TRES interruptores del control
     (caso especial / cambio de equipo / reasignación) son excluyentes; el orden de los toggles importa porque
     casoEspecialToggle vuelve a mostrar las preguntas cuando está apagado y los otros dos solo las ocultan. */
  function ctrlSwitches() { casoEspecialToggle(); cambioEquipoToggle(); reasignacionToggle(); mantenimientoToggle(); }
  // <--- hecho por claude code (21-oct-2026): MANTENIMIENTO dentro del CONTROL (y, dentro, REPARACIÓN). Reemplaza las dos
  // preguntas por Comentarios (+ preguntas de reparación). Excluyente con caso especial / cambio de equipo / reasignación.
  function mantenimientoToggle() {
    const on = $('#chk-mantenimiento').is(':checked') && $('#id_tipo_equipo').val() === 'control';
    $('.ctrl-mant').toggleClass('d-none', !on);
    if (!on) $('#chk-reparacion').prop('checked', false);
    $('.ctrl-reparacion').toggleClass('d-none', !(on && $('#chk-reparacion').is(':checked')));
    if (on) { $('.ctrl-preguntas').addClass('d-none'); $('#ctrl-fallas-detalle-wrap').addClass('d-none'); }
  }
  function reaTexto(d) {
    if (!d) return '—';
    return [d.asignado || 'Sin asignar', d.grado ? 'Grado ' + d.grado : '', d.area || '', d.edificio ? 'Edificio ' + d.edificio : ''].filter(Boolean).join(' · ');
  }
  // ¿El maestro nuevo ya tiene otra computadora asignada? Aviso + sugiere su área/grado/edificio
  function reaRevisarNuevo(inp, aviso, campos, compSel) {
    const nombre = ($(inp).val() || '').trim().toLowerCase();
    const propia = $(compSel).val();
    const suyas = Object.keys(COMP_DATA).filter(k => k !== String(propia) && (COMP_DATA[k].asignado || '').trim().toLowerCase() === nombre && nombre);
    if (!suyas.length) { $(aviso).addClass('d-none').text(''); return; }
    const d = COMP_DATA[suyas[0]];
    $(aviso).removeClass('d-none').html('<i class="ti ti-alert-triangle me-1"></i>' + $('<div>').text($(inp).val()).html() + ' ya tiene asignada ' +
      suyas.map(k => $('<div>').text(COMP_DATA[k].asset || k).html()).join(', ') + ' (seguirá asignada). Se tomaron su área y grado.');
    if (d.area) $(campos.a).val(d.area); if (d.grado) $(campos.g).val(d.grado); if (d.edificio) $(campos.e).val(d.edificio);
  }
  function reasignacionToggle() {
    const on = $('#chk-reasignacion').is(':checked') && $('#id_tipo_equipo').val() === 'control';
    $('.ctrl-reasig').toggleClass('d-none', !on);
    $('#id_asignado_nuevo').prop('required', on);
    if (on) {
      $('.ctrl-preguntas').addClass('d-none'); $('#ctrl-fallas-detalle-wrap').addClass('d-none');
      reasignacionAnterior();
    }
  }
  function reasignacionAnterior() {
    const id = $('#id_computadora').val(), d = COMP_DATA[id];
    $('#rea-anterior').text(id && d ? reaTexto(d) : '— selecciona la computadora arriba —');
    if (d) {   // por defecto la computadora conserva su ubicación; se cambia si el maestro nuevo está en otro lado
      if (!$('#id_area_nueva').val()) $('#id_area_nueva').val(d.area || '');
      if (!$('#id_grado_nuevo').val()) $('#id_grado_nuevo').val(d.grado || '');
      if (!$('#id_edificio_nuevo').val()) $('#id_edificio_nuevo').val(d.edificio || '');
    }
  }
  $(document).on('change', '#chk-caso-especial, #chk-cambio-equipo, #chk-reasignacion, #chk-mantenimiento', function(){
    if (this.checked) $('#chk-caso-especial, #chk-cambio-equipo, #chk-reasignacion, #chk-mantenimiento').not(this).prop('checked', false);
    ctrlSwitches();
  });
  $(document).on('change', '#chk-reparacion', mantenimientoToggle);   // <--- hecho por claude code (21-oct-2026): sub-switch de mantenimiento
  $(document).on('input change', '#id_asignado_nuevo', function(){
    reaRevisarNuevo(this, '#rea-aviso', { a: '#id_area_nueva', g: '#id_grado_nuevo', e: '#id_edificio_nuevo' }, '#id_computadora');
  });
  $('#id_computadora').on('change', function(){
    $('#id_area_nueva, #id_grado_nuevo, #id_edificio_nuevo').val('');
    cambioEquipoAnterior(); reasignacionAnterior();
  });
  // Edición de un control: un switch activo (y sin ficha derivada aún) reemplaza las preguntas por su bloque
  function editCtrlSwitches() {
    const esCtrl = $('#form-edit-mant').attr('data-tipo') === 'control' || $('#edit-record-id-badge').text().indexOf('ANAMAESCTRL') === 0;
    if (!esCtrl) return;
    const ceOn = $('#edit-chk-caso-especial').is(':checked') && !$('#edit-chk-caso-especial').prop('disabled');
    const camOn = $('#edit-chk-cambio-equipo').is(':checked') && !$('#edit-chk-cambio-equipo').prop('disabled');
    const reaOn = $('#edit-chk-reasignacion').is(':checked') && !$('#edit-chk-reasignacion').prop('disabled');   // <--- hecho por claude code (12-oct-2026)
    const manOn = $('#edit-chk-mantenimiento').is(':checked') && !$('#edit-chk-mantenimiento').prop('disabled');   // <--- hecho por claude code (21-oct-2026)
    $('.edit-mant').toggleClass('d-none', !manOn);
    if (!manOn) $('#edit-chk-reparacion').prop('checked', false);
    $('.edit-reparacion').toggleClass('d-none', !(manOn && $('#edit-chk-reparacion').is(':checked')));
    $('.edit-reasig').toggleClass('d-none', !reaOn);
    $('#edit-asignado-nuevo').prop('required', reaOn);
    if (reaOn) {
      const dr = COMP_DATA[$('#edit-computadora').val()];
      $('#edit-rea-anterior').text(dr ? reaTexto(dr) : '—');
      if (dr) {
        if (!$('#edit-area-nueva').val()) $('#edit-area-nueva').val(dr.area || '');
        if (!$('#edit-grado-nuevo').val()) $('#edit-grado-nuevo').val(dr.grado || '');
        if (!$('#edit-edificio-nuevo').val()) $('#edit-edificio-nuevo').val(dr.edificio || '');
      }
    }
    $('.edit-preguntas').toggleClass('d-none', ceOn || camOn || reaOn || manOn);
    if (!(ceOn || camOn || reaOn || manOn)) $('#edit-ctrl-fallas-detalle-wrap').toggleClass('d-none', $('#edit-eval-fallas').val() !== 'si');
    $('.edit-entrega').toggleClass('d-none', !ceOn);
    $('#edit-obs-tecnico-mov').prop('disabled', true);                 // el comentario del técnico es el del control
    if (ceOn) {
      $('.lbl-mov-edit').each(function(){ $(this).text($(this).data('rec')); });
      const fh = $('#edit-fecha-hora');
      if (!fh.val()) { const d = new Date(), p2 = x => String(x).padStart(2, '0'); fh.val(d.getFullYear() + '-' + p2(d.getMonth() + 1) + '-' + p2(d.getDate()) + 'T' + p2(d.getHours()) + ':' + p2(d.getMinutes())); }
      $('#edit-ent-equipo-detalle').text($('#edit-computadora option:selected').text() || '—');
    }
    $('.edit-cambio').toggleClass('d-none', !camOn);
    $('#edit-btn-equipo-nuevo').toggleClass('d-none', !camOn);
    if (camOn) { const dc = COMP_DATA[$('#edit-computadora').val()]; $('#edit-cambio-anterior').text(dc ? equipoTexto(dc) : ($('#edit-computadora option:selected').text() || '—')); }
  }
  $(document).on('change', '#edit-chk-caso-especial, #edit-chk-cambio-equipo, #edit-chk-reasignacion, #edit-chk-mantenimiento', function(){
    if (this.checked) $('#edit-chk-caso-especial, #edit-chk-cambio-equipo, #edit-chk-reasignacion, #edit-chk-mantenimiento').not(this).filter(':not(:disabled)').prop('checked', false);
    editCtrlSwitches();
  });
  $(document).on('change', '#edit-chk-reparacion', editCtrlSwitches);   // <--- hecho por claude code (21-oct-2026)
  $(document).on('input change', '#edit-asignado-nuevo', function(){
    reaRevisarNuevo(this, '#edit-rea-aviso', { a: '#edit-area-nueva', g: '#edit-grado-nuevo', e: '#edit-edificio-nuevo' }, '#edit-computadora');
  });

  // <--- hecho por claude code: "¿Cuáles fallas?" solo si respondió Sí (nuevo y editar)
  $(document).on('change', '#id_eval_fallas', function(){ $('#ctrl-fallas-detalle-wrap').toggleClass('d-none', this.value !== 'si'); });
  $(document).on('change', '#edit-eval-fallas', function(){ $('#edit-ctrl-fallas-detalle-wrap').toggleClass('d-none', this.value !== 'si'); });

  // <--- hecho por claude code: auto-llenado al seleccionar impresora
  $('#id_impresora').on('change', function(){
    const data = IMP_DATA[this.value] || {};
    $('#imp-modelo').val(data.modelo || '');
    $('#imp-persona').val(data.asignado || '');
    $('#imp-serie').val(data.serie || '');
  });

  // Toggle serie manual
  $('#chk-serie-mant').on('change', function(){
    const inp = $('#id_serie');
    if ($(this).is(':checked')) {
      inp.removeClass('bg-light text-muted').prop('readonly', false).focus();
    } else {
      const compId = $('#id_computadora').val();
      const serie = compId && COMP_DATA[compId] ? COMP_DATA[compId].serie : '';
      inp.addClass('bg-light text-muted').prop('readonly', true).val(serie);
    }
  });

  // ── Drop zone fotos ──
  const dropZone   = document.getElementById('drop-zone');
  const fotosInput = document.getElementById('fotos-input');
  const preview    = document.getElementById('fotos-preview');
  let   selectedFiles = [];

  dropZone.addEventListener('click',     () => fotosInput.click());
  dropZone.addEventListener('dragover',  e  => { e.preventDefault(); dropZone.classList.add('drag-over'); });
  dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
  dropZone.addEventListener('drop', e => {
    e.preventDefault(); dropZone.classList.remove('drag-over');
    addFiles(e.dataTransfer.files);
  });
  fotosInput.addEventListener('change', () => addFiles(fotosInput.files));

  // <--- hecho por claude code (21-oct-2026): evita re-agregar el MISMO archivo (nombre+tamaño) = no se duplican las fotos
  function _yaEsta(lista, f) { return lista.some(x => x.name === f.name && x.size === f.size); }
  function addFiles(files) {
    for (const f of files) {
      if (selectedFiles.length >= 5) break;
      if (!f.type.startsWith('image/')) continue;
      if (_yaEsta(selectedFiles, f)) continue;
      selectedFiles.push(f);
    }
    renderPreviews();
    // Reconstruir el FileList en el input via DataTransfer
    const dt = new DataTransfer();
    selectedFiles.forEach(f => dt.items.add(f));
    fotosInput.files = dt.files;
  }

  function renderPreviews() {
    preview.innerHTML = '';
    selectedFiles.forEach((f, i) => {
      const url = URL.createObjectURL(f);
      const wrap = document.createElement('div');
      wrap.style.position = 'relative';
      wrap.innerHTML = `<img src="${url}" class="mant-foto-zoom" title="${f.name}">
        <button type="button" class="btn btn-sm btn-ghost-danger" onclick="removeFile(${i})"
          style="position:absolute;top:-4px;right:-4px;padding:0 4px;font-size:.7rem;">✕</button>`;
      preview.appendChild(wrap);
    });
  }
  window.removeFile = i => { selectedFiles.splice(i,1); renderPreviews(); };

  // <--- hecho por claude code: drop-zone de fotos para el modal de EDITAR ──────
  const editDropZone = document.getElementById('edit-drop-zone');
  const editFotosInput = document.getElementById('edit-fotos-input');
  const editPreview  = document.getElementById('edit-fotos-preview');
  let   editSelectedFiles = [];

  if (editDropZone) {
    editDropZone.addEventListener('click',     () => editFotosInput.click());
    editDropZone.addEventListener('dragover',  e  => { e.preventDefault(); editDropZone.classList.add('drag-over'); });
    editDropZone.addEventListener('dragleave', () => editDropZone.classList.remove('drag-over'));
    editDropZone.addEventListener('drop', e => {
      e.preventDefault(); editDropZone.classList.remove('drag-over');
      editAddFiles(e.dataTransfer.files);
    });
    editFotosInput.addEventListener('change', () => editAddFiles(editFotosInput.files));
  }

  function editAddFiles(files) {
    for (const f of files) {
      if (editSelectedFiles.length >= 5) break;
      if (!f.type.startsWith('image/')) continue;
      if (_yaEsta(editSelectedFiles, f)) continue;   // <--- hecho por claude code (21-oct-2026): no duplicar
      editSelectedFiles.push(f);
    }
    editRenderPreviews();
    const dt = new DataTransfer();
    editSelectedFiles.forEach(f => dt.items.add(f));
    editFotosInput.files = dt.files;
  }

  function editRenderPreviews() {
    editPreview.innerHTML = '';
    editSelectedFiles.forEach((f, i) => {
      const url = URL.createObjectURL(f);
      const wrap = document.createElement('div');
      wrap.style.position = 'relative';
      wrap.innerHTML = `<img src="${url}" class="mant-foto-zoom" title="${f.name}">
        <button type="button" class="btn btn-sm btn-ghost-danger" onclick="editRemoveFile(${i})"
          style="position:absolute;top:-4px;right:-4px;padding:0 4px;font-size:.7rem;">✕</button>`;
      editPreview.appendChild(wrap);
    });
  }
  window.editRemoveFile = i => { editSelectedFiles.splice(i,1); editRenderPreviews(); };

  // Reinicia el selector de fotos nuevas y pinta las fotos ya adjuntas del registro
  function resetEditFotos(fotos) {
    editSelectedFiles = [];
    if (editFotosInput) editFotosInput.value = '';
    if (editPreview) editPreview.innerHTML = '';
    const cont = document.getElementById('edit-fotos-actuales');
    if (cont) {
      cont.innerHTML = '';
      (fotos || []).forEach(ft => {
        const wrap = document.createElement('div');
        wrap.style.position = 'relative';
        // <--- hecho por claude code (21-oct-2026): foto guardada con hover para verla grande y "✕" para borrarla
        wrap.innerHTML = `<img src="${ft.url}" class="mant-foto-zoom" title="Pasa el mouse para verla; ✕ para borrar">
          <button type="button" class="btn btn-sm btn-ghost-danger btn-foto-del"
            data-url="${ft.del || ''}" data-id="${ft.id}"
            style="position:absolute;top:-4px;right:-4px;padding:0 4px;font-size:.7rem;" title="Eliminar esta foto">✕</button>`;
        cont.appendChild(wrap);
      });
    }
  }
  window._resetEditFotos = resetEditFotos;

  // <--- hecho por claude code (21-oct-2026): borrar una foto guardada (quitar duplicadas) sin cerrar el modal
  document.addEventListener('click', function (e) {
    const b = e.target.closest('.btn-foto-del');
    if (!b || !b.dataset.url) return;
    if (!confirm('¿Eliminar esta foto? No se puede deshacer.')) return;
    b.disabled = true;
    const fd = new FormData(); fd.append('csrfmiddlewaretoken', window._PAGE.csrf);
    fetch(b.dataset.url, { method: 'POST', body: fd, headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.ok ? r.json() : Promise.reject())
      .then(() => { const w = b.closest('div'); if (w) w.remove(); })
      .catch(() => { b.disabled = false; alert('No se pudo eliminar la foto.'); });
  });

  // <--- hecho por claude code (21-oct-2026): hover para ver la foto más de cerca (preview flotante, funciona dentro del modal)
  (function () {
    let box = null;
    function show(img) {
      if (!box) { box = document.createElement('div'); box.className = 'mant-foto-zoombox'; document.body.appendChild(box); }
      box.innerHTML = '<img src="' + img.src + '">';
      box.style.display = 'block';
      move(img);
    }
    function move(img) {
      if (!box) return;
      const r = img.getBoundingClientRect();
      let left = r.right + 12, top = r.top;
      if (left + 320 > window.innerWidth) left = r.left - 332;   // si no cabe a la derecha, va a la izquierda
      if (left < 8) left = 8;
      top = Math.max(8, Math.min(top, window.innerHeight - 330));
      box.style.left = left + 'px'; box.style.top = top + 'px';
    }
    document.addEventListener('mouseover', function (e) { const i = e.target.closest('img.mant-foto-zoom'); if (i) show(i); });
    document.addEventListener('mouseout', function (e) { if (e.target.closest('img.mant-foto-zoom') && box) box.style.display = 'none'; });
  })();

  // ── Signature pads (reutilizable: técnico + maestro) ──
  function initPad(canvasId, clearBtnId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return { data: () => '' };
    const ctx = canvas.getContext('2d');
    let drawing = false, hasDrawn = false, lastX = 0, lastY = 0;

    function resizeCanvas() {
      const rect = canvas.getBoundingClientRect();
      canvas.width  = rect.width;
      canvas.height = rect.height;
    }
    resizeCanvas();
    new ResizeObserver(resizeCanvas).observe(canvas);

    function getPos(e) {
      const r = canvas.getBoundingClientRect();
      const src = e.touches ? e.touches[0] : e;
      return [src.clientX - r.left, src.clientY - r.top];
    }
    function start(e) { drawing = true; [lastX, lastY] = getPos(e); }
    function move(e) {
      if (!drawing) return;
      hasDrawn = true;
      ctx.beginPath(); ctx.moveTo(lastX, lastY);
      [lastX, lastY] = getPos(e); ctx.lineTo(lastX, lastY);
      ctx.strokeStyle = '#1a1a2e'; ctx.lineWidth = 2; ctx.lineCap = 'round'; ctx.stroke();
    }
    canvas.addEventListener('mousedown', start);
    canvas.addEventListener('mousemove', move);
    canvas.addEventListener('mouseup',   () => drawing = false);
    canvas.addEventListener('mouseleave',() => drawing = false);
    canvas.addEventListener('touchstart', e => { e.preventDefault(); start(e); }, {passive:false});
    canvas.addEventListener('touchmove',  e => { e.preventDefault(); move(e);  }, {passive:false});
    canvas.addEventListener('touchend',  () => drawing = false);

    function clear() { ctx.clearRect(0, 0, canvas.width, canvas.height); hasDrawn = false; }
    const clearBtn = document.getElementById(clearBtnId);
    if (clearBtn) clearBtn.addEventListener('click', clear);
    return { data: () => hasDrawn ? canvas.toDataURL('image/png') : '', clear };
  }

  const padMaestro = initPad('signature-canvas',          'btn-clear-firma');
  const padTecnico = initPad('signature-canvas-tec',      'btn-clear-firma-tec');
  const padEditTec = initPad('edit-signature-canvas-tec', 'edit-btn-clear-firma-tec');
  const padEditMae = initPad('edit-signature-canvas-mae', 'edit-btn-clear-firma-mae');

  // Al guardar la edición → capturar firmas (vacío = no cambia)
  $('#form-edit-mant').on('submit', function(){
    document.getElementById('edit-firma-tecnico-data').value = padEditTec.data();
    document.getElementById('edit-firma-data').value         = padEditMae.data();
  });

  // Antes de enviar el form → capturar ambas firmas (vacío si no se dibujó)
  $('#modalNuevoRegistro form').on('submit', function(){
    document.getElementById('firma_data').value         = padMaestro.data();
    document.getElementById('firma_tecnico_data').value = padTecnico.data();
  });

  // ── Enviar link de firma al maestro (WhatsApp / Copiar) ──
  $(document).on('click', '.btn-firma-link', function () {
    const link = $(this).data('link');
    const rid  = $(this).data('rid');
    const markUrl = $(this).data('mark');
    const msg = `Hola, por favor firme el mantenimiento ${rid} de su equipo en este enlace: ${link}`;
    const wa  = 'https://wa.me/?text=' + encodeURIComponent(msg);
    Swal.fire({
      title: 'Enviar firma al maestro',
      html: `<p class="text-muted small mb-2">Comparte este enlace para que el maestro firme:</p>
             <input id="mant-link" class="form-control form-control-sm mb-3" value="${link}" readonly onclick="this.select()">
             <div class="d-flex gap-2 justify-content-center">
               <a href="${wa}" target="_blank" rel="noopener" id="mant-wa" class="btn" style="background:#25D366;color:#fff">
                 <i class="ti ti-brand-whatsapp me-1"></i>WhatsApp</a>
               <button type="button" id="mant-copy" class="btn btn-primary">
                 <i class="ti ti-copy me-1"></i>Copiar link</button>
             </div>`,
      showConfirmButton: false,
      showCancelButton: true,
      cancelButtonText: 'Cerrar',
      didOpen: () => {
        const mark = () => $.post(markUrl, { csrfmiddlewaretoken: window._PAGE.csrf });
        // WhatsApp: es un <a target="_blank"> → clic directo (funciona en PC y celular).
        // No cerramos el diálogo de inmediato: en móvil eso cancelaba la apertura de WhatsApp.
        document.getElementById('mant-wa').addEventListener('click', () => {
          mark();
          setTimeout(() => { try { Swal.close(); } catch (e) {} }, 800);
        });
        document.getElementById('mant-copy').addEventListener('click', () => {
          navigator.clipboard.writeText(link).then(() => {
            mark();
            Swal.fire({ icon: 'success', title: 'Link copiado', timer: 1200, showConfirmButton: false });
          }, () => {});
        });
      },
    });
  });

  // ── Editar registro ──
  $(document).on('click', '.btn-editar-mant', function(){
    const pk = $(this).data('pk');
    $.getJSON(`/mantenimiento/${pk}/editar/`, function(d){
      $('#edit-record-id-badge').text(d.record_id);
      $('#form-edit-mant').attr('data-tipo', d.tipo_equipo);   // <--- hecho por claude code (28-sep-2026): tipo del registro en edición
      $('#form-edit-mant').attr('action', `/mantenimiento/${pk}/editar/`);
      $('#edit-computadora').val(d.computadora);
      const comp = COMP_DATA[String(d.computadora)] || {};
      $('#edit-model').val(d.model || comp.modelo || '');
      $('#edit-serie').val(d.serie || comp.serie || '');
      $('#edit-asignado-display').val(d.teacher_name || comp.asignado || '');
      $('#edit-area-display').val(comp.area || '');
      $('#edit-grado-display').val(d.grade || comp.grado || '');
      $('#edit-teacher-name').val(d.teacher_name || comp.asignado || '');
      $('#edit-grade').val(d.grade || comp.grado || '');
      $('#edit-tipo-falla').val(String(d.tipo_falla));
      $('#edit-date').val(d.date);
      $('#edit-status').val(d.status);
      $('#edit-solucion').val(d.solucion);
      $('#edit-observaciones').val(d.observaciones);
      // <--- hecho por claude code: el modal de edición se adapta al Control de equipo
      const esCtrl = d.tipo_equipo === 'control';
      const esInsp = d.tipo_equipo === 'inspeccion';
      // <--- hecho por claude code (17-sep-2026): Entrega / Recogida en el modal de edición
      const esMov = d.tipo_equipo === 'entrega' || d.tipo_equipo === 'recogida' || d.tipo_equipo === 'caso_especial';
      $('.edit-entrega').toggleClass('d-none', !esMov);
      $('.lbl-mov-edit').each(function(){ $(this).text($(this).data(d.tipo_equipo === 'entrega' ? 'ent' : 'rec')); });
      // <--- hecho por claude code (28-sep-2026): aviso del control de origen en un caso especial
      $('#edit-ce-aviso').toggleClass('d-none', d.tipo_equipo !== 'caso_especial');
      // <--- hecho por claude code (28-sep-2026): cambio de equipo en edición
      const esCam = d.tipo_equipo === 'cambio_equipo';
      $('.edit-cambio').toggleClass('d-none', !esCam);
      $('#edit-cam-control').text(d.control_origen_rid || '—');
      $('#edit-modelo-nuevo, #edit-serie-nuevo, #edit-ip-nuevo, #edit-obs-equipo-nuevo').val('');
      $('#edit-btn-equipo-nuevo').toggleClass('d-none', esCam);      // en una ficha de cambio ya registrada no se re-registra
      if (esCam) {
        const ant = [d.modelo_anterior, d.serie_anterior ? 'Serie ' + d.serie_anterior : '', d.ip_anterior ? 'IP ' + d.ip_anterior : ''].filter(Boolean).join(' · ');
        const nue = [d.modelo_nuevo, d.serie_nuevo ? 'Serie ' + d.serie_nuevo : '', d.ip_nuevo ? 'IP ' + d.ip_nuevo : ''].filter(Boolean).join(' · ');
        $('#edit-cambio-anterior').text((d.computadora_rid ? d.computadora_rid + ' · ' : '') + (ant || '—'));
        $('#edit-cambio-nuevo').removeClass('vacio').text(nue || '—');
      } else {
        $('#edit-cambio-anterior').text('—'); $('#edit-cambio-nuevo').addClass('vacio').text('Sin registrar');
      }
      // <--- hecho por claude code (28-sep-2026): switches Caso especial / Cambio de equipo al EDITAR un control
      $('#edit-chk-caso-especial').prop('checked', false).prop('disabled', false);
      $('#edit-chk-cambio-equipo').prop('checked', false).prop('disabled', false);
      $('#edit-chk-reasignacion').prop('checked', false).prop('disabled', false);   // <--- hecho por claude code (12-oct-2026)
      // <--- hecho por claude code (21-oct-2026): mantenimiento / reparación
      $('#edit-chk-mantenimiento, #edit-chk-reparacion').prop('checked', false).prop('disabled', false);
      $('#edit-man-existente').addClass('d-none').text('');
      $('#edit-mant-comentario').val(d.mant_comentario || '');
      $('#edit-rep-que-danado').val(d.rep_que_danado || ''); $('#edit-rep-que-reparacion').val(d.rep_que_reparacion || '');
      $('#edit-rep-como-dano').val(d.rep_como_dano || ''); $('#edit-rep-asistido-por').val(d.rep_asistido_por || '');
      const esMan = d.tipo_equipo === 'mantenimiento', esRep = d.tipo_equipo === 'reparacion';
      $('.edit-mant').toggleClass('d-none', !(esMan || esRep));
      $('.edit-reparacion').toggleClass('d-none', !esRep);
      $('#edit-rea-existente').addClass('d-none').text('');
      $('#edit-asignado-nuevo, #edit-area-nueva, #edit-grado-nuevo, #edit-edificio-nuevo').val('');
      $('#edit-rea-aviso').addClass('d-none').text('');
      // ficha de REASIGNACIÓN ya registrada: solo se muestra (el inventario ya se actualizó al crearla)
      const esRea = d.tipo_equipo === 'reasignacion';
      $('.edit-reasig-info').toggleClass('d-none', !esRea);
      if (esRea) {
        $('#edit-rea-control').text(d.control_origen_rid || '—');
        $('#edit-rea-resumen').text((d.computadora_rid || '') + ': ' + (d.asignado_anterior || '—') + (d.grado_anterior ? ' (' + d.grado_anterior + ')' : '') + ' → ' + (d.asignado_nuevo || '—') + (d.grado_nuevo ? ' (' + d.grado_nuevo + ')' : ''));
      }
      $('#edit-ce-existente, #edit-cam-existente').addClass('d-none').text('');
      if (esCtrl) {
        if (d.hijo_caso_especial) { $('#edit-chk-caso-especial').prop('checked', true).prop('disabled', true); $('#edit-ce-existente').removeClass('d-none').text(d.hijo_caso_especial); }
        if (d.hijo_cambio_equipo) { $('#edit-chk-cambio-equipo').prop('checked', true).prop('disabled', true); $('#edit-cam-existente').removeClass('d-none').text(d.hijo_cambio_equipo); }
        if (d.hijo_reasignacion) { $('#edit-chk-reasignacion').prop('checked', true).prop('disabled', true); $('#edit-rea-existente').removeClass('d-none').text(d.hijo_reasignacion); }
        // <--- hecho por claude code (21-oct-2026): mantenimiento / reparación ya generados desde este control
        if (d.hijo_mantenimiento) { $('#edit-chk-mantenimiento').prop('checked', true).prop('disabled', true); $('#edit-man-existente').removeClass('d-none').text(d.hijo_mantenimiento); }
        if (d.hijo_reparacion) { $('#edit-chk-mantenimiento, #edit-chk-reparacion').prop('checked', true).prop('disabled', true); $('#edit-man-existente').removeClass('d-none').text(d.hijo_reparacion); }
      }
      editCtrlSwitches();
      $('#edit-ce-control').text(d.control_origen_rid || '—');
      $('#edit-ent-equipo').prop('checked', !!d.ent_equipo);
      $('#edit-ent-mouse').prop('checked', !!d.ent_mouse_teclado);
      $('#edit-ent-televisor').prop('checked', !!d.ent_televisor);
      $('#edit-ent-control').prop('checked', !!d.ent_control_tv);
      $('#edit-ent-televisor-wrap').prop('hidden', !d.ent_televisor);
      $('#edit-televisor').val(d.televisor ? String(d.televisor) : '');
      movElegirFirmante('#edit-firma-nombre', d.firma_nombre || '');
      $('#edit-fecha-hora').val(d.fecha_hora || '');
      $('#edit-ent-equipo-detalle').text([d.model, d.serie ? 'Serie ' + d.serie : '', d.teacher_name].filter(Boolean).join(' · ') || '—');
      $('.edit-inspeccion').toggleClass('d-none', !esInsp);
      $('#edit-insp-limpio').prop('checked', !!d.insp_limpio);
      $('#edit-insp-ordenado').prop('checked', !!d.insp_ordenado);
      $('#edit-insp-cables').prop('checked', !!d.insp_cables);
      $('#edit-insp-alimentos').prop('checked', !!d.insp_alimentos);
      if (esCtrl || esInsp || esMov) {
        // <--- hecho por claude code: el control muestra al portador ACTUAL del inventario
        const compAct = COMP_DATA[String(d.computadora)] || {};
        $('#edit-asignado-display').val(compAct.asignado || d.teacher_name || '');
        $('#edit-grado-display').val(compAct.grado || d.grade || '');
        $('#edit-teacher-name').val(compAct.asignado || d.teacher_name || '');
        $('#edit-grade').val(compAct.grado || d.grade || '');
        $('#edit-insp-firma-nombre').text(compAct.asignado || d.teacher_name || '—');
      }
      // <--- hecho por claude code (16-oct-2026): préstamo de equipo en el modal de edición
      const esPre = d.tipo_equipo === 'prestamo';
      $('.edit-prestamo, .edit-prestamo-hint').toggleClass('d-none', !esPre);
      $('#edit-prest-solicitante').val(d.prest_solicitante || '');
      $('#edit-prest-cargo').val(d.prest_cargo || '');
      $('#edit-prest-area').val(d.prest_area || '');
      $('#edit-prest-motivo').val(d.prest_motivo || '');
      $('#edit-prest-lugar').val(d.prest_lugar || '');
      $('#edit-prest-desde').val(d.prest_desde || '');
      $('#edit-prest-hasta').val(d.prest_hasta || '');
      $('#edit-prest-accesorios').val(d.prest_accesorios || '');
      $('#edit-prest-sale').prop('checked', esPre ? !!d.prest_sale : true);
      const esImp  = d.tipo_equipo === 'impresora';
      $('.edit-control').toggleClass('d-none', !esCtrl);
      $('.edit-impresora').toggleClass('d-none', !esImp);
      // <--- hecho por claude code: un campo puede tener AMBAS clases (p. ej. Tipo de Falla es
      // edit-no-control Y edit-no-impresora); con toggles independientes el segundo "des-ocultaba"
      // lo que el primero ocultó. Reset y luego ocultar lo que no aplica.
      $('.edit-no-control, .edit-no-impresora, .edit-no-inspeccion, .edit-no-prestamo, .edit-no-mant').removeClass('d-none');
      if (esPre) $('.edit-no-prestamo').addClass('d-none');
      if (esCtrl) $('.edit-no-control').addClass('d-none');
      if (esImp) $('.edit-no-impresora').addClass('d-none');
      if (esInsp || esMov) $('.edit-no-inspeccion').addClass('d-none');
      if (esMan || esRep) $('.edit-no-mant').addClass('d-none');   // <--- hecho por claude code (22-oct-2026): mantenimiento/reparación ocultan Tipo de Falla/Solución/Observaciones y muestran sus campos
      $('#edit-impresora').val(d.impresora ? String(d.impresora) : '');
      if (esImp) {
        const imp = IMP_DATA[String(d.impresora)] || {};
        $('#edit-model').val(d.model || imp.modelo || '');
        $('#edit-serie').val(d.serie || imp.serie || '');
        $('#edit-asignado-display').val(d.teacher_name || imp.asignado || '');
        $('#edit-teacher-name').val(d.teacher_name || imp.asignado || '');
      }
      $('#edit-area').val(d.area || '');
      $('#edit-tipo-mant-imp').val(d.tipo_mant_impresora || '');
      $('#edit-estado-tinta').val(d.estado_tinta || '');
      $('#edit-tipo-tinta').val(d.tipo_tinta || '');
      $('#edit-tinta-negra').prop('checked', !!d.tinta_negra);
      $('#edit-tinta-magenta').prop('checked', !!d.tinta_magenta);
      $('#edit-tinta-amarillo').prop('checked', !!d.tinta_amarillo);
      $('#edit-tinta-cyan').prop('checked', !!d.tinta_cyan);
      $('#edit-eval-trabajo').val(d.eval_trabajo || '');
      $('#edit-eval-fallas').val(d.eval_fallas || '');
      $('#edit-eval-fallas-detalle').val(d.eval_fallas_detalle || '');
      $('#edit-ctrl-fallas-detalle-wrap').toggleClass('d-none', !(esCtrl && d.eval_fallas === 'si'));
      $('#edit-obs-auditora').val(d.obs_auditora || '');
      $('#edit-obs-tecnico').val(d.obs_tecnico || '');
      $('#edit-obs-tecnico').prop('disabled', esMov);
      $('#edit-obs-tecnico-mov').prop('disabled', !esMov).val(esMov ? (d.obs_tecnico || '') : '');
      $('#edit-estado-equipo').val(d.estado_equipo || '');
      // Firma del técnico: mostrar la actual (si existe) y limpiar el lienzo
      padEditTec.clear();
      if (d.firma_tecnico) {
        $('#edit-firma-tec-img').attr('src', d.firma_tecnico);
        $('#edit-firma-tec-actual').show();
      } else {
        $('#edit-firma-tec-actual').hide();
      }
      // Firma del maestro: mostrar la actual (si existe) y limpiar el lienzo
      padEditMae.clear();
      if (d.firma) {
        $('#edit-firma-mae-img').attr('src', d.firma);
        $('#edit-firma-mae-actual').show();
      } else {
        $('#edit-firma-mae-actual').hide();
      }
      // <--- hecho por claude code: reinicia fotos nuevas y muestra las ya adjuntas
      resetEditFotos(d.fotos);
      $('#modalEditarRegistro').modal('show');
    }).fail(() => Swal.fire('Error', 'No se pudo cargar el registro.', 'error'));
  });

  // <--- hecho por claude code: auto-llenado al cambiar impresora en modal editar
  $('#edit-impresora').on('change', function(){
    const imp = IMP_DATA[this.value] || {};
    $('#edit-model').val(imp.modelo || '');
    $('#edit-serie').val(imp.serie || '');
    $('#edit-asignado-display').val(imp.asignado || '');
    $('#edit-teacher-name').val(imp.asignado || '');
  });

  // Auto-fill al cambiar computadora en modal editar
  $('#edit-computadora').on('change', function(){
    const comp = COMP_DATA[this.value] || {};
    $('#edit-model').val(comp.modelo || '');
    $('#edit-serie').val(comp.serie || '');
    $('#edit-asignado-display').val(comp.asignado || '');
    $('#edit-area-display').val(comp.area || '');
    $('#edit-grado-display').val(comp.grado || '');
    $('#edit-teacher-name').val(comp.asignado || '');
    $('#edit-grade').val(comp.grado || '');
    $('#edit-insp-firma-nombre').text(comp.asignado || '—');
  });

  // ── Eliminar registro ──
  $(document).on('click', '.btn-eliminar-mant', function(){
    const pk  = $(this).data('pk');
    const rid = $(this).data('rid');
    Swal.fire({
      title: '¿Eliminar ' + rid + '?',
      text: 'Se eliminará el registro y la numeración se reiniciará desde 001.',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d63939',
    }).then(res => {
      if (res.isConfirmed) {
        const f = $('<form method="post">').attr('action', `/mantenimiento/${pk}/eliminar/`);
        f.append($('<input type="hidden" name="csrfmiddlewaretoken">').val(window._PAGE.csrf));
        $('body').append(f);
        f.submit();
      }
    });
  });

});

})();
