/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #revision_comentarios-config (un .js no lo procesa Django). */
const CFG_REVISION_COMENTARIOS = (function(){
  var d = document.getElementById("revision_comentarios-config").dataset;
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

window._PAGE = Object.assign(window._PAGE || {}, {
  csrf:                CFG_REVISION_COMENTARIOS.v0,
  urlComentario:       CFG_REVISION_COMENTARIOS.v1,
  urlEliminarComentario:CFG_REVISION_COMENTARIOS.v2,
});
