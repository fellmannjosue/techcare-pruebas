/* <--- hecho por claude code: autoguardado de los formularios de CFP
   (Informe Contable y Planilla administrativa).

   Marca el <form> con data-autoguardado y pon un <span id="tc-autoguardado">
   donde quieras el indicador. Manda el MISMO POST de siempre pero con ?ajax=1,
   así la vista guarda igual y devuelve JSON en vez de redirigir.

   Otros scripts pueden forzar un guardado con window.tcAutoguardar()
   (lo usa la planilla al agregar o quitar una fila, que no dispara 'input'). */
(function () {
  var form = document.querySelector('form[data-autoguardado]');
  if (!form) return;

  var estado    = document.getElementById('tc-autoguardado');
  var ESPERA    = 1200;         // ms sin teclear antes de guardar
  var timer     = null;
  var guardando = false;
  var pendiente = false;
  var sucio     = false;        // hay cambios que aún no llegaron al servidor
  // <--- hecho por claude code: sin botón "Guardar", el catálogo de opciones nuevas
  // se alimenta al SALIR del campo "Agregar nueva…" (no mientras se teclea, o se
  // catalogarían textos a medio escribir).
  var catalogar = false;

  function pinta(txt, clase) {
    if (!estado) return;
    estado.className = 'small ' + (clase || 'text-muted');
    estado.innerHTML = txt;
  }

  function hora() {
    var d = new Date(), p = function (n) { return String(n).padStart(2, '0'); };
    return p(d.getHours()) + ':' + p(d.getMinutes()) + ':' + p(d.getSeconds());
  }

  function fmt(n) {
    return (n || 0).toLocaleString('es-HN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // Refresca en pantalla los montos que recalcula el servidor (cargos del informe).
  function aplicar(d) {
    if (!d || !d.cargos) return;
    Object.keys(d.cargos).forEach(function (clave) {
      var celda = document.querySelector('[data-calculado="' + clave + '"]');
      if (celda) celda.value = d.cargos[clave] ? fmt(d.cargos[clave]) : '-';
    });
    // Los totales del pie los recalcula informe_form.js al recibir un 'input'.
    form.dispatchEvent(new Event('input', { bubbles: true }));
  }

  function guardar() {
    if (guardando) { pendiente = true; return; }
    guardando = true;
    pinta('<i class="ti ti-loader-2 me-1"></i>Guardando…');

    var url = form.getAttribute('action') || (location.pathname + location.search);
    url += (url.indexOf('?') >= 0 ? '&' : '?') + 'ajax=1';

    var datos = new FormData(form);
    if (catalogar) { datos.append('catalogar', '1'); catalogar = false; }

    fetch(url, {
      method: 'POST',
      body: datos,
      headers: { 'X-Requested-With': 'XMLHttpRequest' },
      credentials: 'same-origin'
    })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(r.status); })
      .then(function (d) {
        if (d && d.ok) {
          sucio = false;
          pinta('<i class="ti ti-check me-1"></i>Guardado ' + hora(), 'text-green');
          aplicar(d);
        } else {
          pinta('<i class="ti ti-alert-triangle me-1"></i>No se pudo guardar', 'text-danger');
        }
      })
      .catch(function () {
        pinta('<i class="ti ti-cloud-off me-1"></i>Sin guardar — revisa la conexión', 'text-danger');
      })
      .then(function () {
        guardando = false;
        if (pendiente) { pendiente = false; programar(); }
      });
  }

  function programar() {
    sucio = true;
    pinta('<i class="ti ti-pencil me-1"></i>Sin guardar…');
    clearTimeout(timer);
    timer = setTimeout(guardar, ESPERA);
  }

  form.addEventListener('input', function (e) {
    // El propio aplicar() dispara un 'input' sintético: no debe re-programar.
    if (e.target === form) return;
    programar();
  });
  form.addEventListener('change', function (e) {
    if (e.target === form) return;
    programar();
  });

  // Al salir de un campo "Agregar nueva…" con texto, ese guardado sí cataloga.
  form.addEventListener('focusout', function (e) {
    var i = e.target;
    if (i && i.name && /_nueva$/.test(i.name) && (i.value || '').trim()) {
      catalogar = true;
      programar();
    }
  });

  // Si se sale con algo sin guardar, se intenta guardar ya y se avisa.
  window.addEventListener('beforeunload', function (e) {
    if (!sucio) return;
    clearTimeout(timer);
    guardar();
    e.preventDefault();
    e.returnValue = '';
  });

  window.tcAutoguardar = programar;
})();
