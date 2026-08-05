/* enfermeria/js/atencion_form.js */
$(function () {
  $('#student-select').select2({ placeholder: '-- Selecciona un alumno --', width: '100%' });

  $('#student-select').on('change', function () {
    var opt   = $(this).find('option:selected');
    var grado = opt.data('grado') || '';
    $('#grade-display').val(grado);
    $('#student_grade').val(grado);

    // <--- hecho por claude code: el correo del padre se llena solo al elegir al alumno.
    // Si no hay correo en la base, se avisa para que lo escriban a mano.
    var correo = (opt.data('email') || '').toString().trim();
    $('#email-padre').val(correo);
    $('#email-aviso').text(correo ? '' : 'Este alumno no tiene correo registrado. Escríbelo si deseas enviar la ficha.')
                     .css('color', correo ? '' : '#c2410c');
  });

  $('#atenciones-table').DataTable({
    order: [[2, 'desc']],
    pageLength: 15,
    lengthChange: false,
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });

  window.confirmDelete = function (id) {
    Swal.fire({
      title: '¿Eliminar esta atención?', icon: 'warning',
      showCancelButton: true, confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar'
    }).then(function (result) {
      if (result.isConfirmed) window.location.href = '?delete=' + id;
    });
  };
});
