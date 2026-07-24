/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #form_agenda-config (un .js no lo procesa Django). */
const CFG_FORM_AGENDA = (function(){
  var d = document.getElementById("form_agenda-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

(function(){
  var end=new Date(CFG_FORM_AGENDA.v0).getTime();
  var el=document.getElementById('cd-timer');
  function tick(){
    var diff=end-Date.now();
    if(diff<=0){ document.getElementById('cd-banner').className='alert alert-danger mb-3';
      el.parentElement.innerHTML='<strong>El llenado de agendas se ha cerrado.</strong> Recarga la página.'; return; }
    var h=Math.floor(diff/3.6e6), m=Math.floor(diff%3.6e6/6e4), s=Math.floor(diff%6e4/1000);
    el.textContent=(h<10?'0':'')+h+':'+(m<10?'0':'')+m+':'+(s<10?'0':'')+s;
    setTimeout(tick,1000);
  }
  tick();
})();

(function(){
          var ini=document.getElementById('ag_semana_inicio'),
              fin=document.getElementById('ag_semana_fin');
          if(!ini||!fin)return;
          function sync(){
            fin.min=ini.value||'';
            if(fin.value && ini.value && fin.value<ini.value){
              fin.setCustomValidity('La fecha final no puede ser anterior a la de inicio.');
            } else { fin.setCustomValidity(''); }
          }
          ini.addEventListener('change',sync);
          fin.addEventListener('change',sync);
          sync();
        })();
