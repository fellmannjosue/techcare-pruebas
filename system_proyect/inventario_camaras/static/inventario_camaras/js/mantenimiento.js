/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #mantenimiento-config (un .js no lo procesa Django). */
const CFG_INVENTARIO_CAMARAS_MANTENIMIENTO = (function(){
  var d = document.getElementById("mantenimiento-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
  };
})();

window._IC = {
  csrf: CFG_INVENTARIO_CAMARAS_MANTENIMIENTO.v0,
  camarasPorGrupo: CFG_INVENTARIO_CAMARAS_MANTENIMIENTO.j1,
  editBase: '/inventario-camaras/mantenimiento/',
};
