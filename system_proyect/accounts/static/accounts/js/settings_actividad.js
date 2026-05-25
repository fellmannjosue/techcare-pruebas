(function(){
  const _cfg = document.getElementById('page-config');
  if (!_cfg) return;

  const diasLabels = JSON.parse(_cfg.dataset.diasLabels || '[]');
  const diasData   = JSON.parse(_cfg.dataset.diasData   || '[]');
  const topLabels  = JSON.parse(_cfg.dataset.topLabels  || '[]');
  const topData    = JSON.parse(_cfg.dataset.topData    || '[]');
  const hasTop     = _cfg.dataset.hasTop === 'true';

  new Chart(document.getElementById('chartLoginsDia'), {
    type: 'line',
    data: {
      labels: diasLabels,
      datasets: [{
        label: 'Inicios de sesión',
        data: diasData,
        borderColor: '#206bc4',
        backgroundColor: 'rgba(32,107,196,0.08)',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 5,
      }]
    },
    options: {
      responsive: true,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 } }
      }
    }
  });

  if (hasTop) {
    new Chart(document.getElementById('chartTopUsuarios'), {
      type: 'bar',
      data: {
        labels: topLabels,
        datasets: [{
          label: 'Accesos',
          data: topData,
          backgroundColor: 'rgba(32,107,196,0.7)',
          borderRadius: 4,
        }]
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        plugins: { legend: { display: false } },
        scales: { x: { beginAtZero: true, ticks: { stepSize: 1, precision: 0 } } }
      }
    });
  }
})();
