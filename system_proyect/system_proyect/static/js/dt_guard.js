/* dt_guard.js — evita el error "_DT_CellIndex" de DataTables en tablas vacías.
   Cuando una tabla solo tiene la fila placeholder con <td colspan="N"> (sin datos),
   DataTables falla al indexar las celdas. Este parche, antes de inicializar, vacía
   esa fila placeholder para que DataTables arranque limpio (mostrando su propio
   mensaje de "sin registros") y devuelva una API válida. */
(function () {
  var $ = window.jQuery;
  if (!$ || !$.fn || !$.fn.dataTable || $.fn.dataTable.__guarded) return;

  function prep(tabla) {
    var $body = $(tabla).children('tbody');
    var $rows = $body.children('tr');
    // Solo fila(s) placeholder con colspan y sin filas de datos reales → vaciar tbody
    if ($rows.length && $rows.children('td[colspan], th[colspan]').length &&
        $rows.length === $rows.has('td[colspan], th[colspan]').length) {
      $body.empty();
    }
  }

  function wrap(real) {
    var w = function () {
      try { this.each(function () { prep(this); }); } catch (e) {}
      return real.apply(this, arguments);
    };
    $.extend(w, real);     // conserva .ext, defaults, etc.
    w.__guarded = true;
    return w;
  }

  $.fn.dataTable = wrap($.fn.dataTable);
  $.fn.DataTable = wrap($.fn.DataTable);
})();
