/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
(function () {
  const canvas = document.getElementById('sign');
  const ctx = canvas.getContext('2d');
  let drawing = false, lastX = 0, lastY = 0, hasDrawn = false;
  function resize() { const r = canvas.getBoundingClientRect(); canvas.width = r.width; canvas.height = r.height; }
  resize(); window.addEventListener('resize', resize);
  function pos(e) { const r = canvas.getBoundingClientRect(); const s = e.touches ? e.touches[0] : e; return [s.clientX - r.left, s.clientY - r.top]; }
  function start(e) { drawing = true;[lastX, lastY] = pos(e); }
  function move(e) {
    if (!drawing) return; e.preventDefault();
    ctx.beginPath(); ctx.moveTo(lastX, lastY);[lastX, lastY] = pos(e); ctx.lineTo(lastX, lastY);
    ctx.strokeStyle = '#1a1a2e'; ctx.lineWidth = 2.5; ctx.lineCap = 'round'; ctx.stroke(); hasDrawn = true;
  }
  function end() { drawing = false; }
  canvas.addEventListener('mousedown', start); canvas.addEventListener('mousemove', move);
  canvas.addEventListener('mouseup', end); canvas.addEventListener('mouseleave', end);
  canvas.addEventListener('touchstart', e => { e.preventDefault(); start(e); }, { passive: false });
  canvas.addEventListener('touchmove', move, { passive: false });
  canvas.addEventListener('touchend', end);
  document.getElementById('clear').addEventListener('click', () => { ctx.clearRect(0, 0, canvas.width, canvas.height); hasDrawn = false; });
  document.getElementById('firmaForm').addEventListener('submit', function (e) {
    if (!hasDrawn) { e.preventDefault(); alert('Por favor firma antes de enviar.'); return; }
    document.getElementById('firma_data').value = canvas.toDataURL('image/png');
  });
})();
