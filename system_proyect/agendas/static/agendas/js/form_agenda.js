/* form_agenda.js – agendas */

/* Recargar página al cambiar grado (para traer las materias correctas) */
var gradoSelect = document.getElementById('gradoSelect');
if (gradoSelect) {
  gradoSelect.addEventListener('change', function () {
    document.getElementById('formAgenda').submit();
  });
}

/* Asociadas dinámicas */
var asociadaCount = 0;
var btnAdd = document.getElementById('btnAddAsociada');
if (btnAdd) {
  btnAdd.addEventListener('click', function () {
    if (asociadaCount >= 5) return;
    asociadaCount++;
    var n      = asociadaCount;
    var nombre = 'asociada_' + n;
    var html =
      '<div class="mb-2 border rounded p-2" id="aso-' + n + '">' +
        '<div class="row g-1 align-items-center mb-1">' +
          '<div class="col-auto">' +
            '<input type="text" name="materia_Asociadas[]" class="form-control form-control-sm"' +
            ' placeholder="Nombre materia" style="width:160px;" id="aso-nombre-' + n + '">' +
          '</div>' +
          '<div class="col-auto">' +
            '<button type="button" class="btn btn-sm btn-ghost-danger"' +
            ' onclick="document.getElementById(\'aso-' + n + '\').remove(); asociadaCount--;">' +
            '<i class="ti ti-trash"></i></button>' +
          '</div>' +
        '</div>' +
        '<div class="table-responsive">' +
          '<table class="table table-sm table-bordered mb-0">' +
            '<thead><tr>' +
            '<th>Lunes</th><th>Martes</th><th>Miércoles</th><th>Jueves</th><th>Viernes</th><th>Nota</th>' +
            '</tr></thead>' +
            '<tbody><tr>' +
              '<td><input type="text" name="lunes_Asociadas_'     + nombre + '" class="form-control form-control-sm"></td>' +
              '<td><input type="text" name="martes_Asociadas_'    + nombre + '" class="form-control form-control-sm"></td>' +
              '<td><input type="text" name="miercoles_Asociadas_' + nombre + '" class="form-control form-control-sm"></td>' +
              '<td><input type="text" name="jueves_Asociadas_'    + nombre + '" class="form-control form-control-sm"></td>' +
              '<td><input type="text" name="viernes_Asociadas_'   + nombre + '" class="form-control form-control-sm"></td>' +
              '<td><input type="text" name="nota_Asociadas_'      + nombre + '" class="form-control form-control-sm"></td>' +
            '</tr></tbody>' +
          '</table>' +
        '</div>' +
      '</div>';
    document.getElementById('asociadas-container').insertAdjacentHTML('beforeend', html);
  });
}
