/* admin_inicio.js — <--- hecho por claude code (16-oct-2026): gráficas del inicio del panel admin (datos por json_script).
   Usa el Chart.js que trae Unfold; si no está, no dibuja nada. Un solo global: TCA_INICIO. */
(function () {
  'use strict';
  function leer(id) { var el = document.getElementById(id); try { return el ? JSON.parse(el.textContent) : []; } catch (e) { return []; } }
  function dibujar() {
    if (!window.Chart) return;
    var oscuro = document.documentElement.classList.contains('dark');
    var rejilla = oscuro ? 'rgba(255,255,255,.07)' : 'rgba(0,0,0,.06)', texto = oscuro ? '#a1a1aa' : '#6b7280';
    var base = { responsive: true, plugins: { legend: { display: false } },
      scales: { x: { grid: { color: rejilla }, ticks: { color: texto, font: { size: 11 } } },
                y: { grid: { color: rejilla }, ticks: { color: texto, precision: 0, font: { size: 11 } }, beginAtZero: true } } };
    var l = document.getElementById('tcaLogins'), a = document.getElementById('tcaActividad');
    if (l) new Chart(l, { type: 'bar', options: base, data: { labels: leer('tca-l-lab'), datasets: [{ label: 'Inicios de sesión', data: leer('tca-l-dat'),
      backgroundColor: 'rgba(37, 99, 235, .35)', borderColor: '#2563eb', borderWidth: 2, borderRadius: 6 }] } });
    if (a) new Chart(a, { type: 'line', options: base, data: { labels: leer('tca-a-lab'), datasets: [{ label: 'Acciones', data: leer('tca-a-dat'),
      backgroundColor: 'rgba(124, 58, 237, .14)', borderColor: '#7c3aed', borderWidth: 2, pointBackgroundColor: '#7c3aed', pointRadius: 3, tension: .4, fill: true }] } });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', dibujar); else dibujar();
  window.TCA_INICIO = { dibujar: dibujar };
})();
