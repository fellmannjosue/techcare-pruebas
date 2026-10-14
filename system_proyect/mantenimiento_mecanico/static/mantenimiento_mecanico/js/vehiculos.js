/* vehiculos.js — <--- hecho por claude code (12-oct-2026): detalle de un vehículo (formato de Access sobre Test2).
   Marca las tareas que tocan, cuenta las hechas, calcula el próximo mantenimiento y abre los comentarios.
   Se carga en extra_js (después de Bootstrap); los modales se piden al hacer clic. Un solo global: MV_VEH. */
(function () {
  'use strict';
  function isla(id) { try { return JSON.parse(document.getElementById(id).textContent) || {}; } catch (e) { return {}; } }
  function abrirModal(el) {
    if (!el) return;
    if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(el).show();
    else if (window.jQuery && jQuery.fn.modal) jQuery(el).modal('show');
  }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function miles(n) { return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, '.'); }

  var checks = Array.prototype.slice.call(document.querySelectorAll('.mv-hecho'));
  var nEl = document.getElementById('mv-n-hechas');
  function contar() {
    if (nEl) nEl.textContent = checks.filter(function (c) { return c.checked; }).length;
    checks.forEach(function (c) { c.closest('tr').classList.toggle('mv-hecha', c.checked); });
  }
  checks.forEach(function (c) { c.addEventListener('change', contar); });
  var bT = document.getElementById('mv-marcar-toca');
  if (bT) bT.addEventListener('click', function () { checks.forEach(function (c) { if (c.dataset.toca === '1') c.checked = true; }); contar(); });
  var bD = document.getElementById('mv-desmarcar');
  if (bD) bD.addEventListener('click', function () { checks.forEach(function (c) { c.checked = false; }); contar(); });
  contar();

  // Próximo = km/horas del mantenimiento + intervalo del vehículo
  var val = document.getElementById('mv-valor'), prox = document.getElementById('mv-prox');
  function calc() {
    if (!val || !prox) return;
    var n = parseInt(val.value, 10), i = parseInt(val.dataset.intervalo, 10);
    prox.textContent = (isNaN(n) || isNaN(i) || !i) ? '—' : miles(n + i);
  }
  if (val) { val.addEventListener('input', calc); calc(); }

  // Confirmación antes de guardar (se escribe en el sistema de Access)
  var form = document.getElementById('mv-form-mant');
  if (form) form.addEventListener('submit', function (e) {
    if (form.dataset.ok === '1') return;
    var n = checks.filter(function (c) { return c.checked; }).length;
    if (!n) { e.preventDefault(); alert('Marca al menos una tarea como hecha.'); return; }
    if (window.Swal) {
      e.preventDefault();
      Swal.fire({ title: 'Registrar mantenimiento', icon: 'question',
        html: n + ' de ' + checks.length + ' tareas marcadas como hechas.<br><small class="text-muted">Se guarda en el sistema de mantenimiento (Access / Test2).</small>',
        showCancelButton: true, confirmButtonText: 'Sí, registrar', cancelButtonText: 'Revisar' })
        .then(function (r) { if (r.isConfirmed) { form.dataset.ok = '1'; form.submit(); } });
    }
  });

  // Comentarios de auditoría por mantenimiento
  var COM = isla('mv-comentarios'), fc = document.getElementById('mv-form-com');
  document.querySelectorAll('.mv-coment').forEach(function (b) {
    b.addEventListener('click', function () {
      var lista = COM[b.dataset.id] || [];
      document.getElementById('mv-com-fecha').textContent = b.dataset.fecha || '';
      document.getElementById('mv-com-lista').innerHTML = lista.length
        ? lista.map(function (c) { return '<div class="mm-com"><div class="mm-com-meta">' + esc(c.autor) + ' · ' + esc(c.fecha) + '</div><div class="mm-com-txt">' + esc(c.texto) + '</div></div>'; }).join('')
        : '<div class="text-muted small">Sin comentarios todavía.</div>';
      fc.setAttribute('action', b.dataset.url);
      fc.elements.namedItem('texto').value = '';
      abrirModal(document.getElementById('mvModalComentarios'));
    });
  });
  window.MV_VEH = { contar: contar };
})();
