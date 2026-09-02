/* <--- hecho por claude code: Fase 4 — panel avanzado de red (gráficas Chart.js) */
(function () {
  var cfg = document.getElementById('panel-data');
  if (!cfg || !window.Chart) return;
  var G; try { G = JSON.parse(cfg.dataset.graf || '{}'); } catch (e) { return; }

  var oscuro = document.documentElement.classList.contains('dark');
  var txt = oscuro ? '#c7cfe0' : '#495057';
  var grid = oscuro ? 'rgba(148,163,184,.15)' : 'rgba(0,0,0,.06)';
  Chart.defaults.color = txt;
  Chart.defaults.font.family = "'Inter', system-ui, sans-serif";

  var PAL = ['#206bc4', '#4263eb', '#ae3ec9', '#d6336c', '#f76707', '#2fb344',
             '#12b886', '#e8590c', '#7048e8', '#f59f00', '#0ca678', '#d63939',
             '#4299e1', '#66a80f', '#862e9c', '#e64980'];
  function colores(n) { var a = []; for (var i = 0; i < n; i++) a.push(PAL[i % PAL.length]); return a; }

  function mk(id, type, data, opts) {
    var el = document.getElementById(id); if (!el) return;
    new Chart(el, { type: type, data: data, options: opts });
  }
  var ejeStack = {
    plugins: { legend: { position: 'bottom' } },
    responsive: true, maintainAspectRatio: false,
    scales: { x: { stacked: true, ticks: { color: txt }, grid: { color: grid } },
              y: { stacked: true, beginAtZero: true, ticks: { color: txt }, grid: { color: grid } } }
  };
  var ejeBar = {
    plugins: { legend: { display: false } },
    responsive: true, maintainAspectRatio: false,
    scales: { x: { ticks: { color: txt }, grid: { color: grid } },
              y: { beginAtZero: true, ticks: { color: txt }, grid: { color: grid } } }
  };
  var doughnut = { plugins: { legend: { position: 'bottom' } }, responsive: true, maintainAspectRatio: false };

  // Dispositivos por tipo (doughnut)
  if (G.disp) mk('cDisp', 'doughnut', {
    labels: G.disp.labels,
    datasets: [{ data: G.disp.data, backgroundColor: colores(G.disp.labels.length), borderWidth: 0 }]
  }, doughnut);

  // Dispositivos por edificio (barras)
  if (G.edif) mk('cEdif', 'bar', {
    labels: G.edif.labels,
    datasets: [{ label: 'Dispositivos', data: G.edif.data, backgroundColor: '#4263eb', borderRadius: 6 }]
  }, ejeBar);

  // IPs por VLAN (barras apiladas)
  if (G.vlan) mk('cVlan', 'bar', {
    labels: G.vlan.labels,
    datasets: [
      { label: 'Usadas', data: G.vlan.usadas, backgroundColor: '#d6336c', borderRadius: 4 },
      { label: 'Libres', data: G.vlan.libres, backgroundColor: '#2fb344', borderRadius: 4 }
    ]
  }, ejeStack);

  // Capacidad de VLANs (doughnut con colores fijos)
  if (G.cap) mk('cCap', 'doughnut', {
    labels: G.cap.labels,
    datasets: [{ data: G.cap.data, backgroundColor: ['#2fb344', '#f59f00', '#f76707', '#d63939'], borderWidth: 0 }]
  }, doughnut);

  // Enlaces por tipo (doughnut)
  if (G.enl) mk('cEnl', 'doughnut', {
    labels: G.enl.labels,
    datasets: [{ data: G.enl.data, backgroundColor: colores(G.enl.labels.length), borderWidth: 0 }]
  }, doughnut);

  // Ocupación de puertos por switch (barras apiladas)
  if (G.sw) mk('cSw', 'bar', {
    labels: G.sw.labels,
    datasets: [
      { label: 'Ocupados', data: G.sw.ocup, backgroundColor: '#206bc4', borderRadius: 4 },
      { label: 'Libres', data: G.sw.libre, backgroundColor: '#adb5bd', borderRadius: 4 }
    ]
  }, ejeStack);
})();
