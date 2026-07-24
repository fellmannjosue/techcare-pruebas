/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #grafica-config (un .js no lo procesa Django). */
const CFG_GRAFICA = (function(){
  var d = document.getElementById("grafica-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
    v4: d.v4,
    j4: j(d.v4),
  };
})();

window.GRAFICA_CONTEXT = {
  presentes: CFG_GRAFICA.j3,
  ausentes:  CFG_GRAFICA.j4,
  fecha_inicio: CFG_GRAFICA.v0,
  fecha_fin:    CFG_GRAFICA.v1,
  detalleURL:   CFG_GRAFICA.v2
};


/* <--- hecho por claude code: lógica recuperada; se había perdido al extraer el JS
   del HTML (solo quedó el puente de configuración de arriba). */

(function () {
  // ==== Config esperada desde el template ====
  // window.GRAFICA_CONTEXT = {
  //   presentes: 0,
  //   ausentes: 0,
  //   fecha_inicio: "YYYY-MM-DD",
  //   fecha_fin: "YYYY-MM-DD",
  //   detalleURL: "/reloj/grafica/detalle/"
  // };
  const CFG = (window.GRAFICA_CONTEXT || {});
  const presentes = Number(CFG.presentes || 0);
  const ausentes  = Number(CFG.ausentes  || 0);
  const fechaInicio = CFG.fecha_inicio || "";
  const fechaFin    = CFG.fecha_fin    || "";
  const detalleURL  = CFG.detalleURL   || "";

  // ==== Helpers ====
  function ensureModal() {
    let modal = document.getElementById('modalDetalle');
    if (modal) return modal;

    const tpl = `
      <div class="modal fade" id="modalDetalle" tabindex="-1" aria-labelledby="modalDetalleLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg modal-dialog-scrollable">
          <div class="modal-content">
            <div class="modal-header">
              <h5 id="modalDetalleLabel" class="modal-title">Detalle</h5>
              <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
            </div>
            <div class="modal-body">
              <div class="table-responsive">
                <table class="table table-sm table-striped align-middle mb-0">
                  <thead class="table-light">
                    <tr>
                      <th>ID</th>
                      <th>Empleado</th>
                      <th>Fecha</th>
                      <th>Marcas</th>
                    </tr>
                  </thead>
                  <tbody id="detalleBody"></tbody>
                </table>
              </div>
            </div>
            <div class="modal-footer">
              <small class="text-muted me-auto">Rango: ${fechaInicio} → ${fechaFin}</small>
              <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button>
            </div>
          </div>
        </div>
      </div>`;
    const wrapper = document.createElement('div');
    wrapper.innerHTML = tpl;
    document.body.appendChild(wrapper.firstElementChild);
    return document.getElementById('modalDetalle');
  }

  async function cargarDetalle(estado) {
    if (!detalleURL) return;
    const url = new URL(detalleURL, window.location.origin);
    url.searchParams.set('estado', estado);
    url.searchParams.set('fecha_inicio', fechaInicio);
    url.searchParams.set('fecha_fin', fechaFin);

    try {
      const res = await fetch(url.toString(), { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
      const data = await res.json();

      const modal = ensureModal();
      const tbody = modal.querySelector('#detalleBody');
      const title = modal.querySelector('#modalDetalleLabel');

      tbody.innerHTML = '';
      title.textContent = (estado === 'PRESENTE') ? 'Presentes' : 'Ausentes';

      if (data.success && Array.isArray(data.rows) && data.rows.length) {
        for (const r of data.rows) {
          const tr = document.createElement('tr');
          tr.innerHTML = `
            <td>${r.emp_code}</td>
            <td>${r.empleado}</td>
            <td>${r.fecha}</td>
            <td>${r.marcas || '—'}</td>
          `;
          tbody.appendChild(tr);
        }
      } else {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td colspan="4" class="text-center text-muted">Sin registros.</td>`;
        tbody.appendChild(tr);
      }

      const bsModal = new bootstrap.Modal(modal);
      bsModal.show();
    } catch (err) {
      console.error('Error cargando detalle:', err);
    }
  }

  // ==== Gráfico ====
  const canvas = document.getElementById('pieAsistencia');
  if (!canvas || typeof Chart === 'undefined') return;

  const chart = new Chart(canvas, {
    type: 'pie',
    data: {
      labels: ['Presentes', 'Ausentes'],
      datasets: [{
        data: [presentes, ausentes],
        backgroundColor: ['#22c55e', '#ef4444'],
        borderColor: '#ffffff',
        borderWidth: 2
      }]
    },
    options: {
      onClick: async (evt, elements) => {
        if (!elements.length) return;
        const idx = elements[0].index;
        const label = chart.data.labels[idx]; // 'Presentes' | 'Ausentes'
        const estado = (label === 'Presentes') ? 'PRESENTE' : 'AUSENTE';
        await cargarDetalle(estado);
      },
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          callbacks: {
            label: function (ctx) {
              const total = presentes + ausentes || 1;
              const val = ctx.parsed || 0;
              const pct = (val * 100 / total).toFixed(1);
              return `${ctx.label}: ${val} (${pct}%)`;
            }
          }
        },
        title: {
          display: true,
          text: `Asistencias vs Ausencias | ${fechaInicio} → ${fechaFin}`
        }
      }
    }
  });
})();
