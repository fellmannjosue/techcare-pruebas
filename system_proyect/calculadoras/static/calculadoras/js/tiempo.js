// Horas → Días
$('#inp-horas').on('input', function(){
  const h = parseFloat($(this).val()) || 0;
  if (h <= 0) { $('#res-horas-dias').addClass('d-none'); return; }
  const dias = Math.floor(h / 24);
  const hrest = h % 24;
  $('#res-horas-dias').removeClass('d-none');
  $('#res-dias-val').text(dias + (dias === 1 ? ' día' : ' días'));
  $('#res-horas-rest').text(hrest > 0 ? `+ ${hrest.toFixed(1)} horas restantes` : '');
});

// Minutos → Horas
$('#inp-minutos').on('input', function(){
  const m = parseFloat($(this).val()) || 0;
  if (m <= 0) { $('#res-min-horas').addClass('d-none'); return; }
  const h = Math.floor(m / 60);
  const mrest = m % 60;
  $('#res-min-horas').removeClass('d-none');
  $('#res-horas-val').text(h + (h === 1 ? ' hora' : ' horas'));
  $('#res-min-rest').text(mrest > 0 ? `+ ${mrest} minutos restantes` : '');
});

// Fecha a Fecha
function calcFechas(){
  const fi = new Date($('#inp-fecha-inicio').val());
  const ff = new Date($('#inp-fecha-fin').val());
  if (!$('#inp-fecha-inicio').val() || !$('#inp-fecha-fin').val()) return;
  const diff = Math.round((ff - fi) / (1000 * 60 * 60 * 24));
  if (isNaN(diff)) return;
  const absDiff = Math.abs(diff);
  $('#res-fechas').removeClass('d-none');
  $('#res-dias-total').text(absDiff);
  $('#res-semanas').text((absDiff / 7).toFixed(1));
  $('#res-meses').text((absDiff / 30.44).toFixed(1));
}
$('#inp-fecha-inicio, #inp-fecha-fin').on('change', calcFechas);
