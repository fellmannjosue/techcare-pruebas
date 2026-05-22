/* inventario_monitores.js — uses window._MONI_PAGE bridge set in template */

// Registros ya usados (from bridge)
const LABS_USADOS      = new Set(window._MONI_PAGE.labsUsados);
const ASIGNADOS_USADOS = new Set(window._MONI_PAGE.asignadosUsados);
const NEXT_IDS         = window._MONI_PAGE.nextIds;

function checkDuplicado(valor, esLab) {
  const usado = esLab ? LABS_USADOS.has(valor) : ASIGNADOS_USADOS.has(valor);
  document.getElementById('alerta-duplicado').classList.toggle('d-none', !usado);
}

// ── Detección prefijo incorrecto ──
const PREFIX_LABELS = { ANAMONI: 'General', LABBLMONI: 'Lab BL', LABCOLMONI: 'Lab COL', CFPINFO: 'Lab Informática' };

function getExpectedPrefix(assetId) {
  if (!assetId) return null;
  const id = assetId.toUpperCase();
  if (id.includes('LABCOL')) return 'LABCOLMONI';
  if (id.includes('LABBL'))  return 'LABBLMONI';
  if (id.includes('CFP'))    return 'CFPINFO';
  return 'ANAMONI';
}

function checkPrefijo() {
  const labVal = $('#sel-lab-comp').val();
  if (!labVal || $('#id_ubicacion_tipo').val() !== 'laboratorio') {
    $('#alerta-prefijo').addClass('d-none'); return;
  }
  const selectedPrefix = $('input[name="prefix_sel"]:checked').val() || '';
  const expected = getExpectedPrefix(labVal);
  if (expected && selectedPrefix !== expected) {
    const expLabel = PREFIX_LABELS[expected] || expected;
    const selLabel = PREFIX_LABELS[selectedPrefix] || selectedPrefix || '(ninguno)';
    $('#alerta-prefijo-texto').html(
      '<strong>¡Alto!</strong> La computadora es de <strong>' + expLabel +
      '</strong> pero el ID Monitor usa el prefijo <strong>' + selLabel +
      '</strong>. ¿Estás seguro de la selección?'
    );
    $('#alerta-prefijo').removeClass('d-none');
  } else {
    $('#alerta-prefijo').addClass('d-none');
  }
}

$(function(){
  $('#monitores-table').DataTable({
    pageLength: 10, scrollX: true, order: [[0,'desc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });

  // ── Radio prefijo → actualizar asset_id ──
  $('input[name="prefix_sel"]').on('change', function(){
    const next = NEXT_IDS[this.value] || '';
    $('#preview-asset-id').val(next);
    $('#hidden-asset-id').val(next);
    checkPrefijo();
  });

  // Copiar asignado_a al submit si aplica
  $('#form-add-monitor').on('submit', function(){
    if ($('#id_ubicacion_tipo').val() === 'persona') {
      const opt = $('#sel-asig-comp option:selected');
      $('#hidden-asignado-a').val(opt.data('asignado') || '');
    }
  });

  // ── Serie: toggle manual ──
  $('#chk-serie-manual').on('change', function(){
    const $s = $('#id_serie');
    if (this.checked) {
      $s.prop('readonly', false).removeClass('bg-light').val('').focus();
    } else {
      $s.prop('readonly', true).addClass('bg-light').val('');
    }
  });

  // ── Tipo de ubicación ──
  $('#id_ubicacion_tipo').on('change', function(){
    const v = $(this).val();
    $('#campo-laboratorio').toggleClass('d-none', v !== 'laboratorio');
    $('#campo-asignado').toggleClass('d-none', v !== 'persona');
    $('#alerta-duplicado').addClass('d-none');
    if (v !== 'persona') {
      $('#datos-comp-asig').addClass('d-none');
      if (!$('#chk-serie-manual').is(':checked')) $('#id_serie').val('');
    }
  });

  // ── Laboratorio: verificar duplicado y prefijo ──
  $('#sel-lab-comp').on('change', function(){
    const val = $(this).val();
    if (val) { checkDuplicado(val, true); checkPrefijo(); }
    else { $('#alerta-duplicado').addClass('d-none'); $('#alerta-prefijo').addClass('d-none'); }
  });

  // ── Asignado a: auto-cargar datos ──
  $('#sel-asig-comp').on('change', function(){
    const opt = $(this).find('option:selected');
    const id = opt.val();
    if (!id) {
      $('#datos-comp-asig').addClass('d-none');
      if (!$('#chk-serie-manual').is(':checked')) $('#id_serie').val('');
      return;
    }
    checkDuplicado(opt.data('asignado') || '', false);
    $('#info-asignado').val(opt.data('asignado') || '');
    $('#info-area').val(opt.data('area') || '');
    $('#info-grado').val(opt.data('grado') || '');
    $('#datos-comp-asig').removeClass('d-none');
    // Auto-fill serie si no es manual
    if (!$('#chk-serie-manual').is(':checked')) {
      $('#id_serie').val(opt.data('serie') || '').prop('readonly', true).addClass('bg-light');
    }
    $('#hidden-asignado-a').val(opt.data('asignado') || '');
  });
});
