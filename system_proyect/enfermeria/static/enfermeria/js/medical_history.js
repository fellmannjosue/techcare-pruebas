/* enfermeria/js/medical_history.js */
$(function () {
  var $sel  = $('#studentSelect');
  var $cont = $('#historyContainer');
  var table = $('#historyTable').DataTable({
    order: [[1, 'desc']], pageLength: 25, lengthChange: false,
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' },
    columns: [
      { data: 'index' }, { data: 'date_time' }, { data: 'grade' },
      { data: 'reason' }, { data: 'treatment' }, { data: 'attendant' }
    ]
  });

  $sel.find('option').each(function () {
    var txt = $(this).text().trim();
    if (!txt || txt.startsWith('--')) return;
    var parts = txt.split(' '), t = parts.length;
    $(this).text(parts.slice(0, t - 2).join(' ') + ' ' + parts.slice(t - 2).join(' '));
  });

  $sel.select2({ placeholder: '-- Seleccionar Estudiante --', width: '100%', minimumResultsForSearch: 0 });

  $sel.on('change', function () {
    var student = $(this).val();
    var url = $(this).data('url') + '?student=' + encodeURIComponent(student);
    table.clear().draw();
    $cont.hide();
    if (!student) return;
    fetch(url, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r); })
      .then(function (json) {
        var lista = json.history || [];
        if (!lista.length) {
          table.rows.add([{
            index: '', date_time: '<span data-order="">Sin registros.</span>',
            grade: '', reason: '', treatment: '', attendant: ''
          }]).draw();
        } else {
          table.rows.add(lista.map(function (h, i) {
            var parts   = h.date_time.split(' ');
            var dt      = parts[0], tm = parts[1];
            var datePts = dt.split('-');
            var dd = datePts[0], mm = datePts[1], yyyy = datePts[2];
            return {
              index: i + 1,
              date_time: '<span data-order="' + yyyy + '-' + mm + '-' + dd + ' ' + tm + '">' + h.date_time + '</span>',
              grade: h.grade, reason: h.reason, treatment: h.treatment, attendant: h.attendant
            };
          })).draw();
        }
        $cont.fadeIn(150);
      });
  });
});
