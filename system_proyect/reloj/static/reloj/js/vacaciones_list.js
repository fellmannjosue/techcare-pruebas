/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #vacaciones_list-config (un .js no lo procesa Django). */
const CFG_VACACIONES_LIST = (function(){
  var d = document.getElementById("vacaciones_list-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
  };
})();

window._PAGE = {
  csrf:      CFG_VACACIONES_LIST.v0,
  urlSave:   CFG_VACACIONES_LIST.v1,
  urlEditar: CFG_VACACIONES_LIST.v2
};
