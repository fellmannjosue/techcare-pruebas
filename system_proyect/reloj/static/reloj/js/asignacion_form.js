document.addEventListener('DOMContentLoaded', function(){
  ['id_emp_code','id_template','id_date_start','id_date_end','id_observacion'].forEach(function(id){
    const el = document.getElementById(id);
    if (el && !el.classList.contains('form-control')){
      if (el.tagName === 'SELECT') el.classList.add('form-select');
      else el.classList.add('form-control');
    }
  });

  const $emp = $('#id_emp_code');
  if ($emp.length && $emp.is('select')){
    $emp.select2({ theme:'bootstrap-5', width:'100%', placeholder:'Selecciona un empleado...', allowClear:true });
  }

  const form = document.getElementById('frmAsignacion');
  form?.addEventListener('submit', function(e){
    const fi = document.getElementById('id_date_start')?.value;
    const ff = document.getElementById('id_date_end')?.value;
    if (fi && ff && ff < fi){ e.preventDefault(); alert('La Fecha fin debe ser mayor o igual que la Fecha inicio.'); }
  });
});
