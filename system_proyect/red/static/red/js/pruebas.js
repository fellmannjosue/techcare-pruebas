/* <--- hecho por claude code: Fase 4 — pruebas de conectividad (ping por fila) */
(function () {
  var cfg = document.getElementById('pruebas-cfg'); if (!cfg) return;
  var CSRF = cfg.dataset.csrf;

  function badge(e) {
    if (e === 'ok') return '<span class="badge bg-green-lt text-green"><i class="ti ti-circle-filled me-1"></i>En línea</span>';
    if (e === 'caido') return '<span class="badge bg-red-lt text-red"><i class="ti ti-circle-filled me-1"></i>Caído</span>';
    return '<span class="badge bg-secondary-lt text-secondary">Sin probar</span>';
  }

  function probar(row) {
    var url = row.dataset.url;
    var est = row.querySelector('.estado'), lat = row.querySelector('.lat'), prob = row.querySelector('.prob');
    est.innerHTML = '<span class="badge bg-blue-lt text-blue"><span class="spinner-border spinner-border-sm me-1" style="width:.7rem;height:.7rem"></span>Probando…</span>';
    return fetch(url, { method: 'POST', headers: { 'X-CSRFToken': CSRF } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) { est.innerHTML = badge('desconocido'); return; }
        est.innerHTML = badge(d.estado);
        lat.textContent = (d.latencia != null ? d.latencia + ' ms' : '—');
        prob.textContent = d.probado || '';
      })
      .catch(function () { est.innerHTML = badge('desconocido'); });
  }

  document.querySelectorAll('.probar').forEach(function (b) {
    b.addEventListener('click', function () { probar(b.closest('.ping-row')); });
  });

  var todos = document.getElementById('probar-todos');
  if (todos) todos.addEventListener('click', function () {
    todos.disabled = true;
    var rows = Array.prototype.slice.call(document.querySelectorAll('.ping-row'));
    var i = 0;
    (function next() {
      if (i >= rows.length) { todos.disabled = false; return; }
      probar(rows[i++]).then(next);   // secuencial, para no saturar
    })();
  });
})();
