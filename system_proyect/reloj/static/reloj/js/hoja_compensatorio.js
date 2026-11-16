/* <--- hecho por claude code (16-nov-2026): hoja «Cálculo compensatorio» por empleado — autoguardado y fórmula de derecho a días */
(function () {
  var cfg = document.getElementById('hoja-config');
  if (!cfg) return;
  var URL_HOJA = cfg.dataset.url, CSRF_HOJA = cfg.dataset.csrf, ANIO_HOJA = cfg.dataset.anio;
  var EDITA = cfg.dataset.edit === '1';

  function num(v) { var n = parseFloat(String(v || '').replace(',', '.')); return isNaN(n) ? 0 : n; }
  function fmt(n) { return Math.round(n * 1000) / 1000; }
  function fecha(v) { if (!v || parseInt(v.slice(0, 4), 10) < 2000) return null; var d = new Date(v + 'T00:00:00'); return isNaN(d) ? null : d; }

  // Fórmula 1: años cumplidos entre ingreso y corte → 1=10, 2=12, 3=15, 4 o más=20 (menos de 1 = 0)
  function derecho(ing, corte) {
    if (!ing || !corte || corte < ing) return 0;
    var a = corte.getFullYear() - ing.getFullYear();
    if (corte.getMonth() < ing.getMonth() || (corte.getMonth() === ing.getMonth() && corte.getDate() < ing.getDate())) a--;
    if (a < 1) return 0;
    return a === 1 ? 10 : a === 2 ? 12 : a === 3 ? 15 : 20;
  }

  function dmY(d) { return d ? ('0' + d.getDate()).slice(-2) + '/' + ('0' + (d.getMonth() + 1)).slice(-2) + '/' + String(d.getFullYear()).slice(-2) : '—'; }

  function recalcular(hoja) {
    var ing = fecha(hoja.querySelector('[data-k=fecha_ingreso]').value);
    var corte = fecha(hoja.querySelector('[data-k=fecha_corte]').value);
    hoja.querySelector('.hc-derecho').textContent = derecho(ing, corte);
    var rango = hoja.querySelector('.hc-rango');
    if (rango) rango.textContent = dmY(ing) + ' - ' + dmY(corte);
    // Fórmulas (usuario 16-nov-2026): Saldo de vacación = Derecho − Deuda; Permiso = suma de los días elegidos del detalle;
    // Saldo vacación (año actual) = Saldo de vacación − Permiso
    var der = derecho(ing, corte);
    var saldoAnt = der - num(hoja.querySelector('[data-k=deuda]').value);
    hoja.querySelector('[data-k=saldo_ant]').value = fmt(saldoAnt);
    var filas = hoja.querySelectorAll('.hc-det-fila');
    // Detalle: horas = días × 8; Días que necesita = suma de los días del detalle (cierre ANA)
    var totDias = 0, hayDias = false;
    filas.forEach(function (tr) {
      var dv = tr.querySelector('[data-d=dias]').value;
      tr.querySelector('[data-d=horas]').value = dv.trim() === '' ? '' : fmt(num(dv) * 8);
      if (dv.trim() !== '') hayDias = true;
      totDias += num(dv);
    });
    hoja.querySelector('[data-k=dias_necesita]').value = hayDias ? fmt(totDias) : '';
    var perm = 0;
    hoja._sel = (hoja._sel || []).filter(function (i) { return i < filas.length; });
    hoja._sel.forEach(function (i) { perm += num(filas[i].querySelector('[data-d=dias]').value); });
    hoja.querySelector('[data-k=permiso_vac]').value = hoja._sel.length ? fmt(perm) : '';
    hoja.querySelector('.hc-perm-val').textContent = hoja._sel.length ? fmt(perm) : '—';
    hoja.querySelector('[data-k=saldo_act]').value = fmt(saldoAnt - perm);
    // Días que debe compensar = Días que necesita − Saldo vacación; Horas a compensar = días × 8
    var debe = (hayDias ? totDias : 0) - (saldoAnt - perm);
    hoja.querySelector('[data-k=dias_compensar]').value = fmt(debe);
    hoja.querySelector('[data-k=horas_compensar]').value = fmt(debe * 8);
    pintarMenu(hoja);
    ['dias', 'horas'].forEach(function (k) {
      var t = 0, hay = false;
      hoja.querySelectorAll('.hc-det-fila [data-d=' + k + ']').forEach(function (i) { if (i.value.trim() !== '') hay = true; t += num(i.value); });
      hoja.querySelector('[data-tot=' + k + ']').textContent = hay ? fmt(t) : '';
    });
  }

  // Lista desplegable de selección múltiple con las filas del detalle (concepto + días)
  function pintarMenu(hoja) {
    var menu = hoja.querySelector('.hc-perm-menu');
    if (!menu) return;
    menu.innerHTML = '';
    hoja.querySelectorAll('.hc-det-fila').forEach(function (tr, i) {
      var concepto = tr.querySelector('[data-d=concepto]').value || ('Fila ' + (i + 1));
      var dias = tr.querySelector('[data-d=dias]').value;
      var lab = document.createElement('label');
      lab.className = 'dropdown-item d-flex align-items-center gap-2';
      var cb = document.createElement('input');
      cb.type = 'checkbox'; cb.className = 'form-check-input m-0'; cb.checked = hoja._sel.indexOf(i) !== -1; cb.disabled = !EDITA;
      cb.addEventListener('change', function () {
        hoja._sel = hoja._sel.filter(function (x) { return x !== i; });
        if (cb.checked) hoja._sel.push(i);
        hoja._sel.sort(function (a, b) { return a - b; });
        recalcular(hoja);
        guardar(hoja, hoja.querySelector('.hc-perm-btn'));
      });
      var t = document.createElement('span'); t.className = 'flex-fill'; t.textContent = concepto;
      var n = document.createElement('span'); n.className = 'text-muted ms-3'; n.textContent = dias || '0';
      lab.appendChild(cb); lab.appendChild(t); lab.appendChild(n);
      menu.appendChild(lab);
    });
  }

  function datosDe(hoja) {
    var d = {};
    hoja.querySelectorAll('[data-k]').forEach(function (i) { d[i.dataset.k] = i.value; });
    d.detalle = [];
    hoja.querySelectorAll('.hc-det-fila').forEach(function (tr) {
      d.detalle.push({
        concepto: tr.querySelector('[data-d=concepto]').value,
        dias: tr.querySelector('[data-d=dias]').value,
        horas: tr.querySelector('[data-d=horas]').value
      });
    });
    d.permiso_sel = hoja._sel || [];
    return d;
  }

  function guardar(hoja, input) {
    var estado = hoja.querySelector('.hc-estado');
    fetch(URL_HOJA, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_HOJA },
      body: JSON.stringify({ emp_code: hoja.dataset.emp, anio: ANIO_HOJA, datos: datosDe(hoja) })
    }).then(function (r) { return r.json(); }).then(function (j) {
      input.classList.remove('hc-ok', 'hc-err');
      if (j.ok) {
        input.classList.add('hc-ok');
        setTimeout(function () { input.classList.remove('hc-ok'); }, 1200);
        if (estado) estado.textContent = 'Guardado ' + new Date().toLocaleTimeString();
      } else {
        input.classList.add('hc-err');
        if (estado) estado.textContent = j.error || 'No se pudo guardar.';
      }
    }).catch(function () {
      input.classList.add('hc-err');
      if (estado) estado.textContent = 'Error de conexión: no se guardó.';
    });
  }

  document.querySelectorAll('.hc-hoja').forEach(function (hoja) {
    var selTxt = (hoja.querySelector('.hc-perm-sel') || {}).textContent || '';
    hoja._sel = selTxt.split(',').filter(function (x) { return x.trim() !== ''; }).map(Number);
    recalcular(hoja);
    hoja.querySelectorAll('.hc-in').forEach(function (i) {
      if (i.classList.contains('hc-calc') || i.tagName === 'BUTTON') return;
      if (!EDITA) { i.readOnly = true; if (i.type === 'date') i.disabled = true; return; }
      i.addEventListener('input', function () { recalcular(hoja); });
      i.addEventListener('change', function () {
        if (i.type === 'date' && i.value && parseInt(i.value.slice(0, 4), 10) < 2000) return;  // mientras escribe el año
        recalcular(hoja);
        guardar(hoja, i);
      });
    });
  });
})();
