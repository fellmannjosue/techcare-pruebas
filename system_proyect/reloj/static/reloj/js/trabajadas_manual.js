/* <--- hecho por claude code (11-nov-2026): ventana «Horas trabajadas» manuales (tab 2 · Control de deudas
   compensatorio). Solo aparece en los empleados de reloj.views._TRABAJADAS_MANUAL_EMP (Santos). Al cerrar, si hubo
   cambios, recarga la página para que toda la fila se recalcule. */
(function () {
  'use strict';
  var cfg = document.getElementById('trab-cfg');
  var modalEl = document.getElementById('modalTrabajadas');
  if (!cfg || !modalEl) return;
  var C = cfg.dataset, puede = C.puede === '1';
  var pk = null, editando = null, cambio = false, modal = null;
  var $ = function (id) { return document.getElementById(id); };
  function url(tpl, id) { return tpl.replace(/\/0\//, '/' + id + '/'); }
  function esc(t) { var d = document.createElement('div'); d.textContent = t == null ? '' : String(t); return d.innerHTML; }
  function error(msg) { var e = $('trab-error'); e.textContent = msg || ''; e.classList.toggle('d-none', !msg); }
  function limpiar() { $('trab-fecha').value = ''; $('trab-horas').value = ''; $('trab-razon').value = ''; editando = null; $('trab-guardar').querySelector('span').textContent = 'Agregar'; error(''); }
  function pintar(d) {
    var tb = $('trab-tbody');
    $('trab-total').textContent = d.total;
    if (!d.filas.length) { tb.innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">Sin horas registradas.</td></tr>'; return; }
    tb.innerHTML = d.filas.map(function (f) {
      return '<tr><td class="font-monospace small">' + esc(f.fecha) + '</td><td class="text-center fw-bold text-green">' + esc(f.horas) + ' h</td><td class="small">' + (esc(f.razon) || '—') +
        '</td><td class="small text-muted">' + (esc(f.por) || '—') + '</td><td class="text-end">' +
        (puede ? '<button type="button" class="btn btn-sm btn-ghost-primary px-1 trab-edit" data-pk="' + f.pk + '" data-fecha="' + esc(f.fecha_iso) + '" data-horas="' + f.horas + '" data-razon="' + esc(f.razon) + '"><i class="ti ti-pencil"></i></button>' +
         '<button type="button" class="btn btn-sm btn-ghost-danger px-1 trab-del" data-pk="' + f.pk + '"><i class="ti ti-trash"></i></button>' : '') + '</td></tr>';
    }).join('');
  }
  function pedir(u, cuerpo) {
    var op = cuerpo ? { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': C.csrf }, body: JSON.stringify(cuerpo) } : {};
    return fetch(u, op).then(function (r) { return r.json(); }).then(function (d) {
      if (!d.ok) { error(d.error || 'Error'); return; }
      if (cuerpo) cambio = true;
      pintar(d);
      return d;
    }).catch(function () { error('No se pudo conectar.'); });
  }
  document.addEventListener('click', function (ev) {
    var b = ev.target.closest('.btn-trab-manual');
    if (b) {
      pk = b.dataset.pk; $('trab-nombre').textContent = b.dataset.nombre || '';
      $('trab-form').classList.toggle('d-none', !puede); limpiar();
      $('trab-tbody').innerHTML = '<tr><td colspan="5" class="text-center text-muted py-3">Cargando…</td></tr>';
      modal = modal || new bootstrap.Modal(modalEl); modal.show();
      pedir(url(C.list, pk)); return;
    }
    var ed = ev.target.closest('.trab-edit');
    if (ed) {
      editando = ed.dataset.pk; $('trab-fecha').value = ed.dataset.fecha; $('trab-horas').value = ed.dataset.horas; $('trab-razon').value = ed.dataset.razon;
      $('trab-guardar').querySelector('span').textContent = 'Guardar cambios'; return;
    }
    var del = ev.target.closest('.trab-del');
    if (del) {
      if (del.dataset.confirmar !== '1') { del.dataset.confirmar = '1'; del.innerHTML = '<span class="small">¿Borrar?</span>'; return; }
      pedir(url(C.del, del.dataset.pk), {});
    }
  });
  $('trab-guardar').addEventListener('click', function () {
    error('');
    var datos = { fecha: $('trab-fecha').value, horas: $('trab-horas').value, razon: $('trab-razon').value };
    if (!datos.fecha || !(parseFloat(datos.horas) > 0)) { error('Escribe la fecha y las horas (mayor que 0).'); return; }
    var u = editando ? url(C.edit, editando) : url(C.add, pk);
    pedir(u, datos).then(function (d) { if (d) limpiar(); });
  });
  modalEl.addEventListener('hidden.bs.modal', function () { if (cambio) location.reload(); });
})();
