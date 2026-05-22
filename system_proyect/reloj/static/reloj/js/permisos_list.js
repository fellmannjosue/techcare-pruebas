const CSRF = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

function aprobarRechazar(pk, action){
  Swal.fire({
    title: action === 'aprobar' ? '¿Aprobar este permiso?' : '¿Rechazar este permiso?',
    icon: action === 'aprobar' ? 'question' : 'warning',
    showCancelButton: true,
    confirmButtonText: action === 'aprobar' ? 'Sí, aprobar' : 'Sí, rechazar',
    cancelButtonText: 'Cancelar',
  }).then(function(res){
    if (!res.isConfirmed) return;
    fetch(`/reloj/permisos/${pk}/aprobar/`, {
      method: 'POST',
      headers: {'X-CSRFToken': CSRF, 'X-Requested-With': 'XMLHttpRequest',
                'Content-Type': 'application/x-www-form-urlencoded'},
      body: `action=${action}`
    }).then(r => r.json()).then(function(data){
      if (data.success){
        Swal.fire({icon:'success', title:'Listo', timer:1500, showConfirmButton:false})
          .then(() => location.reload());
      } else {
        Swal.fire({icon:'error', title:'Error', text:'No se pudo actualizar el permiso.'});
      }
    }).catch(function(){
      Swal.fire({icon:'error', title:'Error', text:'Error de red.'});
    });
  });
}

document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.btn-aprobar').forEach(function(btn){
    btn.addEventListener('click', function(){ aprobarRechazar(this.dataset.id, 'aprobar'); });
  });
  document.querySelectorAll('.btn-rechazar').forEach(function(btn){
    btn.addEventListener('click', function(){ aprobarRechazar(this.dataset.id, 'rechazar'); });
  });
});
