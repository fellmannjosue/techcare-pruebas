/* <--- hecho por claude code: form de movimiento.
   - Costo unitario: solo entradas y saldo inicial.
   - Motivo de salida: solo cuando la clase es "salida".
   - Precio (venta): solo cuando el motivo es "venta". */
(function () {
  'use strict';
  var clase = document.getElementById('id_clase');
  var tipoSalida = document.getElementById('id_tipo_salida');
  var wrapCosto = document.getElementById('wrapCosto');
  var wrapMotivo = document.getElementById('wrapMotivo');
  var wrapPrecio = document.getElementById('wrapPrecio');
  var costo = document.getElementById('id_costo_unitario');
  var precio = document.getElementById('id_precio_unitario');
  if (!clase) { return; }
  var CON_COSTO = ['saldo_inicial', 'entrada'];

  function toggle() {
    var esEntradaCosto = CON_COSTO.indexOf(clase.value) !== -1;
    var esSalida = clase.value === 'salida';
    if (wrapCosto) { wrapCosto.classList.toggle('d-none', !esEntradaCosto); if (!esEntradaCosto && costo) costo.value = ''; }
    if (wrapMotivo) { wrapMotivo.classList.toggle('d-none', !esSalida); if (!esSalida && tipoSalida) tipoSalida.value = ''; }
    var esVenta = esSalida && tipoSalida && tipoSalida.value === 'venta';
    if (wrapPrecio) { wrapPrecio.classList.toggle('d-none', !esVenta); if (!esVenta && precio) precio.value = ''; }
  }
  clase.addEventListener('change', toggle);
  if (tipoSalida) { tipoSalida.addEventListener('change', toggle); }
  toggle();
})();
