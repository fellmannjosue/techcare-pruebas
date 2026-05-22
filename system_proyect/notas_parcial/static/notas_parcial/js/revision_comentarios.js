/* notas_parcial/revision_comentarios.js
   Bridge vars injected via window._PAGE from revision_comentarios.html:
     csrf, urlComentario, urlEliminarComentario
*/
(function () {
  const CSRF             = window._PAGE.csrf;
  const URL_COMENTARIO   = window._PAGE.urlComentario;
  const URL_ELIMINAR     = window._PAGE.urlEliminarComentario;

  function toast(msg, ok = true) {
    const el = document.getElementById('toastRev');
    el.className = `toast align-items-center text-bg-${ok ? 'success' : 'danger'} border-0`;
    document.getElementById('toastRevMsg').textContent = msg;
    bootstrap.Toast.getOrCreateInstance(el).show();
  }

  // ── Editar ──────────────────────────────────────────────────────────────────
  document.querySelectorAll('.btn-editar').forEach(btn => {
    btn.addEventListener('click', function () {
      const id = this.dataset.id;
      document.getElementById('texto-' + id).classList.add('d-none');
      document.getElementById('editor-' + id).classList.remove('d-none');
      document.getElementById('acciones-' + id).classList.add('d-none');
      document.getElementById('acciones-edit-' + id).classList.remove('d-none');
    });
  });

  document.querySelectorAll('.btn-cancelar-edit').forEach(btn => {
    btn.addEventListener('click', function () {
      const id = this.dataset.id;
      const orig = document.getElementById('texto-' + id).textContent;
      document.getElementById('editor-' + id).value = orig;
      document.getElementById('editor-' + id).classList.add('d-none');
      document.getElementById('texto-' + id).classList.remove('d-none');
      document.getElementById('acciones-edit-' + id).classList.add('d-none');
      document.getElementById('acciones-' + id).classList.remove('d-none');
    });
  });

  document.querySelectorAll('.btn-guardar-edit').forEach(btn => {
    btn.addEventListener('click', async function () {
      const { id, iid, parcial, anio, area } = this.dataset;
      const nuevo = document.getElementById('editor-' + id).value.trim();
      const r = await fetch(URL_COMENTARIO, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({
          ingr_egr_id: parseInt(iid),
          parcial: parseInt(parcial),
          anio: parseInt(anio),
          area,
          comentario: nuevo,
        }),
      });
      const d = await r.json();
      if (d.ok) {
        document.getElementById('texto-' + id).textContent = nuevo;
        document.getElementById('editor-' + id).classList.add('d-none');
        document.getElementById('texto-' + id).classList.remove('d-none');
        document.getElementById('acciones-edit-' + id).classList.add('d-none');
        document.getElementById('acciones-' + id).classList.remove('d-none');
        toast('Comentario actualizado');
      } else {
        toast('Error: ' + d.error, false);
      }
    });
  });

  // ── Eliminar ─────────────────────────────────────────────────────────────────
  let idEliminar = null;
  document.querySelectorAll('.btn-eliminar').forEach(btn => {
    btn.addEventListener('click', function () {
      idEliminar = this.dataset.id;
      new bootstrap.Modal(document.getElementById('modalEliminar')).show();
    });
  });

  document.getElementById('btnConfirmarEliminar')?.addEventListener('click', async function () {
    if (!idEliminar) return;
    const r = await fetch(URL_ELIMINAR, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ id: parseInt(idEliminar) }),
    });
    const d = await r.json();
    bootstrap.Modal.getInstance(document.getElementById('modalEliminar')).hide();
    if (d.ok) {
      document.getElementById('row-com-' + idEliminar)?.remove();
      toast('Comentario eliminado');
    } else {
      toast('Error: ' + d.error, false);
    }
    idEliminar = null;
  });
})();
