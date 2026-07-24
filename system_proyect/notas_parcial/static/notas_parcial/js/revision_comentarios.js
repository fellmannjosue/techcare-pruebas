/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #revision_comentarios-config (un .js no lo procesa Django). */
const CFG_REVISION_COMENTARIOS = (function(){
  var d = document.getElementById("revision_comentarios-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
  };
})();

window._PAGE = Object.assign(window._PAGE || {}, {
  csrf:                CFG_REVISION_COMENTARIOS.v0,
  urlComentario:       CFG_REVISION_COMENTARIOS.v1,
  urlEliminarComentario:CFG_REVISION_COMENTARIOS.v2,
});


/* <--- hecho por claude code: lógica recuperada; se había perdido al extraer el JS
   del HTML (solo quedó el puente de configuración de arriba). */

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
