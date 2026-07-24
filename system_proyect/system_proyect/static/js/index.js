/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #index-config (un .js no lo procesa Django). */
const CFG_SYSTEM_PROYECT_INDEX = (function(){
  var d = document.getElementById("index-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
  };
})();

window._PAGE = {
  loginsLabels:   CFG_SYSTEM_PROYECT_INDEX.j0,
  loginsData:     CFG_SYSTEM_PROYECT_INDEX.j1,
  activityLabels: CFG_SYSTEM_PROYECT_INDEX.j2,
  activityData:   CFG_SYSTEM_PROYECT_INDEX.j3,
};
