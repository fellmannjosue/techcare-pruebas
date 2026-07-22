/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #informe_form-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("informe_form-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
  };
})();

function cfpSel(sel){
  var inp=document.querySelector('input[name="'+sel.name+'_nueva"]');
  if(!inp)return;
  if(sel.value==='__nueva__'){inp.classList.remove('d-none');inp.required=true;inp.focus();}
  else{inp.classList.add('d-none');inp.required=false;inp.value='';}
}
(function(){
  var INGRESO_NETO = CFG.j0;
  function fmt(n){return (n||0).toLocaleString('es-HN',{minimumFractionDigits:2,maximumFractionDigits:2});}
  function recalc(){
    var tot={}, gran=0;
    document.querySelectorAll('input[data-grupo]').forEach(function(i){
      var g=i.dataset.grupo, v=parseFloat(i.value)||0;
      tot[g]=(tot[g]||0)+v; gran+=v;
    });
    document.querySelectorAll('input[data-total]').forEach(function(i){
      i.value='L '+fmt(tot[i.dataset.total]||0);
    });
    var te=document.getElementById('totalEgresos'); if(te) te.textContent='L '+fmt(gran);
    var ut=document.getElementById('utilidadVal');
    if(ut){var u=INGRESO_NETO-gran; ut.textContent='L '+fmt(u);
      ut.className=(u<0?'text-danger':'text-green');}
  }
  document.addEventListener('input',function(e){ if(e.target&&e.target.dataset.grupo!==undefined) recalc(); });
  recalc();
})();
