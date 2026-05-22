/* filtro_computadoras.js */
$(function(){
  function timestamp() {
    const d = new Date(), pad = n => n.toString().padStart(2,'0');
    return `${d.getFullYear()}${pad(d.getMonth()+1)}${pad(d.getDate())}_${pad(d.getHours())}${pad(d.getMinutes())}`;
  }

  var table = $('#computadoras-table').DataTable({
    pageLength: 10,
    order: [[8,'desc']],
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' },
    dom: 'Bfrtip',
    buttons: [
      { extend: 'print', text: 'Imprimir', title: 'Computadoras filtradas', exportOptions: { columns: ':visible' } },
      { extend: 'excelHtml5', text: 'Exportar a Excel', title: 'Computadoras_filtradas_' + timestamp(),
        exportOptions: { columns: ':visible', modifier: { search: 'applied', order: 'applied' },
          format: { body: function(data){ return (data||'').toString().replace(/<[^>]*>/g,''); } } } }
    ]
  });

  $('#btn-imprimir').on('click', function(){ table.button('.buttons-print').trigger(); });
  $('#btn-excel').on('click', function(){ table.button('.buttons-excel').trigger(); });

  $('#column-search, #column-filter').on('keyup change', function(){
    var col = $('#column-filter').val(), term = $('#column-search').val();
    if (!col) { table.search(term).draw(); }
    else { table.column(col).search(term).draw(); }
  });

  $('#clear-filter').on('click', function(e){
    e.preventDefault();
    $('#column-filter').val(''); $('#column-search').val('');
    table.search('').columns().search('').draw();
  });

  var tbodyEl = $('#computadoras-table tbody').get(0);
  function resaltar(){
    var term = ($('#column-search').val()||'').trim();
    if (!tbodyEl) return;
    if (!term) { new Mark(tbodyEl).unmark(); return; }
    var col = $('#column-filter').val();
    if (col) {
      var idx = parseInt(col,10)+1;
      new Mark(tbodyEl).unmark({ done: function(){
        $('#computadoras-table tbody tr td:nth-child('+idx+')').each(function(){
          new Mark(this).mark(term, { separateWordSearch:false, caseSensitive:false, acrossElements:true, className:'match-bold' });
        });
      }});
    } else {
      new Mark(tbodyEl).unmark({ done: function(){
        new Mark(tbodyEl).mark(term, { separateWordSearch:false, caseSensitive:false, acrossElements:true, className:'match-bold' });
      }});
    }
  }
  resaltar();
  table.on('draw', resaltar);
  $('#column-search, #column-filter').on('keyup change', resaltar);
});
