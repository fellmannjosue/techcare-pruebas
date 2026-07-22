/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #inventario_registros-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("inventario_registros-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

window._REG_PAGE = {
  csrf: CFG.v0
};
