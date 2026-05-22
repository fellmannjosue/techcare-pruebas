/* notas_parcial/asignaciones.js
   Bridge vars injected via window._PAGE from the template:
     csrf, urlActualizarFecha, urlEliminarAsignacion, urlPrecargar
*/
(function () {
  const CSRF = window._PAGE.csrf;
  const URL_FECHA  = window._PAGE.urlActualizarFecha;
  const URL_ELIMINAR = window._PAGE.urlEliminarAsignacion;
  const URL_PRECARGAR = window._PAGE.urlPrecargar;

  function toast(msg, ok = true) {
    const el = document.getElementById('toastAsig');
    el.className = `toast align-items-center text-bg-${ok ? 'success' : 'danger'} border-0`;
    document.getElementById('toastAsigMsg').textContent = msg;
    bootstrap.Toast.getOrCreateInstance(el).show();
  }

  async function guardarFecha(id, valor) {
    const r = await fetch(URL_FECHA, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
      body: JSON.stringify({ id, fecha_limite: valor }),
    });
    const d = await r.json();
    if (d.ok) {
      toast(valor ? 'Fecha límite guardada' : 'Fecha límite eliminada');
      if (!valor) {
        const fila = document.getElementById('fila-' + id);
        if (fila) fila.querySelector('.inp-fecha').value = '';
      }
    } else {
      toast('Error: ' + d.error, false);
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    // Guardar fecha límite
    document.querySelectorAll('.btn-guardar-fecha').forEach(btn => {
      btn.addEventListener('click', function () {
        const id  = this.dataset.id;
        const inp = document.querySelector(`.inp-fecha[data-id="${id}"]`);
        guardarFecha(id, inp.value);
      });
    });

    // Eliminar asignación
    let idEliminarAsig = null;
    document.querySelectorAll('.btn-eliminar-asig').forEach(btn => {
      btn.addEventListener('click', function () {
        idEliminarAsig = this.dataset.id;
        const nombre  = this.dataset.nombre;
        const grado   = this.dataset.grado;
        const seccion = this.dataset.seccion;
        document.getElementById('modalAsigTexto').textContent =
          `¿Quitar la asignación de ${nombre} en ${grado}${seccion ? ' / ' + seccion : ''}?`;
        new bootstrap.Modal(document.getElementById('modalEliminarAsig')).show();
      });
    });

    document.getElementById('btnConfirmarEliminarAsig').addEventListener('click', async function () {
      if (!idEliminarAsig) return;
      const r = await fetch(URL_ELIMINAR, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({ id: parseInt(idEliminarAsig) }),
      });
      const d = await r.json();
      bootstrap.Modal.getInstance(document.getElementById('modalEliminarAsig')).hide();
      if (d.ok) {
        document.getElementById('fila-' + idEliminarAsig)?.remove();
        toast('Asignación eliminada');
      } else {
        toast('Error: ' + d.error, false);
      }
      idEliminarAsig = null;
    });

    // Pre-cargar cache
    document.querySelectorAll('.btn-precargar').forEach(btn => {
      btn.addEventListener('click', async function () {
        const orig = this.innerHTML;
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        const { area, parcial, anio } = this.dataset;
        const r = await fetch(`${URL_PRECARGAR}?area=${area}&parcial=${parcial}&anio=${anio}`);
        const d = await r.json();
        if (d.ok) {
          this.closest('.d-flex').innerHTML =
            '<span class="badge bg-success-lt"><i class="ti ti-database me-1"></i>Cache activo</span>';
          toast('Cache pre-cargado correctamente');
        } else {
          this.disabled = false;
          this.innerHTML = orig;
          toast('Error al pre-cargar cache', false);
        }
      });
    });
  });
})();
