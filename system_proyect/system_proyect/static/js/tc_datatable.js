/* tc_datatable.js — <--- hecho por claude code
   Init ÚNICO de DataTables para todo el sistema. Cualquier <table class="tc-datatable">
   se inicializa sola con el locale ES y estilo del portal, sin repetir el bloque en
   cada JS de página. Respeta data-order / data-page-length si están presentes.
   Convive con dt_guard.js (que ya evita el crash de tablas vacías). */
(function () {
  if (typeof window.jQuery === 'undefined' || !window.jQuery.fn || !window.jQuery.fn.DataTable) return;
  var $ = window.jQuery;
  document.addEventListener('DOMContentLoaded', function () {
    $('table.tc-datatable').each(function () {
      var el = this;
      if ($.fn.dataTable.isDataTable(el)) return;
      var $el = $(el);
      var opts = {
        pageLength: parseInt($el.data('page-length'), 10) || 10,
        order: [],
        autoWidth: false,
        responsive: $el.data('responsive') !== false,
        language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/es-ES.json' },
        dom: "<'tc-dt-top row align-items-center'<'col-sm-6'l><'col-sm-6'f>>" +
             "<'table-responsive't>" +
             "<'tc-dt-bottom row align-items-center'<'col-sm-5'i><'col-sm-7'p>>",
      };
      var ord = $el.data('order');
      if (ord !== undefined && ord !== '') {
        // data-order="0:desc"
        var p = String(ord).split(':');
        opts.order = [[parseInt(p[0], 10) || 0, p[1] || 'asc']];
      }
      try { $el.DataTable(opts); } catch (e) { /* dt_guard maneja tablas vacías */ }
    });
  });
})();
