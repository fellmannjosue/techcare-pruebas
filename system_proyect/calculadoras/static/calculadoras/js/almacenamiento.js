const UNITS = { B: 1, KB: 1024, MB: 1024**2, GB: 1024**3, TB: 1024**4 };
function fmt(n) {
  if (n >= 1e12) return n.toExponential(4);
  return n.toLocaleString('es-HN', {maximumFractionDigits: 6});
}
function calcStorage(){
  const val = parseFloat($('#inp-storage-val').val()) || 0;
  const unit = $('#inp-storage-unit').val();
  if (val <= 0) { $('#res-storage').addClass('d-none'); return; }
  const bytes = val * UNITS[unit];
  $('#res-storage').removeClass('d-none');
  Object.keys(UNITS).forEach(u => $(`#res-${u}`).text(fmt(bytes / UNITS[u])));
}
$('#inp-storage-val, #inp-storage-unit').on('input change', calcStorage);
