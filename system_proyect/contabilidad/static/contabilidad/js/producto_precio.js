/* <--- hecho por claude code: ISV 15% + precio final automáticos; autollena el precio del proveedor seleccionado */
(function () {
  var venta = document.getElementById('id_precio_venta');
  var prov = document.getElementById('id_proveedor');
  var precioProv = document.getElementById('id_precio_proveedor');
  var isvOut = document.getElementById('isv-out');
  var finalOut = document.getElementById('final-out');
  var cfg = document.getElementById('precios-prov');
  if (!venta || !isvOut || !finalOut) return;

  var precios = {};
  try { precios = JSON.parse(cfg && cfg.dataset.precios || '{}'); } catch (e) { precios = {}; }

  function fmt(n) { return 'L ' + (isNaN(n) ? 0 : n).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2}); }

  function calcular() {
    var p = parseFloat(venta.value) || 0;
    var isv = p * 0.15 / 1.15;   // ISV incluido dentro del precio de venta
    isvOut.textContent = fmt(isv);
    finalOut.textContent = fmt(p);   // precio final = precio de venta
  }

  // Al elegir proveedor, trae su precio ya registrado (si existe)
  if (prov && precioProv) {
    prov.addEventListener('change', function () {
      var val = precios[prov.value];
      precioProv.value = (val === undefined || val === null) ? '' : val;
    });
  }

  venta.addEventListener('input', calcular);
  calcular();
})();
