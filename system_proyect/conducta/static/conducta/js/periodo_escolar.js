/* <--- hecho por claude code (06-nov-2026): Período Escolar general — confirmación de borrado en ventana propia */
(function () {
  var modalEl = document.getElementById('peModalBorrar'); if (!modalEl) return;
  var form = document.getElementById('pe-form-borrar'), nom = document.getElementById('pe-borrar-nombre');
  document.addEventListener('click', function (e) {
    var b = e.target.closest('.js-pe-borrar'); if (!b) return;
    form.setAttribute('action', b.dataset.url); nom.textContent = b.dataset.nombre;
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
  });
})();

/* <--- hecho por claude code (06-nov-2026): los interruptores de módulos cambian según el área elegida */
(function () {
  var sel = document.getElementById('pe-area'); if (!sel) return;
  function aplicar() {
    var a = sel.value;
    document.querySelectorAll('.pe-mod[data-areas]').forEach(function (m) {
      var areas = m.dataset.areas.split(' ');
      m.hidden = !(a === 'ambas' ? true : areas.indexOf(a) > -1);
    });
  }
  sel.addEventListener('change', aplicar); aplicar();
})();
