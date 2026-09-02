/* <--- hecho por claude code: gráficos del dashboard de Gestión de Desarrollo (FASE 4).
   Lee los datos de los <script type="application/json"> generados con json_script. */
(function () {
  'use strict';
  if (typeof Chart === 'undefined') { return; }

  function leer(id) {
    var el = document.getElementById(id);
    if (!el) { return null; }
    try { return JSON.parse(el.textContent); } catch (e) { return null; }
  }

  // Si no hay datos, muestra un aviso en el contenedor del canvas.
  function vacio(canvas) {
    var box = canvas.closest('.tc-chart-box') || canvas.parentNode;
    box.innerHTML = '<div class="text-muted small text-center py-4">Sin datos todavía.</div>';
  }

  function totalDatos(d) {
    return (d && d.data || []).reduce(function (a, b) { return a + b; }, 0);
  }

  var LEYENDA = { plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } } };

  function doughnut(id, srcId) {
    var canvas = document.getElementById(id);
    var d = leer(srcId);
    if (!canvas || !d) { return; }
    if (totalDatos(d) === 0) { vacio(canvas); return; }
    new Chart(canvas, {
      type: 'doughnut',
      data: { labels: d.labels, datasets: [{ data: d.data, backgroundColor: d.colors, borderWidth: 1 }] },
      options: Object.assign({ responsive: true, maintainAspectRatio: false, cutout: '58%' }, LEYENDA)
    });
  }

  function barras(id, srcId, horizontal) {
    var canvas = document.getElementById(id);
    var d = leer(srcId);
    if (!canvas || !d) { return; }
    if (totalDatos(d) === 0) { vacio(canvas); return; }
    new Chart(canvas, {
      type: 'bar',
      data: { labels: d.labels, datasets: [{ data: d.data, backgroundColor: d.colors, borderRadius: 4 }] },
      options: {
        indexAxis: horizontal ? 'y' : 'x',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { precision: 0 } }, y: { ticks: { precision: 0 } } }
      }
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    doughnut('chEstado', 'cd-estado');
    doughnut('chSemaforo', 'cd-semaforo');
    barras('chPrioridad', 'cd-prioridad', false);
    barras('chTipo', 'cd-tipo', true);
    barras('chArea', 'cd-area', true);
  });
})();
