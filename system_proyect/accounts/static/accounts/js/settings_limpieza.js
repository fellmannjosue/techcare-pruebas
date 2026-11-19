/* <--- hecho por claude code (13-nov-2026): Configuración → Respaldo y limpieza de módulos */
(function () {
  var cfg = document.getElementById('lp-cfg');
  if (!cfg) return;
  var frase = cfg.dataset.frase || 'BORRAR TODO';
  if (cfg.dataset.descarga) { window.location.href = cfg.dataset.descarga; }

  var fr = document.getElementById('lp-form-respaldo');
  var btnR = document.getElementById('lp-btn-respaldo');
  function syncR() { btnR.disabled = !fr.querySelector('.lp-chk:checked'); }
  fr.addEventListener('change', syncR); syncR();
  fr.addEventListener('submit', function () {
    btnR.disabled = true;
    btnR.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando… no cierres la página';
  });

  var modal = document.getElementById('lp-modal');
  var inFrase = document.getElementById('lp-frase');
  var btnL = document.getElementById('lp-btn-limpiar');
  inFrase.addEventListener('input', function () { btnL.disabled = inFrase.value.trim() !== frase; });
  document.querySelectorAll('.lp-limpiar').forEach(function (b) {
    b.addEventListener('click', function () {
      document.getElementById('lp-respaldo').value = b.dataset.respaldo;
      document.getElementById('lp-nom').textContent = b.dataset.respaldo;
      document.getElementById('lp-mods').textContent = b.dataset.modulos;
      inFrase.value = ''; btnL.disabled = true;
      bootstrap.Modal.getOrCreateInstance(modal).show();
    });
  });
  document.getElementById('lp-form-limpiar').addEventListener('submit', function () {
    btnL.disabled = true;
    btnL.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Limpiando…';
  });
})();
