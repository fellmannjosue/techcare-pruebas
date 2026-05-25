// ── Entre dos horas ──
function calcEntreHoras() {
  const inicio = document.getElementById('inp-hora-inicio').value;
  const fin    = document.getElementById('inp-hora-fin').value;
  const resDiv  = document.getElementById('res-entre-horas');
  const errDiv  = document.getElementById('res-eh-error');

  resDiv.classList.add('d-none');
  errDiv.classList.add('d-none');
  if (!inicio || !fin) return;

  const [h1, m1] = inicio.split(':').map(Number);
  const [h2, m2] = fin.split(':').map(Number);
  const totalMinInicio = h1 * 60 + m1;
  const totalMinFin    = h2 * 60 + m2;
  const diffMin = totalMinFin - totalMinInicio;

  if (diffMin <= 0) {
    errDiv.classList.remove('d-none');
    return;
  }

  const horas = Math.floor(diffMin / 60);
  const mins  = diffMin % 60;
  const horasDec = (diffMin / 60).toFixed(2);

  // Texto principal: "1 hora 53 minutos" / "53 minutos" / "2 horas"
  let principal = '';
  if (horas > 0 && mins > 0) {
    principal = `${horas} hora${horas !== 1 ? 's' : ''} ${mins} minuto${mins !== 1 ? 's' : ''}`;
  } else if (horas > 0) {
    principal = `${horas} hora${horas !== 1 ? 's' : ''}`;
  } else {
    principal = `${mins} minuto${mins !== 1 ? 's' : ''}`;
  }

  document.getElementById('res-eh-principal').textContent  = principal;
  document.getElementById('res-eh-horas-dec').textContent  = horasDec + ' h';
  document.getElementById('res-eh-minutos').textContent    = diffMin + ' min';
  document.getElementById('res-eh-nota').textContent =
    `De ${inicio} a ${fin}`;
  resDiv.classList.remove('d-none');
}

document.getElementById('inp-hora-inicio').addEventListener('change', calcEntreHoras);
document.getElementById('inp-hora-fin').addEventListener('change', calcEntreHoras);
document.getElementById('inp-hora-inicio').addEventListener('input', calcEntreHoras);
document.getElementById('inp-hora-fin').addEventListener('input', calcEntreHoras);

// ── Horas → Días ──
$('#inp-horas').on('input', function(){
  const h = parseFloat($(this).val()) || 0;
  if (h <= 0) { $('#res-horas-dias').addClass('d-none'); return; }
  const dias  = Math.floor(h / 24);
  const hrest = h % 24;
  $('#res-horas-dias').removeClass('d-none');
  $('#res-dias-val').text(dias + (dias === 1 ? ' día' : ' días'));
  $('#res-horas-rest').text(hrest > 0 ? `+ ${hrest.toFixed(1)} horas restantes` : '');
});

// ── Minutos → Horas ──
$('#inp-minutos').on('input', function(){
  const m = parseFloat($(this).val()) || 0;
  if (m <= 0) { $('#res-min-horas').addClass('d-none'); return; }
  const h    = Math.floor(m / 60);
  const mrest = m % 60;
  $('#res-min-horas').removeClass('d-none');
  $('#res-horas-val').text(h + (h === 1 ? ' hora' : ' horas'));
  $('#res-min-rest').text(mrest > 0 ? `+ ${mrest} minutos restantes` : '');
});

// ── Fecha a Fecha ──
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
