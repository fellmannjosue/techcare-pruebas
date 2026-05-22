// directorio_telefonos.js

$(function () {
  $('#tablaDirectorio').DataTable({
    pageLength: 25,
    order: [[1, 'asc']],
    columnDefs: [{ orderable: false, targets: [3] }],
    language: {
      search: 'Buscar:',
      lengthMenu: 'Mostrar _MENU_ registros',
      zeroRecords: 'Sin resultados',
      info: 'Mostrando _START_–_END_ de _TOTAL_',
      infoEmpty: 'Sin registros',
      infoFiltered: '(filtrado de _MAX_)',
      paginate: { first: '«', last: '»', next: '›', previous: '‹' }
    }
  });
});
