/* inventario_televisores.js */
$(function(){
  $('#televisores-table').DataTable({
    pageLength: 10, scrollX: true, order: [[0,'desc']],
    // <--- hecho por claude code (17-sep-2026): el detalle se ve al pasar el mouse por Modelo; estas columnas quedan ocultas pero siguen buscables
    columnDefs: [{ targets: [3, 4, 5, 6, 7], visible: false }],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });
});
