/* <--- hecho por claude code: drag & drop del roadmap Kanban (FASE 5). */
(function () {
  'use strict';
  var board = document.getElementById('kanBoard');
  if (!board) { return; }
  var puedeMover = board.getAttribute('data-puede-mover') === '1';
  var moverBase = board.getAttribute('data-mover-base'); // .../requerimientos/CODIGO/mover/
  var csrfEl = document.querySelector('input[name=csrfmiddlewaretoken]');
  var csrf = csrfEl ? csrfEl.value : '';

  // Navegación al detalle con clic (si no se arrastró).
  board.addEventListener('click', function (e) {
    var card = e.target.closest('.tc-kan-card');
    if (card && !card.classList.contains('tc-dragging')) {
      window.location.href = card.getAttribute('data-url');
    }
  });

  if (!puedeMover) { return; }

  var arrastrada = null;

  board.addEventListener('dragstart', function (e) {
    var card = e.target.closest('.tc-kan-card');
    if (!card) { return; }
    arrastrada = card;
    card.classList.add('tc-dragging');
    e.dataTransfer.effectAllowed = 'move';
    try { e.dataTransfer.setData('text/plain', card.getAttribute('data-codigo')); } catch (err) {}
  });

  board.addEventListener('dragend', function () {
    if (arrastrada) { arrastrada.classList.remove('tc-dragging'); }
    arrastrada = null;
    var cols = board.querySelectorAll('.tc-kan-col');
    for (var i = 0; i < cols.length; i++) { cols[i].classList.remove('tc-kan-over'); }
  });

  board.addEventListener('dragover', function (e) {
    var col = e.target.closest('.tc-kan-col');
    if (col && arrastrada) { e.preventDefault(); col.classList.add('tc-kan-over'); }
  });

  board.addEventListener('dragleave', function (e) {
    var col = e.target.closest('.tc-kan-col');
    if (col && !col.contains(e.relatedTarget)) { col.classList.remove('tc-kan-over'); }
  });

  board.addEventListener('drop', function (e) {
    var col = e.target.closest('.tc-kan-col');
    if (!col || !arrastrada) { return; }
    e.preventDefault();
    col.classList.remove('tc-kan-over');
    var origen = arrastrada.parentNode;
    var nuevoEstado = col.getAttribute('data-estado');
    var codigo = arrastrada.getAttribute('data-codigo');
    if (origen === col.querySelector('.tc-kan-body')) { return; } // misma columna

    var body = col.querySelector('.tc-kan-body');
    body.appendChild(arrastrada); // movimiento optimista
    actualizarConteos();

    var url = moverBase.replace('CODIGO', encodeURIComponent(codigo));
    fetch(url, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrf, 'X-Requested-With': 'XMLHttpRequest',
                 'Content-Type': 'application/x-www-form-urlencoded' },
      body: 'estado=' + encodeURIComponent(nuevoEstado)
    }).then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (!res.ok || !res.j.ok) {
          origen.appendChild(arrastrada); // revertir
          actualizarConteos();
          alert((res.j && res.j.error) || 'No se pudo mover el requerimiento.');
        }
      }).catch(function () {
        origen.appendChild(arrastrada); // revertir en error de red
        actualizarConteos();
        alert('Error de red al mover el requerimiento.');
      });
  });

  function actualizarConteos() {
    var cols = board.querySelectorAll('.tc-kan-col');
    for (var i = 0; i < cols.length; i++) {
      var n = cols[i].querySelectorAll('.tc-kan-card').length;
      var c = cols[i].querySelector('.tc-kan-count');
      if (c) { c.textContent = n; }
    }
  }
})();
