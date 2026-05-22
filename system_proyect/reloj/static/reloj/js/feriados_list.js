$(function(){
  $('#tblFeriados').DataTable({
    pageLength: 25, order: [[0,'desc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json' }
  });
});
