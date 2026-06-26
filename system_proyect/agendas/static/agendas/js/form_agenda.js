/* form_agenda.js – agendas */

/* Recargar página al cambiar grado (para traer las materias correctas) */
var gradoSelect = document.getElementById('gradoSelect');
if (gradoSelect) {
  gradoSelect.addEventListener('change', function () {
    document.getElementById('formAgenda').submit();
  });
}
