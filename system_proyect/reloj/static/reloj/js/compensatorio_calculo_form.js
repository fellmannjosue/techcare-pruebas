const MIN_DIA = window._PAGE.minutosDia;

function actualizarPreview() {
  const dias = parseFloat(document.querySelector('[name=dias_adeudados]').value);
  if (isNaN(dias) || dias <= 0) {
    document.getElementById('preview-calculo').style.display = 'none';
    return;
  }
  const minutos = Math.round(dias * 480);
  const diasHab = Math.ceil(minutos / MIN_DIA);
  document.getElementById('prev-min').textContent  = minutos.toLocaleString() + ' min';
  document.getElementById('prev-dias').textContent = diasHab + ' días';
  document.getElementById('preview-calculo').style.display = '';
}

document.querySelector('[name=dias_adeudados]').addEventListener('input', actualizarPreview);

// Autocompletar nombre al seleccionar empleado
document.getElementById('id_emp_code').addEventListener('change', function () {
  const nombre = window._PAGE.empMap[this.value] || '';
  document.querySelector('[name=nombre_empleado]').value = nombre;
});
