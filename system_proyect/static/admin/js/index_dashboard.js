(function () {
  const isDark = document.documentElement.classList.contains('dark');
  const gridColor  = isDark ? 'rgba(255,255,255,0.07)' : 'rgba(0,0,0,0.07)';
  const labelColor = isDark ? '#a1a1aa' : '#71717a';

  const baseOpts = {
    responsive: true,
    plugins: { legend: { display: false } },
    scales: {
      x: { grid: { color: gridColor }, ticks: { color: labelColor, font: { size: 11 } } },
      y: { grid: { color: gridColor }, ticks: { color: labelColor, stepSize: 1, font: { size: 11 } }, beginAtZero: true },
    },
  };

  new Chart(document.getElementById('chartLogins'), {
    type: 'bar',
    data: {
      labels: window._PAGE.loginsLabels,
      datasets: [{
        label: 'Inicios de sesión',
        data: window._PAGE.loginsData,
        backgroundColor: 'rgba(234, 88, 12, 0.25)',
        borderColor: 'rgba(234, 88, 12, 0.9)',
        borderWidth: 2,
        borderRadius: 6,
      }],
    },
    options: baseOpts,
  });

  new Chart(document.getElementById('chartActivity'), {
    type: 'line',
    data: {
      labels: window._PAGE.activityLabels,
      datasets: [{
        label: 'Acciones',
        data: window._PAGE.activityData,
        backgroundColor: 'rgba(59, 130, 246, 0.15)',
        borderColor: 'rgba(59, 130, 246, 0.9)',
        borderWidth: 2,
        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
        pointRadius: 4,
        tension: 0.4,
        fill: true,
      }],
    },
    options: baseOpts,
  });
})();
