/* enfermeria/js/atencion_form.js */
$(function () {
  $('#student-select').select2({ placeholder: '-- Selecciona un alumno --', width: '100%' });

  $('#student-select').on('change', function () {
    var grado = $(this).find('option:selected').data('grado') || '';
    $('#grade-display').val(grado);
    $('#student_grade').val(grado);
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
