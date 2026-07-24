/* ================================================================
   DASHBOARD SUMMARY (TechCare)
   Carga automática de conteos para el Panel Principal.
   ================================================================ */

// ===============================
// 1. ENDPOINTS DEL BACKEND
// ===============================
const URL_TICKETS  = "/core/api/summary/tickets/";
const URL_COORD_BL = "/core/api/summary/coordinacion_bl/";
const URL_COORD_COL = "/core/api/summary/coordinacion_col/";

// ===============================
// 2. ELEMENTOS HTML A ACTUALIZAR
// ===============================
const cardTickets  = document.getElementById("card-tickets-total");
const cardCoordBL  = document.getElementById("card-coord-bl-total");
const cardCoordCOL = document.getElementById("card-coord-col-total");

let resumenDatos = {
    tickets:  [],
    coord_bl: [],
    coord_col: [],
};

// ===============================
// 3. FUNCIÓN GENÉRICA PARA FETCH
// ===============================
async function cargarResumen(url) {
    try {
        const resp = await fetch(url);
        if (!resp.ok) return { total: 0, items: [] };
        return await resp.json();
    } catch (err) {
        return { total: 0, items: [] };
    }
}

// ===============================
// 4. CARGAR TODOS LOS MÓDULOS
// ===============================
async function actualizarDashboard() {
    const t = await cargarResumen(URL_TICKETS);
    if (cardTickets) cardTickets.innerText = t.total ?? 0;
    resumenDatos.tickets = t.items;

    const cb = await cargarResumen(URL_COORD_BL);
    if (cardCoordBL) cardCoordBL.innerText = cb.total ?? 0;
    resumenDatos.coord_bl = cb.items;

    const cc = await cargarResumen(URL_COORD_COL);
    if (cardCoordCOL) cardCoordCOL.innerText = cc.total ?? 0;
    resumenDatos.coord_col = cc.items;
}

// ===============================
// 5. AUTO-ACTUALIZACIÓN CADA 60s
// ===============================
document.addEventListener("DOMContentLoaded", actualizarDashboard);
setInterval(actualizarDashboard, 60000);


// <--- hecho por claude code: al extraer el JS del HTML se perdió abrirModalResumen,
// así que las tarjetas resumen (onclick="abrirModalResumen(...)") no hacían nada.
// Reescrito con un modal Bootstrap creado al vuelo (Tabler ya trae Bootstrap; antes
// dependía de SweetAlert, que no se carga en esta página).
window.abrirModalResumen = function (modulo) {
  const datos = (typeof resumenDatos !== 'undefined' && resumenDatos[modulo]) || [];
  let cuerpo;
  if (!datos.length) {
    cuerpo = "<p class='text-center text-muted mb-0 py-3'>No hay elementos recientes.</p>";
  } else {
    const filas = datos.map(i => `
      <tr>
        <td>${i.titulo ?? ''}</td>
        <td>${i.descripcion ?? ''}</td>
        <td class="text-nowrap">${i.fecha ?? ''}</td>
      </tr>`).join("");
    cuerpo = `<div class="table-responsive"><table class="table table-sm table-striped mb-0">
        <thead><tr><th>Título</th><th>Descripción</th><th>Fecha</th></tr></thead>
        <tbody>${filas}</tbody></table></div>`;
  }
  let el = document.getElementById('modalResumenDin');
  if (!el) {
    el = document.createElement('div');
    el.id = 'modalResumenDin';
    el.className = 'modal modal-blur fade';
    el.tabIndex = -1;
    el.innerHTML = `<div class="modal-dialog modal-lg modal-dialog-centered"><div class="modal-content">
        <div class="modal-header"><h5 class="modal-title">Resumen del módulo</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button></div>
        <div class="modal-body" id="modalResumenDinBody"></div>
        <div class="modal-footer"><button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cerrar</button></div>
      </div></div>`;
    document.body.appendChild(el);
  }
  document.getElementById('modalResumenDinBody').innerHTML = cuerpo;
  if (window.bootstrap && bootstrap.Modal) bootstrap.Modal.getOrCreateInstance(el).show();
};
