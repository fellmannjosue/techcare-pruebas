/* <--- hecho por claude code: autollena el precio del producto y calcula el total de la venta */
(function () {
  var cfg = document.getElementById('venta-precios');
  var prod = document.getElementById('id_producto');
  var precioEl = document.getElementById('id_precio_unitario');
  var cantEl = document.getElementById('id_cantidad');
  var totalEl = document.getElementById('venta-total');
  if (!cfg || !prod) return;

  var precios = {};
  try { precios = JSON.parse(cfg.dataset.precios || '{}'); } catch (e) { precios = {}; }

  function precioDeProducto() {
    var p = precios[prod.value];
    return (p === undefined || p === null || p === '') ? '' : p;
  }

  function autollenar() {
    // solo rellena si el usuario no escribió un precio manual
    if (precioEl && !precioEl.value) {
      var p = precioDeProducto();
      if (p !== '') precioEl.value = p;
    }
    calcularTotal();
  }

  function calcularTotal() {
    if (!totalEl) return;
    var cant = parseFloat(cantEl && cantEl.value) || 0;
    var precio = parseFloat(precioEl && precioEl.value);
    if (isNaN(precio)) { var p = precioDeProducto(); precio = parseFloat(p) || 0; }
    var total = cant * precio;
    totalEl.textContent = 'L ' + (isNaN(total) ? 0 : total).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
  }

  prod.addEventListener('change', function () {
    if (precioEl) precioEl.value = '';   // al cambiar producto, recargar su precio
    autollenar();
  });
  if (cantEl) cantEl.addEventListener('input', calcularTotal);
  if (precioEl) precioEl.addEventListener('input', calcularTotal);
  autollenar();
})();
