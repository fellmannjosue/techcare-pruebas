/* <--- hecho por claude code: editor de topología con Cytoscape.js */
(function () {
  var cfg = document.getElementById('topo-cfg');
  if (!cfg || typeof cytoscape === 'undefined') return;
  var CSRF = cfg.dataset.csrf, POS_URL = cfg.dataset.pos;
  function J(v) { try { return JSON.parse(v || '[]'); } catch (e) { return []; } }
  var rawNodes = J(cfg.dataset.nodes), rawEdges = J(cfg.dataset.edges);

  // Elementos: asigna posición en cuadrícula a los nodos sin coordenadas guardadas
  var gx = 60, gy = 60, i = 0;
  var elements = [];
  rawNodes.forEach(function (n) {
    var pos = n.position && n.position.x != null ? n.position : { x: gx + (i % 8) * 130, y: gy + Math.floor(i / 8) * 110 };
    i++;
    elements.push({ data: n.data, position: pos });
  });
  rawEdges.forEach(function (e) { elements.push({ data: e.data }); });

  var dark = document.documentElement.classList.contains('dark');
  var cy = cytoscape({
    container: document.getElementById('cy'),
    elements: elements,
    style: [
      { selector: 'node', style: {
        'background-color': 'data(color)', 'label': 'data(label)', 'width': 34, 'height': 34,
        'font-size': 9, 'color': dark ? '#c7ccd6' : '#333', 'text-valign': 'bottom', 'text-margin-y': 3,
        'border-width': 2, 'border-color': '#fff', 'text-outline-width': 2, 'text-outline-color': dark ? '#1a2234' : '#f8f9fb' } },
      { selector: 'node[?ciclo]', style: { 'border-color': '#d63939', 'border-width': 3 } },
      { selector: 'edge', style: {
        'width': 2, 'line-color': '#adb5bd', 'curve-style': 'bezier', 'target-arrow-shape': 'none' } },
      { selector: 'edge[tipo="fibra"]', style: { 'line-color': '#206bc4' } },
      { selector: 'edge[tipo="radio"]', style: { 'line-style': 'dashed' } },
      { selector: 'edge[tipo="virtual"]', style: { 'line-style': 'dotted' } },
      { selector: 'edge[modo="trunk"]', style: { 'width': 5 } },
      { selector: ':selected', style: { 'line-color': '#f59f00', 'border-color': '#f59f00', 'background-color': '#f59f00' } },
    ],
    layout: { name: 'preset' },
    wheelSensitivity: 0.2,
  });
  cy.fit(null, 40);

  // Guardar posición al soltar un nodo (solo dispositivos "d…"; los "m…" son de un plano)
  cy.on('dragfree', 'node', function (ev) {
    var n = ev.target, rawId = n.id();
    if (rawId.charAt(0) !== 'd') return;   // en modo plano no se guarda posición
    var id = rawId.replace(/^d/, ''), p = n.position();
    var body = new URLSearchParams({ x: p.x, y: p.y });
    fetch(POS_URL.replace('/0/', '/' + id + '/'), {
      method: 'POST', headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/x-www-form-urlencoded' }, body: body
    });
  });

  // Info del enlace al hacer clic
  var info = document.createElement('div');
  info.style.cssText = 'position:absolute;z-index:5;background:#222;color:#fff;padding:4px 8px;border-radius:5px;font-size:.75rem;display:none;pointer-events:none;';
  document.getElementById('cy').parentNode.style.position = 'relative';
  document.getElementById('cy').parentNode.appendChild(info);
  cy.on('tap', 'edge', function (ev) {
    var d = ev.target.data();
    info.innerHTML = '<strong>' + d.label + '</strong> · ' + (d.modo || '') +
      (d.nativa ? ' · nativa ' + d.nativa : '') + (d.permitidas ? ' · tagged ' + d.permitidas : '');
    var rp = ev.renderedPosition;
    info.style.left = (rp.x + 8) + 'px'; info.style.top = (rp.y + 8) + 'px'; info.style.display = 'block';
  });
  cy.on('tap', function (ev) { if (ev.target === cy) info.style.display = 'none'; });

  // Botones
  document.getElementById('btn-fit').addEventListener('click', function () { cy.fit(null, 40); });
  document.getElementById('btn-png').addEventListener('click', function () {
    var a = document.createElement('a');
    a.href = cy.png({ full: true, scale: 2, bg: dark ? '#1a2234' : '#ffffff' });
    a.download = 'topologia.png'; a.click();
  });

  // <--- hecho por claude code: export SVG (vectorial, usa el plugin cytoscape-svg)
  function descargar(blob, nombre) {
    var url = URL.createObjectURL(blob), a = document.createElement('a');
    a.href = url; a.download = nombre; a.click();
    setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
  }
  var btnSvg = document.getElementById('btn-svg');
  if (btnSvg) btnSvg.addEventListener('click', function () {
    if (typeof cy.svg !== 'function') { alert('El plugin SVG no cargó (sin conexión al CDN).'); return; }
    var svg = cy.svg({ full: true, scale: 1, bg: dark ? '#1a2234' : '#ffffff' });
    descargar(new Blob([svg], { type: 'image/svg+xml;charset=utf-8' }), 'topologia.svg');
  });

  // <--- hecho por claude code: export PDF (jsPDF: mete el PNG de alta resolución en una hoja apaisada)
  var btnPdf = document.getElementById('btn-pdf');
  if (btnPdf) btnPdf.addEventListener('click', function () {
    if (!window.jspdf || !window.jspdf.jsPDF) { alert('jsPDF no cargó (sin conexión al CDN).'); return; }
    var png = cy.png({ full: true, scale: 3, bg: '#ffffff' });   // PDF siempre fondo blanco (imprimible)
    var img = new Image();
    img.onload = function () {
      var landscape = img.width >= img.height;
      var doc = new window.jspdf.jsPDF({ orientation: landscape ? 'landscape' : 'portrait', unit: 'mm', format: 'a4' });
      var pw = doc.internal.pageSize.getWidth(), ph = doc.internal.pageSize.getHeight(), m = 10;
      doc.setFontSize(13); doc.text('Topología de red — ANA Network Manager', m, m + 2);
      doc.setFontSize(9); doc.text(new Date().toLocaleString('es-HN'), pw - m, m + 2, { align: 'right' });
      var maxW = pw - 2 * m, maxH = ph - 2 * m - 10;
      var r = Math.min(maxW / img.width, maxH / img.height);
      var w = img.width * r, h = img.height * r;
      doc.addImage(png, 'PNG', m + (maxW - w) / 2, m + 8, w, h);
      doc.save('topologia.pdf');
    };
    img.src = png;
  });
})();
