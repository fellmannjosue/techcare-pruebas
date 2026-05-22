$(function(){
  $('#tblPlantillas').DataTable({
    pageLength: 10,
    order: [[1,'asc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json' }
  });
});
