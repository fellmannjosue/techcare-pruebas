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
