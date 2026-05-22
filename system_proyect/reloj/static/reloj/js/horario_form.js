document.addEventListener('DOMContentLoaded', function(){
  ['id_emp_code','id_nombre_empleado','id_template','id_fecha_inicio','id_fecha_fin'].forEach(function(id){
    const el = document.getElementById(id);
    if (!el) return;
    if (el.type === 'checkbox') el.classList.add('form-check-input');
    else if (el.tagName === 'SELECT') el.classList.add('form-select');
    else el.classList.add('form-control');
  });
  const activo = document.getElementById('id_activo');
  if (activo) activo.classList.add('form-check-input');

  const $emp = $('#id_emp_code');
  if ($emp.length && $emp.is('select')){
    $emp.select2({ theme:'bootstrap-5', width:'100%', placeholder:'Selecciona un empleado...', allowClear:true });
  }

  function syncNombreEmpleado(){
    const sel = document.getElementById('id_emp_code');
    const lblSpan = document.getElementById('selected-employee-label');
    const nombreInput = document.getElementById('id_nombre_empleado');
    if (!sel) return;
    const opt = sel.options[sel.selectedIndex];
    const label = opt ? opt.text : '';
    if (lblSpan) lblSpan.textContent = label || '—';
    if (nombreInput){
      const parts = label.split(' - ');
      nombreInput.value = parts.length > 1 ? parts[1].trim() : '';
    }
  }

  const sel = document.getElementById('id_emp_code');
  if (sel){ sel.addEventListener('change', syncNombreEmpleado); syncNombreEmpleado(); }

  document.getElementById('formHorario')?.addEventListener('submit', function(e){
    const fi = document.getElementById('id_fecha_inicio')?.value;
    const ff = document.getElementById('id_fecha_fin')?.value;
    if (fi && ff && ff < fi){
      e.preventDefault();
      Swal.fire({icon:'warning', title:'Rango inválido', text:'La fecha fin no puede ser anterior a la fecha inicio.'});
    }
  });
});
