/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
(function(){
  var btn = document.getElementById('btn-eliminar');
  if(!btn) return;
  btn.addEventListener('click', function(){
    Swal.fire({
      icon: 'warning',
      title: '¿Eliminar este sponsor?',
      html: 'Se borrará también su <strong>historial de ingresos, padrinazgos y correspondencia</strong>.<br>Esta acción no se puede deshacer.',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d63939'
    }).then(function(r){
      if(r.isConfirmed) document.getElementById('form-eliminar').submit();
    });
  });
})();
