/* <--- hecho por claude code: gráficas del dashboard de Red */
(function () {
  var cfg = document.getElementById('red-charts');
  if (!cfg || typeof Chart === 'undefined') return;
  var p = function (v) { try { return JSON.parse(v || '[]'); } catch (e) { return []; } };
  var dark = document.documentElement.classList.contains('dark');
  Chart.defaults.color = dark ? '#c7ccd6' : '#64748b';

  var elV = document.getElementById('chartVlan');
  if (elV) new Chart(elV, {
    type: 'bar',
    data: { labels: p(cfg.dataset.vlanLabels), datasets: [{ label: 'Ocupación %', data: p(cfg.dataset.vlanOcup), backgroundColor: 'rgba(32,107,196,0.75)', borderRadius: 4 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { beginAtZero: true, max: 100 } }, plugins: { legend: { display: false } } }
  });

  var elD = document.getElementById('chartDisp');
  if (elD) new Chart(elD, {
    type: 'doughnut',
    data: { labels: p(cfg.dataset.dispLabels), datasets: [{ data: p(cfg.dataset.dispData),
      backgroundColor: ['#206bc4', '#2fb344', '#f76707', '#ae3ec9', '#d63939', '#0ca678', '#f59f00', '#4263eb', '#d6336c', '#12b886'] }] },
    options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } }
  });
})();
