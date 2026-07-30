/* permiso_comentario.js — <--- hecho por claude code: comentario GLOBAL por empleado.

   Uno por empleado y mes, no atado a un tipo de permiso. El botón de la columna
   "Comentario" abre el modal; al guardar se pinta el icono en azul con un punto
   para que se vea de un vistazo quién tiene nota. */
(function () {
  var P = window._PAGE || {};
  if (!P.urlSetComentario) return;

  var modalEl = document.getElementById('modalComentEmp');
  var txt     = document.getElementById('ce-texto');
  if (!modalEl || !txt) return;

  var modal = null;
  var btnActual = null;

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function msg(t, tipo) {
    var el = document.getElementById('ce-msg');
    el.innerHTML = t ? '<div class="alert alert-' + (tipo || 'danger') + ' py-2 mb-0">' + esc(t) + '</div>' : '';
  }
  function cuenta() {
    document.getElementById('ce-cuenta').textContent = txt.value.length;
  }

  // Abrir: el botón trae el empleado y el texto que ya tenga
  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.btn-coment-emp') : null;
    if (!btn) return;
    btnActual = btn;
    document.getElementById('ce-nombre').textContent = btn.dataset.nombre || btn.dataset.emp;
    document.getElementById('ce-mes').textContent    = P.mesActual || '';
    txt.value = btn.dataset.texto || '';
    cuenta();
    msg('');
    if (!modal) modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    modal.show();
    setTimeout(function () { txt.focus(); }, 300);
  });

  txt.addEventListener('input', cuenta);

  document.getElementById('ce-guardar').addEventListener('click', function () {
    if (!btnActual) return;
    var boton = this;
    var texto = txt.value.trim();

    boton.disabled = true;
    boton.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando…';

    var fd = new FormData();
    fd.append('emp_code',  btnActual.dataset.emp);
    fd.append('nombre',    btnActual.dataset.nombre || '');
    fd.append('mes',       P.mesActual || '');
    fd.append('comentario', texto);

    fetch(P.urlSetComentario, {
      method: 'POST', credentials: 'same-origin',
      headers: { 'X-CSRFToken': P.csrf || '' }, body: fd,
    })
      .then(function (r) {
        return r.text().then(function (t) {
          var d;
          try { d = JSON.parse(t); } catch (err) { throw new Error('El servidor respondió ' + r.status); }
          if (!r.ok || !d.ok) throw new Error(d.error || ('Error ' + r.status));
          return d;
        });
      })
      .then(function (d) {
        // Se refleja en el botón sin recargar
        btnActual.dataset.texto = d.comentario;
        btnActual.title = d.tiene ? d.comentario.slice(0, 120) : 'Agregar comentario';
        btnActual.innerHTML = '<i class="ti ti-message-2' + (d.tiene ? ' text-blue' : '') + '"></i>' +
          (d.tiene ? '<span class="badge bg-blue ms-1" style="width:7px;height:7px;padding:0;border-radius:50%;"></span>' : '');
        boton.disabled = false;
        boton.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
        modal.hide();
      })
      .catch(function (err) {
        boton.disabled = false;
        boton.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
        msg('No se pudo guardar: ' + err.message);
      });
  });
})();
