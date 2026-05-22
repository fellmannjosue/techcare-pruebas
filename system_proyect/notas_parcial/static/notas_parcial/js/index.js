/* notas_parcial/index.js
   Bridge vars injected via window._PAGE from index.html:
     csrf, urlSave, anioActual
*/
(function () {
  const URL_SAVE = window._PAGE.urlSave;
  const CSRF     = window._PAGE.csrf;

  // Auto-submit on dropdown/year change (resets grade/section state)
  document.getElementById('selParcial')?.addEventListener('change', function () {
    const v = parseInt(this.value);
    if (v >= 3 || v === 1) return; // leave it to the modal
    document.getElementById('frmFiltro').submit();
  });
  document.getElementById('selArea')?.addEventListener('change', () =>
    document.getElementById('frmFiltro').submit()
  );
  document.getElementById('inpAnio')?.addEventListener('change', function () {
    if (parseInt(this.value) < window._PAGE.anioActual) return; // modal handles it
    document.getElementById('frmFiltro').submit();
  });

  async function guardar(tr) {
    const btn = tr.querySelector('.btn-guardar-uno');
    const msg = tr.querySelector('.estado-msg');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
      const res = await fetch(URL_SAVE, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ingr_egr_id: tr.dataset.iid,
          parcial:     tr.dataset.parcial,
          anio:        tr.dataset.anio,
          area:        tr.dataset.area,
          comentario:  tr.querySelector('.comentario-txt').value,
        }),
      });
      const d = await res.json();
      msg.className   = d.ok ? 'estado-msg saved-ok' : 'estado-msg saved-err';
      msg.textContent = d.ok ? '✓' : '✗';
      setTimeout(() => { msg.textContent = ''; }, 3000);
    } catch (e) {
      msg.className = 'estado-msg saved-err'; msg.textContent = '✗';
    }
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-check"></i>';
  }

  async function guardarTodo() {
    for (const tr of document.querySelectorAll('#lista-alumnos tr[data-iid]'))
      await guardar(tr);
  }

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.btn-guardar-uno').forEach(btn => {
      btn.addEventListener('click', () => guardar(btn.closest('tr')));
    });
    document.getElementById('btnGuardarTodo')?.addEventListener('click', guardarTodo);
    document.getElementById('btnGuardarTodo2')?.addEventListener('click', guardarTodo);
  });
})();
