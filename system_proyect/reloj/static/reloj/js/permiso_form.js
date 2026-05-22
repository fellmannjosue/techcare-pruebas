document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('form input, form textarea, form select').forEach(function(el){
    if (el.type === 'checkbox') el.classList.add('form-check-input');
    else if (el.tagName === 'SELECT') el.classList.add('form-select');
    else if (!el.classList.contains('form-control')) el.classList.add('form-control');
  });

  document.getElementById('formPermiso')?.addEventListener('submit', function(e){
    const fi = document.getElementById('id_fecha_inicio')?.value;
    const ff = document.getElementById('id_fecha_fin')?.value;
    if (fi && ff && ff < fi){
      e.preventDefault();
      Swal.fire({icon:'warning', title:'Rango inválido', text:'La fecha fin no puede ser anterior a la fecha inicio.'});
    }
  });
});
