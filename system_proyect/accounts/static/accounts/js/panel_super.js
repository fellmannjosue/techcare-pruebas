/* <--- hecho por claude code: Panel Principal del superusuario — gráficas de actividad (Chart.js,
   datos reales por data-*) y pestañas de filtro de la cuadrícula de módulos (Horizon, 30-sep-2026). */
(function () {
  'use strict';

  /* ── Pestañas de filtro (Todos / Soporte / Académico / Administración) ── */
  var tabs = document.getElementById('ps-tabs');
  var grid = document.getElementById('ps-grid');
  if (tabs && grid) {
    tabs.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-cat]');
      if (!b) return;
      var cat = b.getAttribute('data-cat');
      Array.prototype.forEach.call(tabs.querySelectorAll('button'), function (x) { x.classList.toggle('on', x === b); });
      Array.prototype.forEach.call(grid.querySelectorAll('.ps-mod'), function (m) {
        m.classList.toggle('ps-hide', !!cat && m.getAttribute('data-cat') !== cat);
      });
    });
  }

  /* ── Gráficas ── */
  var cfg = document.getElementById('ps-chart-data');
  if (!cfg || typeof Chart === 'undefined') return;

  function parse(v) { try { return JSON.parse(v || '[]'); } catch (e) { return []; } }

  var accLabels = parse(cfg.dataset.accLabels);
  var accData   = parse(cfg.dataset.accData);
  var topLabels = parse(cfg.dataset.topLabels);
  var topData   = parse(cfg.dataset.topData);

  var dark = document.documentElement.classList.contains('dark');
  Chart.defaults.color       = dark ? '#98a2b3' : '#667085';
  Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
  var gridColor = dark ? '#1f2937' : '#e4e7ef';

  var elAcc = document.getElementById('psChartAccesos');
  if (elAcc) {
    var ctx = elAcc.getContext('2d');
    var grad = ctx.createLinearGradient(0, 0, 0, 240);
    grad.addColorStop(0, 'rgba(37,99,235,0.28)');
    grad.addColorStop(1, 'rgba(37,99,235,0.02)');
    new Chart(elAcc, {
      type: 'line',
      data: { labels: accLabels, datasets: [{
        label: 'Accesos', data: accData, borderColor: '#2563eb', backgroundColor: grad,
        fill: true, tension: 0.4, pointRadius: 3, pointHoverRadius: 5, pointBackgroundColor: '#2563eb', borderWidth: 2
      }] },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor } }, x: { grid: { display: false } } }
      }
    });
  }

  var elTop = document.getElementById('psChartTop');
  if (elTop) {
    new Chart(elTop, {
      type: 'bar',
      data: { labels: topLabels, datasets: [{ label: 'Accesos', data: topData, backgroundColor: '#7c3aed', borderRadius: 6, maxBarThickness: 16 }] },
      options: {
        indexAxis: 'y', responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: gridColor } }, y: { grid: { display: false } } }
      }
    });
  }
})();
