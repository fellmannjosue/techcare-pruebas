$(function(){
  $('#tablaAsignaciones').DataTable({
    pageLength: 25, order: [[0,'asc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json' }
  });

  const baseEditUrl = window._PAGE.baseEditUrl;

  $(document).on('click', '.link-edit', function(e){
    e.preventDefault();
    const pk = $(this).data('id');
    if (!pk) return;
    $.ajax({
      url: baseEditUrl.replace('99999', pk),
      headers: {'X-Requested-With':'XMLHttpRequest'},
      success: function(html){
        $('#modalAsignacionContent').html(html);
        $('#editarAsignacionModal').modal('show');
      },
      error: function(){
        Swal.fire({icon:'error', title:'Error', text:'No se pudo cargar el formulario.'});
      }
    });
  });

  $(document).on('submit', '#formEditarAsignacion', function(e){
    e.preventDefault();
    const form = $(this);
    $.ajax({
      url: form.attr('action'), method:'POST',
      headers: {'X-Requested-With':'XMLHttpRequest'},
      data: form.serialize(),
      success: function(res){
        if (res.success){
          $('#editarAsignacionModal').modal('hide');
          Swal.fire({icon:'success', title:'Listo', text:'Asignación actualizada.', timer:1800, showConfirmButton:false})
            .then(() => location.reload());
        } else {
          Swal.fire({icon:'error', title:'Error', text:'Revisa los campos e intenta de nuevo.'});
        }
      },
      error: function(){
        Swal.fire({icon:'error', title:'Error', text:'Error al guardar la asignación.'});
      }
    });
  });

  if (window._PAGE.messages && window._PAGE.messages.length) {
    Swal.fire({icon:'success', title:'Listo', html: window._PAGE.messages.join('<br>'), timer:2400, showConfirmButton:false});
  }
});
