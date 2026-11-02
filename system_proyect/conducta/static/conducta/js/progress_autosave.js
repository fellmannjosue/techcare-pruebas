// <--- hecho por claude code (27-oct-2026): auto-guardado del Progress Report (crear y editar).
// Crear: el primer guardado crea un BORRADOR (no avisa al coordinador) y la pantalla pasa a
// modo edición (los siguientes guardados actualizan ese borrador). "Finalizar" (el submit
// normal) lo pasa a "enviado" y avisa al coordinador.
// Editar: se guarda SOLO; no hay botón manual para el maestro.
// v2: además del debounce (1.5s) guarda al salir de cada campo (focusout) y hace un último
//     guardado con sendBeacon al cerrar/abandonar la página, para no perder lo recién escrito.
//     IIFE con su propio ámbito.
(function () {
  'use strict';
  document.addEventListener('DOMContentLoaded', function () {
    var cfg = document.getElementById('tc-progress-autosave');
    if (!cfg) return;
    var modo   = cfg.dataset.modo;                 // 'crear' | 'editar'
    var url    = cfg.dataset.url;                   // url de autoguardado
    var form   = document.getElementById(cfg.dataset.form);
    var estado = document.getElementById('tc-autosave-status');
    if (!form) return;

    var pk = cfg.dataset.pk || '';
    var timer = null, enviando = false, pendiente = false, sucio = false;

    function setEstado(txt, cls) {
      if (!estado) return;
      estado.textContent = txt;
      var map = { ok: 'text-success', err: 'text-danger', guardando: 'text-muted', pend: 'text-muted' };
      estado.className = 'tc-autosave small ms-1 ' + (map[cls] || 'text-muted');
    }

    // En crear, solo guardar cuando ya hay alumno + ambas semanas.
    function listoParaCrear() {
      var al = form.querySelector('[name="alumno"]');
      var si = form.querySelector('[name="semana_inicio"]');
      var sf = form.querySelector('[name="semana_fin"]');
      return !!(al && al.value && si && si.value && sf && sf.value);
    }

    function puedeGuardar() {
      if (modo === 'crear' && !pk && !listoParaCrear()) return false;
      return true;
    }

    function guardar() {
      clearTimeout(timer);
      if (enviando) { pendiente = true; return; }
      if (!puedeGuardar()) { setEstado('', ''); return; }
      enviando = true;
      sucio = false;
      setEstado('Guardando…', 'guardando');
      var fd = new FormData(form);
      fd.set('ajax', '1');
      fetch(url, { method: 'POST', headers: { 'X-Requested-With': 'XMLHttpRequest' }, body: fd })
        .then(function (r) { return r.json().then(function (j) { return j; }).catch(function () { return {}; }); })
        .then(function (j) {
          enviando = false;
          if (j && j.ok) {
            setEstado('Guardado ✓', 'ok');
            // Crear → el primer guardado devuelve pk + edit_url: pasar a modo edición.
            if (modo === 'crear' && j.pk && j.edit_url) {
              pk = String(j.pk);
              url = j.edit_url;
              form.setAttribute('action', j.edit_url);   // "Finalizar" también irá ahí
              try { history.replaceState(null, '', j.edit_url); } catch (e) {}
            }
          } else {
            var err = j && j.error;
            if (err === 'duplicado') setEstado('Ya existe un reporte de esa semana', 'err');
            else if (err === 'incompleto') setEstado('', '');
            else setEstado('No se pudo guardar', 'err');
          }
          if (pendiente) { pendiente = false; guardar(); }
        })
        .catch(function () { enviando = false; setEstado('Sin conexión', 'err'); });
    }

    function programar() {
      sucio = true;
      setEstado('Sin guardar…', 'pend');
      clearTimeout(timer);
      timer = setTimeout(guardar, 1500);
    }

    // Último intento al cerrar/abandonar la página (no se espera respuesta).
    function flushBeacon() {
      if (!sucio || enviando) return;
      if (!puedeGuardar()) return;
      try {
        var fd = new FormData(form);
        fd.set('ajax', '1');
        if (navigator.sendBeacon) { navigator.sendBeacon(url, fd); sucio = false; }
      } catch (e) {}
    }

    form.addEventListener('input', programar);
    form.addEventListener('change', programar);
    // Al salir de un campo, guardar ya (no esperar el debounce): cubre el clic en "Volver".
    form.addEventListener('focusout', function () { if (sucio) guardar(); });
    window.addEventListener('pagehide', flushBeacon);
    document.addEventListener('visibilitychange', function () {
      if (document.visibilityState === 'hidden') flushBeacon();
    });
  });
})();
