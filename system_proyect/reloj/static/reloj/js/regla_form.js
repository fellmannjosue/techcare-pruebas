function el(id){ return document.getElementById(id); }

function toggleHorasPorTrabaja(){
  const chk = el('id_trabaja');
  const disabled = chk ? !chk.checked : false;
  ['id_entrada_manana','id_salida_manana','id_entrada_tarde','id_salida_tarde'].forEach(function(id){
    const input = el(id);
    if (input){ input.disabled = disabled; if (disabled) input.value = ''; }
  });
}

function validarParesHoras(e){
  const trabaja = el('id_trabaja') ? el('id_trabaja').checked : true;
  if (!trabaja) return true;
  const em = el('id_entrada_manana')?.value || '', sm = el('id_salida_manana')?.value || '';
  const et = el('id_entrada_tarde')?.value  || '', st = el('id_salida_tarde')?.value   || '';
  if ((em && !sm) || (!em && sm) || (et && !st) || (!et && st)){
    e.preventDefault();
    alert('Completa las parejas de horas: Entrada/Salida Mañana y/o Entrada/Salida Tarde.');
    return false;
  }
  return true;
}

document.addEventListener('DOMContentLoaded', function(){
  ['id_trabaja','id_entrada_manana','id_salida_manana','id_entrada_tarde','id_salida_tarde','id_weekday']
    .forEach(function(id){
      const node = el(id);
      if (!node) return;
      if (node.type === 'checkbox') node.classList.add('form-check-input');
      else if (!node.classList.contains('form-control') && node.tagName === 'INPUT') node.classList.add('form-control');
      else if (node.tagName === 'SELECT') node.classList.add('form-select');
    });

  document.querySelectorAll('input[id^="id_weekdays_"]').forEach(function(cb){ cb.classList.add('form-check-input'); });

  const chk = el('id_trabaja');
  if (chk){ chk.addEventListener('change', toggleHorasPorTrabaja); toggleHorasPorTrabaja(); }

  const form = document.querySelector('form');
  if (form) form.addEventListener('submit', validarParesHoras);
});
