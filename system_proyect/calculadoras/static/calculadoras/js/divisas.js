const CSRF     = window._PAGE.csrf;
const URL_TASA = window._PAGE.urlTasa;
const URL_AUTO = window._PAGE.urlAuto;
const TASAS    = Object.assign({}, window._PAGE.tasas);

// Calcular en tiempo real
$(document).on('input', '.input-monto', function(){
  const moneda = $(this).data('moneda');
  const monto  = parseFloat($(this).val()) || 0;
  const tasa   = TASAS[moneda] || 0;
  if (monto > 0 && tasa > 0) {
    const resultado = monto * tasa;
    $(`.resultado-div-${moneda}`).removeClass('d-none');
    $(`.resultado-lps-${moneda}`).text('L. ' + resultado.toLocaleString('es-HN', {minimumFractionDigits:2, maximumFractionDigits:2}));
  } else {
    $(`.resultado-div-${moneda}`).addClass('d-none');
  }
});

// Ajuste manual
$(document).on('click', '.btn-guardar-tasa', function(){
  const moneda = $(this).data('moneda');
  const tasa   = $(`.input-nueva-tasa[data-moneda="${moneda}"]`).val();
  const fecha  = $(`.input-fecha-tasa[data-moneda="${moneda}"]`).val();
  if (!tasa || parseFloat(tasa) <= 0) {
    Swal.fire({icon:'warning', title:'Ingresa una tasa válida'}); return;
  }
  $.ajax({
    url: URL_TASA, method: 'POST',
    headers: {'X-CSRFToken': CSRF},
    data: { moneda, tasa, fecha },
    success: function(res){
      if (res.ok){
        TASAS[moneda] = parseFloat(res.tasa);
        $(`.tasa-display-${moneda}`).text('L. ' + res.tasa);
        $(`.tasa-fecha-${moneda}`).text(res.fecha);
        Swal.fire({icon:'success', title:'Tasa actualizada', timer:1200, showConfirmButton:false});
      } else {
        Swal.fire({icon:'error', title:'Error', text: res.error});
      }
    }
  });
});

// Auto-fetch desde internet
$('#btn-auto-tasas').on('click', function(){
  const $btn = $(this).prop('disabled', true).html('<i class="ti ti-loader me-1"></i>Consultando...');
  $.ajax({
    url: URL_AUTO, method: 'GET',
    headers: {'X-CSRFToken': CSRF},
    success: function(res){
      $btn.prop('disabled', false).html('<i class="ti ti-refresh me-1"></i>Actualizar tasas desde internet');
      if (res.ok){
        Object.entries(res.tasas).forEach(([moneda, info]) => {
          TASAS[moneda] = parseFloat(info.tasa);
          $(`.tasa-display-${moneda}`).text('L. ' + info.tasa);
          $(`.tasa-fecha-${moneda}`).text(info.fecha);
          // Recalcular si hay monto ingresado
          $(`.input-monto[data-moneda="${moneda}"]`).trigger('input');
        });
        $('#alerta-tasas').removeClass('d-none alert-danger')
          .addClass('alert alert-success')
          .html('<i class="ti ti-check me-1"></i>Tasas actualizadas desde <strong>' + res.fuente + '</strong> · ' + new Date().toLocaleTimeString('es-HN'));
      } else {
        $('#alerta-tasas').removeClass('d-none').addClass('alert alert-danger')
          .html('<i class="ti ti-alert-circle me-1"></i>' + res.error);
      }
    },
    error: function(){
      $btn.prop('disabled', false).html('<i class="ti ti-refresh me-1"></i>Actualizar tasas desde internet');
      $('#alerta-tasas').removeClass('d-none').addClass('alert alert-danger')
        .html('<i class="ti ti-alert-circle me-1"></i>Error de red al consultar la API.');
    }
  });
});
