/* <--- hecho por claude code (seguridad): panel de Seguridad — interruptores y lista blanca. */
(function () {
  var C = document.getElementById('seg-config');
  if (!C) return;
  var d = C.dataset;

  function post(url, datos) {
    var fd = new FormData();
    Object.keys(datos).forEach(function (k) { fd.append(k, datos[k]); });
    return fetch(url, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'X-CSRFToken': d.csrf }, body: fd
    }).then(function (r) { return r.json(); });
  }
  function msg(el, texto, ok) {
    el.className = 'small mt-2 ' + (ok ? 'text-green' : 'text-danger');
    el.textContent = texto;
    if (ok) setTimeout(function () { el.textContent = ''; }, 2500);
  }

  // ── Interruptores ──
  var estado = document.getElementById('sw-estado');
  document.querySelectorAll('.sw-toggle').forEach(function (sw) {
    sw.addEventListener('change', function () {
      var valor = sw.checked;
      post(d.toggle, { clave: sw.dataset.clave, valor: valor })
        .then(function (r) {
          if (!r.ok) { sw.checked = !valor; msg(estado, r.error || 'No se pudo cambiar', false); return; }
          var nombre = sw.dataset.clave === 'DOSFA_ACTIVO' ? '2FA' : 'Crear usuarios';
          msg(estado, nombre + (valor ? ' activado' : ' desactivado'), true);
        })
        .catch(function () { sw.checked = !valor; msg(estado, 'Sin conexión', false); });
    });
  });

  // ── Agregar correo ──
  var frm = document.getElementById('frm-add');
  var addMsg = document.getElementById('add-msg');
  frm.addEventListener('submit', function (e) {
    e.preventDefault();
    var correo = document.getElementById('add-correo').value.trim().toLowerCase();
    var nombre = document.getElementById('add-nombre').value.trim();
    post(d.add, { correo: correo, nombre: nombre })
      .then(function (r) {
        if (!r.ok) { msg(addMsg, r.error || 'No se pudo agregar', false); return; }
        agregarFila(r);
        frm.reset();
        msg(addMsg, 'Correo agregado', true);
      })
      .catch(function () { msg(addMsg, 'Sin conexión', false); });
  });

  function agregarFila(r) {
    var tb = document.getElementById('tabla-correos');
    var vacia = tb.querySelector('td[colspan]');
    if (vacia) tb.innerHTML = '';
    var tr = document.createElement('tr');
    tr.dataset.id = r.id;
    tr.innerHTML =
      '<td class="font-monospace">' + r.correo + '</td>' +
      '<td>' + (r.nombre || '—') + '</td>' +
      '<td class="text-center"><span class="badge bg-green-lt text-green c-estado">Habilitado</span></td>' +
      '<td class="text-center"><span class="text-muted small">disponible</span></td>' +
      '<td class="text-end">' +
        '<button class="btn btn-sm btn-ghost-secondary c-toggle" title="Habilitar/Deshabilitar"><i class="ti ti-power"></i></button>' +
        '<button class="btn btn-sm btn-ghost-danger c-del" title="Quitar de la lista"><i class="ti ti-trash"></i></button>' +
      '</td>';
    tb.appendChild(tr);
  }

  // ── Habilitar/Deshabilitar y Quitar (delegado) ──
  document.getElementById('tabla-correos').addEventListener('click', function (e) {
    var tr = e.target.closest('tr');
    if (!tr) return;
    var id = tr.dataset.id;

    if (e.target.closest('.c-toggle')) {
      post(d.ctoggle, { id: id }).then(function (r) {
        if (!r.ok) return;
        var b = tr.querySelector('.c-estado');
        if (r.activo) { b.className = 'badge bg-green-lt text-green c-estado'; b.textContent = 'Habilitado'; }
        else { b.className = 'badge bg-secondary-lt text-secondary c-estado'; b.textContent = 'Deshabilitado'; }
      });
    } else if (e.target.closest('.c-del')) {
      if (!confirm('¿Quitar este correo de la lista de permitidos?')) return;
      post(d.cdel, { id: id }).then(function (r) { if (r.ok) tr.remove(); });
    }
  });
})();

// <--- hecho por claude code: subir la lista (CSV/JSON/XLSX)
(function () {
  var C = document.getElementById('seg-config');
  if (!C) return;
  var d = C.dataset;
  var btn = document.getElementById('imp-subir');
  if (!btn) return;
  var msg = document.getElementById('imp-msg');

  btn.addEventListener('click', function () {
    var f = document.getElementById('imp-archivo').files[0];
    if (!f) { msg.textContent = 'Elige un archivo primero.'; msg.style.color = '#c2410c'; return; }
    var reemplazar = document.getElementById('imp-reemplazar').checked;
    if (reemplazar && !confirm('Modo "Reemplazar": los correos que NO estén en el archivo se ELIMINARÁN de la lista. ¿Continuar?')) return;

    var fd = new FormData();
    fd.append('archivo', f);
    fd.append('reemplazar', reemplazar ? 'true' : 'false');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Subiendo…';

    fetch(d.import, { method: 'POST', credentials: 'same-origin',
                     headers: { 'X-CSRFToken': d.csrf }, body: fd })
      .then(function (r) { return r.json(); })
      .then(function (r) {
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-upload me-1"></i>Subir';
        if (!r.ok) { msg.textContent = r.error || 'No se pudo subir'; msg.style.color = '#dc2626'; return; }
        msg.style.color = '#15803d';
        msg.textContent = 'Listo: ' + r.creados + ' agregados, ' + r.actualizados + ' actualizados' +
                          (r.eliminados ? ', ' + r.eliminados + ' eliminados' : '') + '. Recargando…';
        setTimeout(function () { location.reload(); }, 1200);
      })
      .catch(function () {
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-upload me-1"></i>Subir';
        msg.textContent = 'Sin conexión'; msg.style.color = '#dc2626';
      });
  });
})();
