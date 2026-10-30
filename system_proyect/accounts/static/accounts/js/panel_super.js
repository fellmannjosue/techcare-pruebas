/* <--- hecho por claude code: Panel Principal del superusuario — gráficas de actividad (Chart.js,
   datos reales por data-*) y pestañas de filtro de la cuadrícula de módulos (Horizon, 30-sep-2026). */
(function () {
  'use strict';

  /* ── Filtro: pestañas de categoría + buscador en vivo ── */
  var tabs = document.getElementById('ps-tabs');
  var grid = document.getElementById('ps-grid');
  var inputQ = document.getElementById('ps-q');
  var countEl = document.getElementById('ps-count');
  var catSel = '', query = '';

  function aplicarFiltro() {
    if (!grid) return;
    var visibles = 0;
    Array.prototype.forEach.call(grid.querySelectorAll('.ps-mod'), function (m) {
      var okCat = !catSel || m.getAttribute('data-cat') === catSel;
      var okQ = !query || (m.getAttribute('data-search') || '').toLowerCase().indexOf(query) >= 0;
      var ok = okCat && okQ;
      m.classList.toggle('ps-hide', !ok);
      if (ok) visibles++;
    });
    if (countEl) countEl.textContent = visibles + (visibles === 1 ? ' programa' : ' programas');
  }

  if (tabs && grid) {
    tabs.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-cat]');
      if (!b) return;
      catSel = b.getAttribute('data-cat');
      Array.prototype.forEach.call(tabs.querySelectorAll('button'), function (x) { x.classList.toggle('on', x === b); });
      aplicarFiltro();
    });
  }
  if (inputQ) {
    inputQ.addEventListener('input', function () { query = this.value.trim().toLowerCase(); aplicarFiltro(); });
  }

  /* ── Tiles "Launcher" con varios accesos: desplegar/colapsar al tocarlos ── */
  if (grid) {
    grid.addEventListener('click', function (e) {
      var sec = e.target.closest('.ps-mod-multi');
      if (!sec) return;
      if (e.target.closest('.ps-mod-list a')) return;   // dejar pasar el clic al enlace
      var abierto = sec.classList.toggle('abierto');
      sec.setAttribute('aria-expanded', abierto ? 'true' : 'false');
    });
    grid.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var sec = e.target.closest('.ps-mod-multi');
      if (!sec || e.target !== sec) return;
      e.preventDefault();
      var abierto = sec.classList.toggle('abierto');
      sec.setAttribute('aria-expanded', abierto ? 'true' : 'false');
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
