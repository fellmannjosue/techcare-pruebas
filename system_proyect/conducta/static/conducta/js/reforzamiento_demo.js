/* <--- hecho por claude code (06-nov-2026): maqueta TC-PRY-0005 Convocatoria a reforzamiento, fase 2 (nota opcional, docente de grado, coordinación por grado, V° B° fijo); datos de ejemplo, no guarda nada */
(function(){
  var ASIG=['Inglés','Reading','Matemáticas','Español','Ciencias','Sociales','Computación','Arte'];
  var CFG=document.getElementById('rz-cfg').dataset;
  var MAESTROS=[];try{MAESTROS=JSON.parse(document.getElementById('rz-maestros').textContent);}catch(e){}
  // alumnos de ejemplo: nombre, grado (num), sección, marcas {asignatura: nota}
  var AL=[
    {n:'Mateo Rivera',g:5,s:'A',m:{0:58,2:61,3:''}},
    {n:'Valeria Mejía',g:5,s:'A',m:{0:55,1:62,2:48,3:66,4:59,5:64,6:52,7:60}},
    {n:'Camila Flores',g:5,s:'A',m:{}},
    {n:'Andrés Núñez',g:5,s:'A',m:{2:''}},
    {n:'Lucía Herrera',g:5,s:'A',m:{1:'',4:57}},
    {n:'Diego Castro',g:5,s:'A',m:{}},
    {n:'Sofía Andino',g:2,s:'B',m:{0:'',3:''}},
    {n:'Daniel Zelaya',g:7,s:'A',m:{2:65}}
  ];
  var DOCENTE={};            // docente de grado por 'grado.seccion'
  var SEL=1;                 // alumno cuya carta se ve
  var GRL={1:'1er grado',2:'2do grado',3:'3er grado',4:'4to grado',5:'5to grado',6:'6to grado',7:'7mo grado',8:'8vo grado',9:'9no grado'};
  function n(o){return Object.keys(o).length;}
  function gs(a){return a.g+'.'+a.s;}
  function grado(a){return GRL[a.g].replace(' grado','')+' '+a.s;}
  function coord(a){return (a.g<=3)?{k:'C1',nom:CFG.c1}:{k:'C2',nom:CFG.c2};}
  function esc(x){return String(x).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}

  /* 1 · tabla por grado (5to A) */
  var tm=document.getElementById('tm');
  function drawMaestro(){
    var h='<thead><tr><th>Alumno</th>'+ASIG.map(function(a){return '<th class="c">'+a+'</th>';}).join('')+'<th class="c">Asignaturas</th></tr></thead><tbody>';
    AL.forEach(function(r,i){ if(r.g!==5)return;
      h+='<tr><td>'+esc(r.n)+'</td>'+ASIG.map(function(_,j){var on=(j in r.m);return '<td class="c"><span class="mk'+(on?' on':'')+'" data-i="'+i+'" data-j="'+j+'">'+(on?'✓':'')+'</span>'+(on?'<input class="nota" type="number" min="0" max="100" placeholder="Nota (opcional)" data-i="'+i+'" data-j="'+j+'" value="'+r.m[j]+'">':'')+'</td>';}).join('')+'<td class="c"><span class="cnt'+(n(r.m)>=8?' full':'')+'">'+n(r.m)+'/8</span></td></tr>';
    });
    tm.innerHTML=h+'</tbody>';
  }
  tm.addEventListener('click',function(e){var mk=e.target.closest('.mk');if(!mk)return;var o=AL[+mk.dataset.i].m,j=+mk.dataset.j;if(j in o)delete o[j];else if(n(o)<8)o[j]='';else return;todo();var f=tm.querySelector('input.nota[data-i="'+mk.dataset.i+'"][data-j="'+j+'"]');if(f)f.focus();});
  tm.addEventListener('input',function(e){var f=e.target.closest('input.nota');if(!f)return;var v=f.value;if(v!==''){v=Math.max(0,Math.min(100,+v));}AL[+f.dataset.i].m[+f.dataset.j]=v;drawCoord();carta();});

  /* 2 · panel del coordinador */
  var tc=document.getElementById('tc');
  function opciones(sel){return '<option value="">— Elegir docente de grado —</option>'+MAESTROS.map(function(m){return '<option'+(m===sel?' selected':'')+'>'+esc(m)+'</option>';}).join('');}
  function drawCoord(){
    var h='';
    AL.forEach(function(r,i){ if(!n(r.m))return; var c=coord(r);
      h+='<tr><td>'+esc(r.n)+'</td><td>'+grado(r)+'</td><td class="c"><span class="cnt'+(n(r.m)>=8?' full':'')+'">'+n(r.m)+'</span></td>'+
         '<td><select class="dg" data-gs="'+gs(r)+'">'+opciones(DOCENTE[gs(r)]||'')+'</select></td>'+
         '<td><span class="badge">'+c.k+'</span> '+esc(c.nom)+'</td>'+
         '<td class="c"><button class="btn ver" data-i="'+i+'">Ver carta</button></td></tr>';
    });
    tc.innerHTML=h||'<tr><td colspan="6">Sin convocados.</td></tr>';
  }
  tc.addEventListener('change',function(e){var s=e.target.closest('select.dg');if(!s)return;DOCENTE[s.dataset.gs]=s.value;drawCoord();carta();});
  tc.addEventListener('click',function(e){var b=e.target.closest('button.ver');if(!b)return;SEL=+b.dataset.i;selCarta();tab('carta');});

  /* 4 · carta */
  var psel=document.getElementById('p-sel');
  function selCarta(){var h='';AL.forEach(function(r,i){if(n(r.m))h+='<option value="'+i+'"'+(i===SEL?' selected':'')+'>'+esc(r.n)+' · '+grado(r)+'</option>';});psel.innerHTML=h;carta();}
  psel.addEventListener('change',function(){SEL=+psel.value;carta();});
  function carta(){
    var a=AL[SEL]; if(!a||!n(a.m)){a=AL[1];}
    var s=Object.keys(a.m).map(Number).sort(function(x,y){return x-y;});
    var conNota=s.some(function(j){return a.m[j]!==''&&a.m[j]!==undefined;});
    document.getElementById('p-head').innerHTML='<tr><th>N°</th><th>Asignatura</th>'+(conNota?'<th>Resultado</th>':'')+'</tr>';
    var h='';for(var k=0;k<8;k++){var j=s[k];h+='<tr><td>'+(k+1)+'</td><td>'+(j!==undefined?'<span class="new">'+ASIG[j]+'</span>':'&nbsp;')+'</td>'+(conNota?'<td>'+(j!==undefined&&a.m[j]!==''?'<span class="new">'+a.m[j]+'</span>':'&nbsp;')+'</td>':'')+'</tr>';}
    document.getElementById('p-tab').innerHTML=h;
    document.getElementById('p-alumno').textContent=a.n+' · '+grado(a);
    document.getElementById('p-docente').textContent=DOCENTE[gs(a)]||'';
    document.getElementById('p-coord').textContent=coord(a).nom;
    document.getElementById('p-dir').textContent=CFG.dir;
  }

  /* 3 · fechas */
  var MES=['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'],DIA=['domingo','lunes','martes','miércoles','jueves','viernes','sábado'];
  function d(id){var v=document.getElementById(id).value.split('-');return new Date(+v[0],+v[1]-1,+v[2]);}
  function dd(x){return ('0'+x.getDate()).slice(-2)+' de '+MES[x.getMonth()];}
  function fechas(){try{var a=d('f1'),b=d('f2'),c=d('f3'),e=d('f4');
    document.getElementById('p-fecha').textContent=dd(a)+' de '+a.getFullYear();
    document.getElementById('p-ini').textContent=DIA[b.getDay()]+' '+dd(b);
    document.getElementById('p-ref').textContent=DIA[c.getDay()]+' '+('0'+c.getDate()).slice(-2)+' al '+DIA[e.getDay()]+' '+dd(e);}catch(x){}}
  ['f1','f2','f3','f4'].forEach(function(id){document.getElementById(id).addEventListener('change',fechas);});

  /* pestañas */
  var tabs=document.getElementById('tabs');
  function tab(t){[].forEach.call(tabs.children,function(x){x.classList.toggle('on',x.dataset.t===t);});['maestro','coord','config','carta'].forEach(function(k){document.getElementById('t-'+k).hidden=(k!==t);});}
  tabs.addEventListener('click',function(e){var b=e.target.closest('button');if(b)tab(b.dataset.t);});

  function todo(){drawMaestro();drawCoord();selCarta();}
  todo();fechas();
})();
