/* form_agenda.js – agendas
   <--- hecho por claude code: restaurado el auto-submit al cambiar de grado (se
   perdió en la extracción de JS: sin él la tabla de materias nunca cargaba y el
   docente no podía registrar) y protegido el countdown contra elemento ausente. */

/* 1) Recargar la página al cambiar de grado para traer las materias correctas.
   form.submit() (método) omite la validación HTML5, así que envía aunque las
   fechas estén vacías; la vista solo recarga la tabla (no guarda) si no viene
   el botón "guardar". */
(function () {
  var gradoSelect = document.getElementById('gradoSelect');
  var formAgenda  = document.getElementById('formAgenda');
  if (gradoSelect && formAgenda) {
    gradoSelect.addEventListener('change', function () {
      formAgenda.submit();
    });
  }
})();

/* 2) Countdown de cierre (solo si existe el banner y su config). */
(function () {
  var cfg = document.getElementById('form_agenda-config');
  var el  = document.getElementById('cd-timer');
  if (!cfg || !el) return;
  var end = new Date(cfg.dataset.v0).getTime();
  function tick() {
    var diff = end - Date.now();
    if (diff <= 0) {
      var banner = document.getElementById('cd-banner');
      if (banner) banner.className = 'alert alert-danger mb-3';
      el.parentElement.innerHTML = '<strong>El llenado de agendas se ha cerrado.</strong> Recarga la página.';
      return;
    }
    var h = Math.floor(diff / 3.6e6),
        m = Math.floor(diff % 3.6e6 / 6e4),
        s = Math.floor(diff % 6e4 / 1000);
    el.textContent = (h < 10 ? '0' : '') + h + ':' + (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    setTimeout(tick, 1000);
  }
  tick();
})();

/* 3) La fecha final no puede ser anterior a la de inicio. */
(function () {
  var ini = document.getElementById('ag_semana_inicio'),
      fin = document.getElementById('ag_semana_fin');
  if (!ini || !fin) return;
  function sync() {
    fin.min = ini.value || '';
    if (fin.value && ini.value && fin.value < ini.value) {
      fin.setCustomValidity('La fecha final no puede ser anterior a la de inicio.');
    } else {
      fin.setCustomValidity('');
    }
  }
  ini.addEventListener('change', sync);
  fin.addEventListener('change', sync);
  sync();
})();
