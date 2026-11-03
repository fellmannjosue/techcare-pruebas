/* <--- hecho por claude code (03-nov-2026): Progress Report · aviso al topar los 20 caracteres de "Asignación".
   Cuando el maestro llena el campo (llega al límite), aparece debajo:
   "Si desea escribir más, póngalo en comentarios." Vale para crear y editar, filas fijas y dinámicas. */
(function () {
  var LIMITE = 20;
  var MSG = 'Si desea escribir más, póngalo en comentarios.';

  function esAsignacion(el) {
    return el && el.tagName === 'TEXTAREA' && el.name && el.name.indexOf('asignacion_') === 0;
  }
  function avisoDe(ta) {
    var sig = ta.nextElementSibling;
    if (!sig || !sig.classList || !sig.classList.contains('tc-asig-aviso')) {
      sig = document.createElement('div');
      sig.className = 'tc-asig-aviso text-danger small mt-1';
      sig.style.display = 'none';
      sig.innerHTML = '<i class="ti ti-alert-triangle me-1"></i>' + MSG;
      ta.insertAdjacentElement('afterend', sig);
    }
    return sig;
  }
  function revisar(ta) {
    if (!esAsignacion(ta)) return;
    avisoDe(ta).style.display = (ta.value.length >= LIMITE) ? '' : 'none';
  }
  // delegación: cubre filas que llegan después (materias por grado, Asociadas +)
  document.addEventListener('input', function (e) { revisar(e.target); });
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('textarea[name^="asignacion_"]').forEach(revisar);
  });
})();
