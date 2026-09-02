/* <--- hecho por claude code: gráficas de actividad del Panel Principal (Chart.js, datos reales) */
(function () {
  var cfg = document.getElementById('ps-chart-data');
  if (!cfg || typeof Chart === 'undefined') return;

  function parse(v) { try { return JSON.parse(v || '[]'); } catch (e) { return []; } }

  var accLabels = parse(cfg.dataset.accLabels);
  var accData   = parse(cfg.dataset.accData);
  var topLabels = parse(cfg.dataset.topLabels);
  var topData   = parse(cfg.dataset.topData);

  // Tema claro/oscuro: color de texto y grillas legibles en ambos
  var dark = document.documentElement.classList.contains('dark');
  Chart.defaults.color       = dark ? '#c7ccd6' : '#64748b';
  Chart.defaults.font.family = "Inter, system-ui, sans-serif";
  var grid = dark ? 'rgba(148,163,184,0.15)' : 'rgba(148,163,184,0.22)';

  // ── Accesos por día (área) ──
  var elAcc = document.getElementById('psChartAccesos');
  if (elAcc) {
    var ctx = elAcc.getContext('2d');
    var grad = ctx.createLinearGradient(0, 0, 0, 240);
    grad.addColorStop(0, 'rgba(32,107,196,0.28)');
    grad.addColorStop(1, 'rgba(32,107,196,0.02)');
    new Chart(elAcc, {
      type: 'line',
      data: {
        labels: accLabels,
        datasets: [{
          label: 'Accesos',
          data: accData,
          borderColor: '#206bc4',
          backgroundColor: grad,
          fill: true,
          tension: 0.4,
          pointRadius: 2,
          pointHoverRadius: 5,
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: grid } },
          x: { grid: { display: false } }
        }
      }
    });
  }

  // ── Top usuarios (barra horizontal) ──
  var elTop = document.getElementById('psChartTop');
  if (elTop) {
    new Chart(elTop, {
      type: 'bar',
      data: {
        labels: topLabels,
        datasets: [{
          label: 'Accesos',
          data: topData,
          backgroundColor: 'rgba(174,62,201,0.75)',
          borderRadius: 5,
          maxBarThickness: 18,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { beginAtZero: true, ticks: { precision: 0 }, grid: { color: grid } },
          y: { grid: { display: false } }
        }
      }
    });
  }
})();
