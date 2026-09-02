/* <--- hecho por claude code: compra multilínea (agregar/quitar filas + totales en vivo).
   Los porcentajes de impuesto vienen del backend (catálogo), nunca hardcodeados. */
(function () {
  'use strict';
  var body = document.getElementById('lineasBody');
  var tpl = document.getElementById('tplLinea');
  var btnAdd = document.getElementById('btnAddLinea');
  if (!body || !tpl || !btnAdd) { return; }

  var IMPUESTOS = {};
  try {
    JSON.parse(document.getElementById('impuestos-data').textContent).forEach(function (i) {
      IMPUESTOS[String(i.id)] = parseFloat(i.pct) || 0;
    });
  } catch (e) { /* sin impuestos */ }

  // <--- hecho por claude code: Lempiras + separador de millares (L 1,250.00)
  function money(n) {
    return 'L ' + (Math.round(n * 100) / 100).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }

  function calcFila(tr) {
    var cant = parseFloat(tr.querySelector('.in-cant').value) || 0;
    var costo = parseFloat(tr.querySelector('.in-costo').value) || 0;
    var impId = tr.querySelector('.sel-imp').value;
    var sub = cant * costo;
    var pct = IMPUESTOS[impId] || 0;
    var imp = sub * pct / 100;
    tr.querySelector('.sub').textContent = money(sub);
    tr.querySelector('.tot').textContent = money(sub + imp);
    return { sub: sub, imp: imp };
  }

  function calcTotales() {
    var sub = 0, imp = 0;
    body.querySelectorAll('tr.linea').forEach(function (tr) {
      var r = calcFila(tr); sub += r.sub; imp += r.imp;
    });
    document.getElementById('tSubtotal').textContent = money(sub);
    document.getElementById('tImpuesto').textContent = money(imp);
    document.getElementById('tTotal').textContent = money(sub + imp);
  }

  function addLinea() {
    var tr = tpl.content.firstElementChild.cloneNode(true);
    body.appendChild(tr);
    tr.addEventListener('input', calcTotales);
    tr.addEventListener('change', calcTotales);
    tr.querySelector('.btn-del-linea').addEventListener('click', function () {
      tr.remove(); calcTotales();
    });
    calcTotales();
  }

  btnAdd.addEventListener('click', addLinea);
  addLinea();  // primera línea por defecto
})();
