/* <--- hecho por claude code (09-nov-2026): Programas por aplicación — autoguardado de cada interruptor */
(function () {
  var cfg = document.getElementById('cn-cfg');
  if (!cfg) return;
  var estado = document.getElementById('cn-estado');
  function pinta(txt, cls) { estado.className = 'card-options small ' + (cls || 'text-secondary'); estado.textContent = txt; }
  document.addEventListener('change', function (e) {
    var sw = e.target.closest('.cn-sw'); if (!sw) return;
    var fd = new FormData();
    fd.append('canal', sw.dataset.canal);
    fd.append('programa', sw.dataset.programa);
    fd.append('visible', sw.checked ? '1' : '0');
    sw.disabled = true; pinta('Guardando…');
    fetch(cfg.dataset.url, { method: 'POST', body: fd, credentials: 'same-origin', headers: { 'X-CSRFToken': cfg.dataset.csrf } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        sw.disabled = false;
        if (!d.ok) { sw.checked = !sw.checked; pinta(d.error || 'No se guardó', 'text-danger'); return; }
        var n = document.querySelector('.cn-res[data-canal="' + d.canal + '"] .cn-num'); if (n) n.textContent = d.visibles;
        pinta('✓ ' + d.msg, 'text-green');
      })
      .catch(function () { sw.disabled = false; sw.checked = !sw.checked; pinta('Sin conexión — no se guardó', 'text-danger'); });
  });
})();
