/* inventario_datashows.js */
$(function(){
  $('#datashows-table').DataTable({
    pageLength: 10, scrollX: true, order: [[0,'desc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });
});
