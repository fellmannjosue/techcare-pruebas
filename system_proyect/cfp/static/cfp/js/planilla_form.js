/* <--- hecho por claude code: planilla de gastos administrativos.
   (09-sep-2026) El monto de cada persona se ESCRIBE A MANO: ya no se reparte
   automáticamente en partes iguales. Aquí solo se suma lo escrito y se compara
   con el "disponible" (20% − capturados) para avisar si cuadra, falta o se pasa.
   (09-sep-2026) Al elegir el CARGO se cargan nombre y DNI de la persona registrada
   en el admin (catálogo "Personas por cargo"); "Agregar persona" trae al siguiente
   cargo del catálogo que aún no está en la planilla. */
const CFG_CFP_PLANILLA = (function () {
  var el = document.getElementById('planilla-config');
  var personas = {};
  try { personas = JSON.parse((el && el.dataset.personas) || '{}') || {}; } catch (e) { personas = {}; }
  return { disponible: el ? parseFloat(el.dataset.v0) || 0 : 0,
           personas: personas,     // (09-sep-2026) cargo → {nombre, dni}, catálogo del admin
           personasUrl: el ? (el.dataset.personasUrl || '') : '' };
})();

(function () {
  var tbody = document.getElementById('tb-planilla');
  if (!tbody) return;
  var tpl     = document.getElementById('tpl-fila');
  var vacio   = document.getElementById('msj-vacio');
  var totalEl = document.getElementById('total-repartido');
  var resumen = document.getElementById('resumen-reparto');

  function fmt(n) {
    return (n || 0).toLocaleString('es-HN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }
  // Acepta "1,234.56" (formato del filtro money) o "1234.56".
  function num(v) {
    var n = parseFloat(String(v || '').replace(/[^0-9.\-]/g, ''));
    return isNaN(n) ? 0 : n;
  }

  function recalcular() {
    var filas = Array.prototype.slice.call(tbody.querySelectorAll('.fila-persona'));
    var n = filas.length;
    if (vacio) vacio.hidden = n > 0;
    var suma = 0;
    filas.forEach(function (tr) {
      var inp = tr.querySelector('.inp-monto');
      suma += num(inp && inp.value);
    });
    suma = Math.round(suma * 100) / 100;
    totalEl.textContent = 'L ' + fmt(suma);
    if (!n) { resumen.textContent = ''; return; }
    var disp = CFG_CFP_PLANILLA.disponible;
    var dif  = Math.round((disp - suma) * 100) / 100;
    var estado = Math.abs(dif) < 0.005
      ? '<span class="text-green">cuadra</span>'
      : (dif > 0 ? '<span class="text-warning">faltan L ' + fmt(dif) + '</span>'
                 : '<span class="text-danger">se pasa L ' + fmt(-dif) + '</span>');
    resumen.innerHTML = n + (n === 1 ? ' persona · ' : ' personas · ') +
      'Disponible L ' + fmt(disp) + ' · Repartido L ' + fmt(suma) + ' · ' + estado;
  }

  // Agregar/quitar filas no dispara 'input', así que hay que avisarle al autoguardado a mano.
  function avisarAutoguardado() {
    if (typeof window.tcAutoguardar === 'function') window.tcAutoguardar();
  }

  // ── (09-sep-2026) Al elegir el cargo se carga la persona del catálogo (admin) ──
  // Solo se pisa el nombre si la fila está vacía o si lo puso este mismo autollenado
  // (data-auto="1"); lo que el usuario escribió a mano se respeta.
  function aplicarPersona(fila) {
    var sel = fila.querySelector('.inp-cargo');
    var nom = fila.querySelector('.inp-nombre');
    var dni = fila.querySelector('.inp-dni');
    if (!sel || !nom) return false;
    var per = CFG_CFP_PLANILLA.personas[sel.value];
    var puedePisar = !nom.value.trim() || fila.dataset.auto === '1';
    if (!puedePisar) return false;
    if (per && per.nombre) {
      nom.value = per.nombre;
      if (dni) dni.value = per.dni || '';
      fila.dataset.auto = '1';
      return true;
    }
    if (fila.dataset.auto === '1') {         // el cargo nuevo no tiene persona: no dejar la anterior
      nom.value = ''; if (dni) dni.value = '';
      fila.dataset.auto = '0';
    }
    return false;
  }

  // El catálogo se consulta EN VIVO al elegir el cargo y al agregar persona: así no hace
  // falta recargar la planilla después de registrar a alguien en el admin. Si la consulta
  // falla se sigue con lo que traía la página.
  function refrescarPersonas(cb) {
    var url = CFG_CFP_PLANILLA.personasUrl;
    if (!url || !window.fetch) { cb(); return; }
    fetch(url, { credentials: 'same-origin', headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) { if (j && typeof j === 'object') CFG_CFP_PLANILLA.personas = j; })
      .catch(function () {})
      .then(cb);
  }

  // Primer cargo del catálogo que todavía no está en la planilla (para que "Agregar"
  // vaya trayendo a cada persona en orden); si todos están, se deja el primero del select.
  function cargoSugerido() {
    var usados = {};
    tbody.querySelectorAll('.fila-persona .inp-cargo').forEach(function (s) { usados[s.value] = true; });
    var opts = tpl.content.querySelectorAll('.inp-cargo option');
    for (var i = 0; i < opts.length; i++) {
      var k = opts[i].value, per = CFG_CFP_PLANILLA.personas[k];
      if (per && per.nombre && !usados[k]) return k;
    }
    return null;
  }

  document.getElementById('btn-agregar').addEventListener('click', function () {
    tbody.appendChild(tpl.content.cloneNode(true));
    var filas = tbody.querySelectorAll('.fila-persona');
    var fila  = filas[filas.length - 1];
    recalcular();
    refrescarPersonas(function () {
      var nom = fila && fila.querySelector('.inp-nombre');
      if (nom && !nom.value.trim()) {            // si aún no escribieron nada, se sugiere el cargo
        var k = cargoSugerido();
        if (k) { fila.querySelector('.inp-cargo').value = k; aplicarPersona(fila); }
      }
      var foco = fila && fila.querySelector(fila.dataset.auto === '1' ? '.inp-monto' : '.inp-nombre');
      if (foco) foco.focus();
    });
    // No se autoguarda al agregar: se guarda al primer cambio (cargo, monto, nombre…).
  });

  tbody.addEventListener('change', function (e) {
    var sel = e.target;
    if (!sel.classList || !sel.classList.contains('inp-cargo')) return;
    var fila = sel.closest('.fila-persona');
    if (!fila) return;
    refrescarPersonas(function () { if (aplicarPersona(fila)) avisarAutoguardado(); });
  });

  // Al volver a esta pestaña (p. ej. desde el admin) se refresca el catálogo.
  window.addEventListener('focus', function () { refrescarPersonas(function () {}); });

  tbody.addEventListener('click', function (e) {
    var btn = e.target.closest('.btn-quitar');
    if (!btn) return;
    var fila = btn.closest('.fila-persona');
    if (fila) { fila.remove(); recalcular(); avisarAutoguardado(); }
  });

  tbody.addEventListener('input', function (e) {
    var inp = e.target;
    if (inp.classList && inp.classList.contains('inp-monto')) { recalcular(); return; }
    // Al elegir a alguien ya registrado se rellenan su DNI y su cargo.
    if (!inp.classList || !inp.classList.contains('inp-nombre')) return;
    var filaNom = inp.closest('.fila-persona');
    if (filaNom) filaNom.dataset.auto = '0';   // lo escribió el usuario: ya no se pisa al cambiar el cargo
    var opt = document.querySelector('#lista-conocidos option[value="' + inp.value.replace(/"/g, '\\"') + '"]');
    if (!opt) return;
    var fila  = inp.closest('.fila-persona');
    var dni   = fila.querySelector('.inp-dni');
    var cargo = fila.querySelector('.inp-cargo');
    if (dni && !dni.value) dni.value = opt.dataset.dni || '';
    if (cargo && opt.dataset.cargo) cargo.value = opt.dataset.cargo;
  });

  recalcular();
})();
