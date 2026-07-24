/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #base-config (un .js no lo procesa Django). */
const CFG_BASE = (function(){
  var d = document.getElementById("base-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

if('serviceWorker' in navigator){window.addEventListener('load',function(){navigator.serviceWorker.register('/sw.js',{scope:'/'}).catch(function(){});});}

window.CSRF_TOKEN = CFG_BASE.v0;
