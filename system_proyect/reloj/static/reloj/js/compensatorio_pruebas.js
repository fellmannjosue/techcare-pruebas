/* <--- hecho por claude code (16-sep-2026): pantalla "Pruebas" del Reloj.
   Los modales (días no laborables, tiempo extra, tiempo tomado) y el lápiz de la vacación
   acumulada los maneja el JS compartido de Cálculo Compensatorio. Como en esta pantalla los
   tabs 2, 3 y 4 dependen de esos datos, al cerrar cualquiera de esos modales se recarga la
   página para que todos los números vuelvan a cuadrar. */
(function () {
  // En Pruebas el modal de tiempo tomado NO muestra las horas de permiso de los 3 días (van en el tab 4)
  if (window._PAGE && window._PAGE.urlGetTomado) window._PAGE.urlGetTomado = window._PAGE.urlGetTomado + '?pruebas=1';
  var ids = ['modalDiasNoLab', 'modalTiempoExtra', 'modalTomado'];
  var tocado = false;
  // Cualquier POST hecho desde un modal marca la página como "sucia"
  var _fetch = window.fetch;
  window.fetch = function (url, opts) {
    if (opts && String(opts.method || 'GET').toUpperCase() === 'POST') tocado = true;
    return _fetch.apply(this, arguments);
  };
  ids.forEach(function (id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.addEventListener('hidden.bs.modal', function () {
      if (tocado) location.reload();
    });
  });
  // Valores fijados a mano (vacío = volver al cálculo): tab 1 "Saldo para gastar", tab 4 "Tomado de los 3 días"
  var pc = document.getElementById('pruebas-config');
  function editorManual(selector, url, campo, titulo) {
    document.querySelectorAll(selector).forEach(function (btn) {
      btn.addEventListener('click', function () {
        if (!pc) return;
        var val = window.prompt(titulo + ' — ' + (btn.dataset.nombre || '') + '\n(deja vacío para volver al valor calculado):', btn.dataset.valor || '');
        if (val === null) return;
        val = val.trim().replace(',', '.');
        if (val !== '' && isNaN(parseFloat(val))) { alert('Número inválido.'); return; }
        var body = { emp_code: btn.dataset.emp }; body[campo] = val;
        fetch(url, { method: 'POST', credentials: 'same-origin',
                     headers: { 'Content-Type': 'application/json', 'X-CSRFToken': pc.dataset.csrf },
                     body: JSON.stringify(body) })
          .then(function (r) { return r.json(); })
          .then(function (d) { if (d.ok) location.reload(); else alert(d.error || 'Error'); })
          .catch(function () { alert('Error de conexión.'); });
      });
    });
  }
  if (pc) {
    editorManual('.btn-edit-permtom', pc.dataset.permtom, 'horas', 'Horas tomadas de los 3 días de permiso');
    editorManual('.btn-edit-saldo', pc.dataset.saldo, 'saldo', 'Saldo para gastar (días)');
  }

  // Recordar el tab activo entre recargas
  // (también en Cálculo Compensatorio, que ahora incluye estos 4 tabs)
  try {
    var lista = document.getElementById('pruebas-tabs') || document.getElementById('comp-tabs');
    if (lista) {
      var clave = 'tc-tab-' + lista.id;
      var activo = localStorage.getItem(clave);
      // En Pruebas ningún panel viene activo del servidor: si no hay tab guardado, abrir el primero
      if (!activo && lista.id === 'pruebas-tabs') activo = '#ptab-vac';
      if (activo && !lista.querySelector('[data-bs-target="' + activo + '"]')) activo = (lista.id === 'pruebas-tabs') ? '#ptab-vac' : null;
      if (activo) { var b = lista.querySelector('[data-bs-target="' + activo + '"]'); if (b && window.bootstrap) new bootstrap.Tab(b).show(); }
      lista.querySelectorAll('[data-bs-target]').forEach(function (b) {
        b.addEventListener('shown.bs.tab', function () { localStorage.setItem(clave, b.dataset.bsTarget); });
      });
    }
  } catch (e) {}
})();
