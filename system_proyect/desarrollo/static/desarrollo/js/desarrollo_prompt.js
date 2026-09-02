/* <--- hecho por claude code: copiar el prompt para Claude Code al portapapeles. */
(function () {
  'use strict';
  var btn = document.getElementById('btnCopiarPrompt');
  if (!btn) { return; }
  var ta = document.getElementById(btn.getAttribute('data-target'));
  if (!ta) { return; }

  btn.addEventListener('click', function () {
    var texto = ta.value;
    function ok() {
      var original = btn.innerHTML;
      btn.innerHTML = '<i class="ti ti-check me-1"></i>Copiado';
      btn.classList.add('btn-success');
      setTimeout(function () { btn.innerHTML = original; btn.classList.remove('btn-success'); }, 1600);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texto).then(ok, function () { fallback(); });
    } else {
      fallback();
    }
    function fallback() {
      ta.removeAttribute('readonly');
      ta.select();
      try { document.execCommand('copy'); ok(); } catch (e) { alert('No se pudo copiar automáticamente; selecciona y copia manual.'); }
      ta.setAttribute('readonly', 'readonly');
      window.getSelection().removeAllRanges();
    }
  });
})();
