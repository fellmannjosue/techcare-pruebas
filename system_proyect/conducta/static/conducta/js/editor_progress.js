// editor_progress.js

document.addEventListener('DOMContentLoaded', function () {
  var MAX_ASOCIADAS = 5;
  var btnAdd = document.getElementById('btnAddAsociada');

  function contarAsociadas() {
    return document.querySelectorAll('#tabla-materias .fila-asociada').length;
  }

  function actualizarBoton() {
    if (btnAdd) btnAdd.disabled = contarAsociadas() >= MAX_ASOCIADAS;
  }

  actualizarBoton();

  if (btnAdd) {
    btnAdd.addEventListener('click', function () {
      if (contarAsociadas() >= MAX_ASOCIADAS) return;
      var tbody = document.querySelector('#tabla-materias tbody');
      var tr = document.createElement('tr');
      tr.classList.add('fila-asociada');
      tr.innerHTML =
        '<td><input type="text" class="form-control form-control-sm" value="Asociadas" readonly></td>' +
        '<td><textarea name="asignacion_Asociadas[]" class="form-control form-control-sm" rows="2" maxlength="80"></textarea></td>' +
        '<td><textarea name="comentario_Asociadas[]" class="form-control form-control-sm" rows="2" maxlength="80"></textarea></td>';
      tbody.appendChild(tr);
      actualizarBoton();
    });
  }
});
