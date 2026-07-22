/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #login-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("login-config").dataset;
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

(function(){var s=CFG.j2;var el=document.getElementById('tempSecs');var b=document.querySelector('#loginForm button[type=submit]');if(b)b.disabled=true;var t=setInterval(function(){s--;if(el)el.textContent=s;if(s<=0){clearInterval(t);var w=document.getElementById('tempLock');if(w)w.remove();if(b)b.disabled=false;}},1000);})();

(function(){
              var f=document.getElementById('unlockForm'); if(!f) return;
              f.addEventListener('submit', function(e){
                e.preventDefault();
                var email=(document.getElementById('unlockEmail').value||'').trim();
                var msg=(document.getElementById('unlockMsg').value||'').trim();
                var btn=document.getElementById('unlockBtn');
                var err=document.getElementById('unlockErr'); err.classList.add('d-none');
                if(!email){err.textContent='Ingresa tu correo.';err.classList.remove('d-none');return;}
                btn.disabled=true;
                fetch(CFG.v0,{method:'POST',headers:{'Content-Type':'application/json'},
                  body:JSON.stringify({name:CFG.v1,grade:'Desbloqueo de acceso',email:email,
                    description:'Solicitud de desbloqueo de acceso — usuario: CFG.j1. '+msg})})
                  .then(function(r){return r.json().then(function(d){return {ok:r.ok,d:d};});})
                  .then(function(res){ if(res.ok){document.getElementById('unlockOk').classList.remove('d-none'); btn.classList.add('d-none');}
                    else {err.textContent=(res.d&&(res.d.error||res.d.message))||'No se pudo enviar.'; err.classList.remove('d-none'); btn.disabled=false;} })
                  .catch(function(){err.textContent='Error de red.'; err.classList.remove('d-none'); btn.disabled=false;});
              });
            })();
