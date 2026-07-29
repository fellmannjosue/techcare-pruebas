/* <--- hecho por claude code: planilla de gastos administrativos.
   Reparte en vivo el monto disponible en partes iguales entre las personas
   de la tabla, con la MISMA regla que el backend (el residuo de centavos va
   al último), para que lo que se ve en pantalla sea lo que se guarda. */
const CFG_CFP_PLANILLA = (function () {
  var el = document.getElementById('planilla-config');
  return { aRepartir: el ? parseFloat(el.dataset.v0) || 0 : 0 };
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

  function repartir() {
    var filas = Array.prototype.slice.call(tbody.querySelectorAll('.fila-persona'));
    var n = filas.length;
    if (vacio) vacio.hidden = n > 0;

    if (!n) {
      totalEl.textContent = 'L 0.00';
      resumen.textContent = '';
      return;
    }
    var total = CFG_CFP_PLANILLA.aRepartir;
    var parte = Math.round((total / n) * 100) / 100;
    var suma = 0;
    filas.forEach(function (tr, i) {
      // El último absorbe el residuo del redondeo, igual que en el servidor.
      var monto = (i === n - 1) ? Math.round((total - parte * (n - 1)) * 100) / 100 : parte;
      suma += monto;
      var celda = tr.querySelector('.celda-monto');
      if (celda) celda.textContent = 'L ' + fmt(monto);
    });
    totalEl.textContent = 'L ' + fmt(Math.round(suma * 100) / 100);
    resumen.textContent = n + (n === 1 ? ' persona · ' : ' personas · ') +
                          'L ' + fmt(parte) + ' cada una';
  }

  // <--- hecho por claude code: agregar/quitar filas no dispara 'input', así que
  // hay que avisarle al autoguardado a mano.
  function avisarAutoguardado() {
    if (typeof window.tcAutoguardar === 'function') window.tcAutoguardar();
  }

  document.getElementById('btn-agregar').addEventListener('click', function () {
    tbody.appendChild(tpl.content.cloneNode(true));
    repartir();
    var ultimos = tbody.querySelectorAll('.inp-nombre');
    if (ultimos.length) ultimos[ultimos.length - 1].focus();
    // No se autoguarda al agregar: la fila aún no tiene nombre y el servidor
    // la descartaría. Se guardará en cuanto se escriba el nombre.
  });

  tbody.addEventListener('click', function (e) {
    var btn = e.target.closest('.btn-quitar');
    if (!btn) return;
    var fila = btn.closest('.fila-persona');
    if (fila) { fila.remove(); repartir(); avisarAutoguardado(); }
  });

  // Al elegir a alguien ya registrado se rellenan su DNI y su cargo.
  tbody.addEventListener('input', function (e) {
    var inp = e.target;
    if (!inp.classList || !inp.classList.contains('inp-nombre')) return;
    var opt = document.querySelector('#lista-conocidos option[value="' + inp.value.replace(/"/g, '\\"') + '"]');
    if (!opt) return;
    var fila = inp.closest('.fila-persona');
    var dni = fila.querySelector('.inp-dni');
    var cargo = fila.querySelector('.inp-cargo');
    if (dni && !dni.value) dni.value = opt.dataset.dni || '';
    if (cargo && opt.dataset.cargo) cargo.value = opt.dataset.cargo;
  });

  repartir();
})();
