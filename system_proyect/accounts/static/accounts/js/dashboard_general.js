/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
(function () {
  // Toggle de área para maestro (BL / Colegio) — solo cuando hay ambas áreas.
  var toggle = document.getElementById('dg-area-toggle');
  if (!toggle) return;
  var KEY = 'dgMaestroArea';
  function aplicar(area) {
    document.querySelectorAll('.dg-maestro-area').forEach(function (el) {
      el.style.display = (el.dataset.area === area) ? '' : 'none';
    });
    toggle.querySelectorAll('button').forEach(function (b) {
      b.classList.toggle('active', b.dataset.area === area);
    });
    try { localStorage.setItem(KEY, area); } catch (e) {}
  }
  toggle.querySelectorAll('button').forEach(function (b) {
    b.addEventListener('click', function () { aplicar(this.dataset.area); });
  });
  var guardada = null;
  try { guardada = localStorage.getItem(KEY); } catch (e) {}
  aplicar(guardada === 'colegio' ? 'colegio' : 'bilingue');
})();
