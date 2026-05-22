(function(){
  if (typeof window._PAGE === 'undefined') return;

  const diasLabels = window._PAGE.diasLabels;
  const diasData   = window._PAGE.diasData;
  const topLabels  = window._PAGE.topLabels;
  const topData    = window._PAGE.topData;
  const hasTop     = window._PAGE.hasTop;

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
