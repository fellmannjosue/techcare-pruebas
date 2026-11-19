/* <--- hecho por claude code (19-nov-2026): por empleado, copia SU fila de cada control de Pruebas (1 · Días a compensar,
   2 · Control de deudas, 3 · Control 3 días) a sus sub-pestañas. Se carga ANTES de los JS de la página para que los
   lápices y las ventanas de las filas copiadas queden enlazados igual que en las tablas originales. */
(function () {
  document.querySelectorAll('.hc-ind').forEach(function (cont) {
    var src = document.getElementById(cont.dataset.src);
    var tabla = src && src.querySelector('table');
    var fila = tabla && tabla.querySelector('tbody tr[data-emp="' + cont.dataset.emp + '"]');
    if (!fila) {
      cont.innerHTML = '<div class="alert alert-secondary py-2 small mb-0"><i class="ti ti-info-circle me-1"></i>No aparece en este control.</div>';
      return;
    }
    var nueva = tabla.cloneNode(false);
    var thead = tabla.querySelector('thead');
    if (thead) nueva.appendChild(thead.cloneNode(true));
    var tbody = document.createElement('tbody');
    var copia = fila.cloneNode(true);
    copia.querySelectorAll('[id]').forEach(function (el) { el.removeAttribute('id'); });
    tbody.appendChild(copia);
    nueva.appendChild(tbody);
    var card = document.createElement('div');
    card.className = 'card';
    var resp = document.createElement('div');
    resp.className = 'table-responsive';
    resp.appendChild(nueva);
    card.appendChild(resp);
    cont.appendChild(card);
  });
})();
