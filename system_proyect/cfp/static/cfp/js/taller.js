/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #taller-config (un .js no lo procesa Django). */
const CFG_TALLER = (function(){
  var d = document.getElementById("taller-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
  };
})();

const CSRF=CFG_TALLER.v0;
const modalEj=new bootstrap.Modal(document.getElementById('modalEj'));
function clearEj(){['pk','no_ejecucion','no_curso','no_contrato','nombre_curso','horas','part_inicial','part_pago','costo_hora','horario','perdida_manual'].forEach(f=>{const el=document.getElementById('ej-'+f);if(el)el.value='';});const ta=document.getElementById('ej-taller_anio');if(ta)ta.value='';}
function openEj(){clearEj();modalEj.show();}
function editEj(id){fetch(`/cfp/ejecucion/${id}/`).then(r=>r.json()).then(d=>{
  for(const k in d){const el=document.getElementById('ej-'+k);if(el)el.value=(d[k]===null?'':d[k]);}
  modalEj.show();
});}
document.getElementById('formEj').addEventListener('submit',function(e){
  e.preventDefault();
  const fd=new FormData(this);fd.append('csrfmiddlewaretoken',CSRF);
  fetch(CFG_TALLER.v1,{method:'POST',body:fd}).then(r=>r.json()).then(d=>{
    if(d.ok){location.reload();}else{alert(d.error||'Error');}
  }).catch(()=>alert('Error de red'));
});
function delEj(id,nombre){
  if(!confirm('¿Eliminar la ejecución '+(nombre||'')+'?'))return;
  const fd=new FormData();fd.append('csrfmiddlewaretoken',CSRF);
  fetch(`/cfp/ejecucion/${id}/eliminar/`,{method:'POST',body:fd}).then(r=>r.json()).then(d=>{if(d.ok)location.reload();else alert('Error');});
}

/* <--- hecho por claude code (06-nov-2026): lápiz de la pérdida → modal pequeño; vacío = automática por deserción */
(function(){
  const el=document.getElementById('modalPerdida'); if(!el)return;
  const modal=new bootstrap.Modal(el), inp=document.getElementById('perd-monto'), err=document.getElementById('perd-err');
  let pk=null;
  document.addEventListener('click',function(e){
    const b=e.target.closest('.cfp-perdida'); if(!b)return;
    pk=b.dataset.pk; inp.value=b.dataset.manual||''; err.classList.add('d-none');
    document.getElementById('perd-curso').textContent=b.dataset.curso||'';
    document.getElementById('perd-auto').textContent='L '+Number(b.dataset.auto||0).toFixed(2);
    modal.show(); setTimeout(()=>inp.focus(),300);
  });
  document.getElementById('formPerdida').addEventListener('submit',function(e){
    e.preventDefault();
    const v=inp.value.trim();
    if(v!==''&&(isNaN(+v)||+v<0)){err.textContent='Escribe un monto válido (0 o más).';err.classList.remove('d-none');return;}
    const fd=new FormData();fd.append('csrfmiddlewaretoken',CSRF);fd.append('perdida',v);
    fetch(`/cfp/ejecucion/${pk}/perdida/`,{method:'POST',body:fd}).then(r=>r.json()).then(d=>{
      if(d.ok){location.reload();}else{err.textContent=d.error||'No se pudo guardar.';err.classList.remove('d-none');}
    }).catch(()=>{err.textContent='Error de red.';err.classList.remove('d-none');});
  });
})();
