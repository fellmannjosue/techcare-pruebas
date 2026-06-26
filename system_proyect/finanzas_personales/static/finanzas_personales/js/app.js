'use strict';
/* ===================== Ledger · Finanzas (SPA) ===================== */
const API = '/finanzas/api/';
let state = {categories:[],accounts:[],transactions:[],pendings:[],budgets:[],quickEntries:[],recurrents:[],goals:[],settings:{currency:'L',theme:'dark'}};
let current = 'dashboard';
let charts = {};
const COLORS = ['#2A7A4F','#349e66','#43b581','#7cc66a','#5c8c3a','#a8c43a',
  '#C9A84C','#e0b73a','#D4843C','#e07a2f','#cf5a2a','#B84040','#e1574c','#d9415f',
  '#d96aa0','#c264b8','#9b59b6','#7B5EA7','#6c5ce7','#5a6fd6','#3A6FA8','#3a8fb7',
  '#2f9e8f','#1abc9c','#16a085','#0fb9b1','#8A6D3B','#a0522d','#7f8c8d','#566573',
  '#2c3e50','#e84393','#fd79a8','#e67e22','#f39c12','#27ae60'];
const ICONS = ['ti-tag','ti-cash','ti-businessplan','ti-shopping-cart','ti-car','ti-bolt','ti-home','ti-heartbeat',
  'ti-device-gamepad','ti-plane','ti-coffee','ti-shirt','ti-book','ti-gift','ti-paw','ti-phone','ti-wifi','ti-pizza',
  'ti-medicine-syrup','ti-school','ti-building-bank','ti-credit-card','ti-pig-money','ti-wallet','ti-coin','ti-receipt',
  // Música / audio
  'ti-music','ti-brand-spotify','ti-headphones','ti-microphone','ti-playlist','ti-disc','ti-device-speaker',
  // IA / tecnología
  'ti-robot','ti-brain','ti-sparkles','ti-cpu','ti-bulb','ti-server','ti-cloud','ti-world','ti-code',
  // Juegos
  'ti-device-gamepad-2','ti-dice','ti-puzzle','ti-ball-football','ti-chess','ti-trophy',
  // Chats / mensajería / redes
  'ti-message-circle','ti-messages','ti-brand-whatsapp','ti-mail','ti-send','ti-users','ti-heart',
  // Streaming / video / foto
  'ti-movie','ti-device-tv','ti-brand-youtube','ti-player-play','ti-camera','ti-photo','ti-ticket',
  // Comida / bebida
  'ti-burger','ti-meat','ti-salad','ti-cake','ti-beer','ti-glass','ti-bottle','ti-cheese','ti-ice-cream',
  // Transporte / viajes
  'ti-bus','ti-motorbike','ti-gas-station','ti-bed','ti-map-pin','ti-luggage',
  // Servicios / hogar / salud
  'ti-droplet','ti-flame','ti-tools','ti-key','ti-shield','ti-stethoscope','ti-pill','ti-tooth','ti-dog','ti-cat',
  // Trabajo / dinero
  'ti-briefcase','ti-building-store','ti-shopping-bag','ti-basket','ti-report-money','ti-moneybag','ti-discount','ti-currency-dollar','ti-calendar','ti-star'];
const TIPO_CUENTA = {cash:'Efectivo',bank:'Banco',card:'Tarjeta',savings:'Ahorro',loan:'Préstamo',other:'Otro'};
const FREQ = {weekly:'Semanal',biweekly:'Quincenal',monthly:'Mensual',yearly:'Anual'};
const MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];

/* ---------- helpers ---------- */
function sym(){return state.settings.currency||'L';}
function money(n){return sym()+' '+Number(n||0).toLocaleString('es-HN',{minimumFractionDigits:2,maximumFractionDigits:2});}
function moneyS(n,s){return (s||sym())+' '+Number(n||0).toLocaleString('es-HN',{minimumFractionDigits:2,maximumFractionDigits:2});}
function accCur(id){const a=acc(id);return a&&a.currency?a.currency:sym();}
function moneyA(n,accId){return moneyS(n,accCur(accId));}
function today(){return new Date().toISOString().slice(0,10);}
function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function cat(id){return state.categories.find(c=>c.id===String(id));}
function acc(id){return state.accounts.find(a=>a.id===String(id));}
function fmtDate(d){const x=new Date(d+'T00:00:00');return x.toLocaleDateString('es-HN',{day:'2-digit',month:'short',year:'numeric'});}
function monthKey(d){return (d||'').slice(0,7);}
function curMonth(){return today().slice(0,7);}
function $(id){return document.getElementById(id);}

async function api(method,path,data){
  const o={method,headers:{'Content-Type':'application/json'}};
  if(method!=='GET'){o.headers['X-CSRFToken']=window.CSRF;}
  if(data!==undefined)o.body=JSON.stringify(data);
  const r=await fetch(API+path,o);
  if(!r.ok){let e='Error';try{e=(await r.json()).error||e;}catch(_){}toast(e);throw new Error(e);}
  return r.status===204?{}:r.json();
}
function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('show');clearTimeout(t._t);t._t=setTimeout(()=>t.classList.remove('show'),2200);}
async function apiUpload(path,fd){
  const r=await fetch(API+path,{method:'POST',headers:{'X-CSRFToken':window.CSRF},body:fd});
  if(!r.ok){let e='Error';try{e=(await r.json()).error||e;}catch(_){}toast(e);throw new Error(e);}
  return r.json();
}

/* ---------- theme / sidebar ---------- */
function applyTheme(){document.documentElement.setAttribute('data-theme',state.settings.theme);
  $('themeIcon').className='ti '+(state.settings.theme==='dark'?'ti-sun':'ti-moon');}
async function toggleTheme(){state.settings.theme=state.settings.theme==='dark'?'light':'dark';applyTheme();
  await api('POST','configuracion/',{theme:state.settings.theme});render();}
function toggleSidebar(){$('sidebar').classList.toggle('open');}

/* ---------- navigation ---------- */
const TITLES={dashboard:['Dashboard','Resumen financiero'],movements:['Movimientos','Ingresos, gastos y transferencias'],
  accounts:['Cuentas','Tus billeteras y saldos'],recurrents:['Recurrentes','Movimientos automáticos'],
  pendings:['Pendientes','Por cobrar y por pagar'],budgets:['Presupuestos','Control de gastos por categoría'],
  goals:['Metas de Ahorro','Tus objetivos'],reports:['Reportes','Análisis y exportación'],
  categories:['Categorías','Organiza tus movimientos'],settings:['Configuración','Preferencias y respaldo']};
function goTo(id){
  current=id;
  document.querySelectorAll('.nav a').forEach(a=>a.classList.toggle('active',a.dataset.go===id));
  document.querySelectorAll('.section').forEach(s=>s.classList.remove('active'));
  $('sec-'+id).classList.add('active');
  $('pageTitle').textContent=TITLES[id][0];$('pageSub').textContent=TITLES[id][1];
  $('sidebar').classList.remove('open');
  render();
}
function render(){({dashboard:renderDashboard,movements:renderMovements,accounts:renderAccounts,recurrents:renderRecurrents,
  pendings:renderPendings,budgets:renderBudgets,goals:renderGoals,reports:renderReports,categories:renderCategories,
  settings:renderSettings}[current])();}

/* ---------- selects ---------- */
function catOptions(type,sel){return '<option value="">— Categoría —</option>'+state.categories.filter(c=>c.type===type)
  .map(c=>`<option value="${c.id}" ${c.id===String(sel)?'selected':''}>${esc(c.name)}</option>`).join('');}
function accOptions(sel,placeholder){return `<option value="">${placeholder||'— Cuenta —'}</option>`+state.accounts.filter(a=>!a.archived)
  .map(a=>`<option value="${a.id}" ${a.id===String(sel)?'selected':''}>${esc(a.name)}</option>`).join('');}

/* ======================= QUICK ACCESS ======================= */
function qaChip(q){
  const sign=q.type==='income'?'+':'−';
  return `<div class="qa" onclick="execQE('${q.id}')" title="Registrar al instante">
    <button class="qa-del" onclick="event.stopPropagation();delQE('${q.id}')"><i class="ti ti-x"></i></button>
    <div class="qa-ic" style="background:${q.color}"><i class="ti ${q.icon}"></i></div>
    <div class="qa-nm">${esc(q.name)}</div>
    <div class="qa-amt ${q.type==='income'?'pos':'neg'}">${sign}${money(q.amount)}</div></div>`;
}
async function execQE(id){await api('POST','quick-entries/'+id+'/ejecutar/',{});await reload();toast('Movimiento registrado');}
let qaType='expense',qaColor=COLORS[0],qaIcon='ti-bolt';
function openQE(){qaType='expense';qaColor=COLORS[0];qaIcon='ti-bolt';
  openModal('Nuevo acceso rápido',`
    <div class="seg" style="margin-bottom:14px">
      <button id="qgIn" onclick="setQEType('income')">Ingreso</button>
      <button id="qgOut" onclick="setQEType('expense')">Gasto</button></div>
    <div class="fld"><label>Nombre</label><input id="qeName" class="inp" placeholder="Ej. Café"></div>
    <div class="row2"><div class="fld"><label>Monto</label><input id="qeAmt" class="inp" type="number" step="0.01" placeholder="0.00"></div>
      <div class="fld"><label>Cuenta</label><select id="qeAcc" class="inp">${accOptions('')}</select></div></div>
    <div class="fld"><label>Categoría</label><select id="qeCat" class="inp">${catOptions(qaType,'')}</select></div>
    <div class="fld"><label>Color</label><div class="swatches" id="qeSw">${COLORS.map(c=>`<div class="swatch ${c===qaColor?'sel':''}" style="background:${c}" onclick="pickQEColor('${c}')"></div>`).join('')}</div></div>
    <div class="fld"><label>Ícono</label><div class="icons" id="qeIc">${ICONS.map(i=>`<div class="ic ${i===qaIcon?'sel':''}" onclick="pickQEIcon('${i}')"><i class="ti ${i}"></i></div>`).join('')}</div></div>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="saveQE()">Guardar</button>`);
  setQEType('expense');
}
function setQEType(tp){qaType=tp;$('qgIn').className=tp==='income'?'on-in':'';$('qgOut').className=tp==='expense'?'on-out':'';
  $('qeCat').innerHTML=catOptions(tp,$('qeCat').value);}
function pickQEColor(c){qaColor=c;document.querySelectorAll('#qeSw .swatch').forEach(s=>s.classList.toggle('sel',s.style.background===hex2rgb(c)));}
function pickQEIcon(i){qaIcon=i;document.querySelectorAll('#qeIc .ic').forEach(e=>e.classList.remove('sel'));event.currentTarget.classList.add('sel');}
async function saveQE(){const name=$('qeName').value.trim();const amt=parseFloat($('qeAmt').value);
  if(!name)return shake('qeName');if(!amt||amt<=0)return shake('qeAmt');
  await api('POST','quick-entries/',{name,amount:amt,type:qaType,categoryId:$('qeCat').value,accountId:$('qeAcc').value,color:qaColor,icon:qaIcon});
  closeModal();await reload();toast('Acceso rápido creado');}
async function delQE(id){if(!confirm('¿Eliminar este acceso rápido?'))return;await api('DELETE','quick-entries/'+id+'/');await reload();toast('Eliminado');}

/* ======================= DASHBOARD ======================= */
function catExcluded(t){const c=cat(t.categoryId);return !!(c&&c.exclude);}
let accFilter='all';
function inScope(t){return accFilter==='all'||t.accountId===String(accFilter)||(t.type==='transfer'&&t.toAccountId===String(accFilter));}
function scopeSym(){if(accFilter!=='all'){const a=acc(accFilter);return a&&a.currency?a.currency:sym();}return sym();}
function setAccFilter(v){accFilter=v;render();}
function accFilterSel(){return `<select class="inp acc-filter" onchange="setAccFilter(this.value)">
    <option value="all" ${accFilter==='all'?'selected':''}>Todas las cuentas</option>
    ${state.accounts.filter(a=>!a.archived).map(a=>`<option value="${a.id}" ${accFilter===String(a.id)?'selected':''}>${esc(a.name)}</option>`).join('')}
  </select>`;}
function sumMonth(type,mk){return state.transactions.filter(t=>t.type===type&&monthKey(t.date)===mk&&!catExcluded(t)&&inScope(t)).reduce((s,t)=>s+t.amount,0);}
function patrimonio(){
  if(accFilter!=='all'){const a=acc(accFilter);return a?(a.type==='loan'?-(a.balance||0):(a.balance||0)):0;}
  return state.accounts.filter(a=>!a.archived)
    .reduce((s,a)=>s+(a.type==='loan'? -(a.balance||0) : (a.balance||0)),0);}

function renderDashboard(){
  const mk=curMonth();
  const inc=sumMonth('income',mk),exp=sumMonth('expense',mk),bal=inc-exp;
  const ss=scopeSym();
  const recent=[...state.transactions].filter(inScope).slice(0,7);
  $('sec-dashboard').innerHTML=`
    <div class="card" style="margin-bottom:16px;padding:12px 16px"><div class="hd mb0" style="margin-bottom:0;align-items:center">
      <h3 style="margin:0"><i class="ti ti-wallet" style="color:var(--brand)"></i> Cuenta</h3>
      <div style="max-width:260px;width:100%">${accFilterSel()}</div></div></div>
    <div class="grid g-4" style="margin-bottom:18px">
      ${kpi('k-net','ti-businessplan',accFilter==='all'?'Patrimonio total':'Saldo de la cuenta',moneyS(patrimonio(),ss))}
      ${kpi('k-in','ti-trending-up','Ingresos del mes',moneyS(inc,ss))}
      ${kpi('k-out','ti-trending-down','Gastos del mes',moneyS(exp,ss))}
      ${kpi('k-bal','ti-scale','Balance del mes',moneyS(bal,ss),bal>=0?'pos':'neg')}
    </div>
    <div class="card" style="margin-bottom:18px"><div class="hd"><h3><i class="ti ti-bolt" style="color:var(--gold)"></i> Accesos rápidos</h3>
      <button class="btn btn-soft btn-sm" onclick="openQE()"><i class="ti ti-plus"></i> Agregar</button></div>
      <div class="qa-wrap">${state.quickEntries.map(qaChip).join('')}
        <button class="qa qa-add" onclick="openQE()"><i class="ti ti-plus"></i><span>Agregar</span></button></div>
    </div>
    <div class="grid g-2" style="margin-bottom:18px">
      <div class="card"><div class="hd"><h3>Ingresos vs Gastos</h3><span class="badge b-in">6 meses</span></div>
        <div class="chartbox"><canvas id="chTrend"></canvas></div></div>
      <div class="card"><div class="hd"><h3>Gastos por categoría</h3><span class="badge b-out">Este mes</span></div>
        <div class="chartbox"><canvas id="chCat"></canvas></div></div>
    </div>
    <div class="grid g-2">
      <div class="card"><div class="hd"><h3>Movimientos recientes</h3><button class="btn btn-soft btn-sm" onclick="goTo('movements')">Ver todos</button></div>
        <div>${recent.length?recent.map(t=>txnRow(t,false)).join(''):emptyBox('ti-inbox','Sin movimientos')}</div></div>
      <div class="card"><div class="hd"><h3>Mis cuentas</h3><button class="btn btn-soft btn-sm" onclick="goTo('accounts')">Gestionar</button></div>
        <div>${state.accounts.filter(a=>!a.archived).length?state.accounts.filter(a=>!a.archived).map(accRow).join(''):emptyBox('ti-wallet','Sin cuentas')}</div></div>
    </div>`;
  drawTrend();drawCat();
}
function kpi(cls,icon,label,val,tone){return `<div class="card kpi ${cls}"><div class="ic"><i class="ti ${icon}"></i></div>
  <div class="lbl">${label}</div><div class="val ${tone||''}">${val}</div></div>`;}
function emptyBox(icon,txt){return `<div class="empty"><i class="ti ${icon}"></i>${txt}</div>`;}
function accRow(a){return `<div class="row-item"><div class="av" style="background:${a.color}"><i class="ti ${a.icon}"></i></div>
  <div><div class="nm">${esc(a.name)}</div><div class="mt">${TIPO_CUENTA[a.type]||''}</div></div>
  <div class="amt ${a.balance<0?'neg':'pos'}">${moneyS(a.balance,a.currency)}</div></div>`;}

function txnRow(t,tools,sel){
  const c=cat(t.categoryId),a=acc(t.accountId);
  const isT=t.type==='transfer';
  const color=isT?'#3a8fb7':(c?c.color:(t.type==='income'?'#2fae6b':'#e1574c'));
  const icon=isT?'ti-arrows-exchange':(c?c.icon:(t.type==='income'?'ti-arrow-down-left':'ti-arrow-up-right'));
  let sub;
  if(isT){const a2=acc(t.toAccountId);sub=`${a?esc(a.name):'?'} → ${a2?esc(a2.name):'?'}`;}
  else{sub=`${c?esc(c.name):'Sin categoría'}${a?' · '+esc(a.name):''}`;}
  const sign=t.type==='income'?'+':(t.type==='expense'?'−':'');
  const amtCls=isT?'tr':(t.type==='income'?'pos':'neg');
  return `<div class="row-item ${sel&&mvSel.has(t.id)?'row-sel':''}">
    ${sel?`<input type="checkbox" class="row-chk" ${mvSel.has(t.id)?'checked':''} onclick="toggleSel('${t.id}')">`:''}
    <div class="av" style="background:${color}"><i class="ti ${icon}"></i></div>
    <div><div class="nm">${esc(t.description||(c?c.name:(isT?'Transferencia':'Movimiento')))}</div><div class="mt">${sub} · ${fmtDate(t.date)}</div></div>
    <div class="amt ${amtCls}">${sign}${moneyA(t.amount,t.accountId)}</div>
    ${tools?`<div class="tools">
      ${!isT?`<select class="row-cat" title="Categoría" onchange="quickCat('${t.id}',this.value)">${catOptions(t.type,t.categoryId)}</select>`:''}
      <button class="tbtn" onclick="openTxn('${t.id}')"><i class="ti ti-pencil"></i></button>
      <button class="tbtn del" onclick="delTxn('${t.id}')"><i class="ti ti-trash"></i></button></div>`:''}</div>`;
}

function lastMonths(n){const arr=[];const d=new Date();d.setDate(1);
  for(let i=n-1;i>=0;i--){const x=new Date(d.getFullYear(),d.getMonth()-i,1);arr.push({mk:x.toISOString().slice(0,7),label:MESES[x.getMonth()]});}return arr;}
function drawTrend(){
  const ms=lastMonths(6);
  const inc=ms.map(m=>sumMonth('income',m.mk)),exp=ms.map(m=>sumMonth('expense',m.mk));
  charts.trend&&charts.trend.destroy();
  charts.trend=new Chart($('chTrend'),{type:'bar',data:{labels:ms.map(m=>m.label),datasets:[
    {label:'Ingresos',data:inc,backgroundColor:'#2fae6b',borderRadius:6,maxBarThickness:26},
    {label:'Gastos',data:exp,backgroundColor:'#e1574c',borderRadius:6,maxBarThickness:26}]},
    options:chartOpts(true)});
}
function drawCat(){
  const mk=curMonth(),map={};
  state.transactions.filter(t=>t.type==='expense'&&monthKey(t.date)===mk&&!catExcluded(t)&&inScope(t)).forEach(t=>{const c=cat(t.categoryId);const k=c?c.name:'Sin categoría';
    map[k]=map[k]||{v:0,color:c?c.color:'#888'};map[k].v+=t.amount;});
  const keys=Object.keys(map);
  charts.cat&&charts.cat.destroy();
  if(!keys.length){const ctx=$('chCat').getContext('2d');ctx.clearRect(0,0,999,999);
    $('chCat').parentElement.innerHTML=emptyBox('ti-chart-donut','Sin gastos este mes');return;}
  charts.cat=new Chart($('chCat'),{type:'doughnut',data:{labels:keys,datasets:[{data:keys.map(k=>map[k].v),
    backgroundColor:keys.map(k=>map[k].color),borderWidth:0}]},options:{cutout:'62%',plugins:{legend:{position:'right',
    labels:{color:gridColor(true),boxWidth:12,padding:10,font:{size:12}}},tooltip:{callbacks:{label:c=>' '+money(c.raw)}}}}});
}
function gridColor(text){const dark=state.settings.theme==='dark';return dark?(text?'#cbd5e1':'#26303d'):(text?'#475569':'#e7ebef');}
function chartOpts(legend){return{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:legend,labels:{color:gridColor(true),boxWidth:12,font:{size:12}}},
  tooltip:{callbacks:{label:c=>c.dataset.label+': '+money(c.raw)}}},
  scales:{x:{grid:{display:false},ticks:{color:gridColor(true)}},y:{grid:{color:gridColor(false)},ticks:{color:gridColor(true),callback:v=>sym()+' '+v}}}};}

/* ======================= MOVEMENTS ======================= */
let mvFilter='all',mvMonth=curMonth(),mvSearch='',mvSel=new Set();
function mvFiltered(){
  // Con búsqueda: filtra TODO el historial. Sin búsqueda: solo el mes.
  let list = mvSearch ? state.transactions.slice() : state.transactions.filter(t=>monthKey(t.date)===mvMonth);
  list=list.filter(inScope);
  if(mvFilter==='uncat') list=list.filter(t=>!t.categoryId && t.type!=='transfer');
  else if(mvFilter!=='all') list=list.filter(t=>t.type===mvFilter);
  if(mvSearch){const q=mvSearch.toLowerCase();
    list=list.filter(t=>(t.description||'').toLowerCase().includes(q)||((cat(t.categoryId)||{}).name||'').toLowerCase().includes(q));}
  return list;
}
function catOptionsAll(){return '<option value="">— Sin categoría —</option>'+state.categories
  .map(c=>`<option value="${c.id}">${esc(c.name)} (${c.type==='income'?'ingreso':'gasto'})</option>`).join('');}
function renderMovements(){
  const list=mvFiltered();
  const inc=list.filter(t=>t.type==='income').reduce((s,t)=>s+t.amount,0);
  const exp=list.filter(t=>t.type==='expense').reduce((s,t)=>s+t.amount,0);
  const [y,m]=mvMonth.split('-');
  $('sec-movements').innerHTML=`
    <div class="card" style="margin-bottom:16px"><div class="hd mb0" style="margin-bottom:0">
      <div style="display:flex;align-items:center;gap:10px">
        <button class="iconbtn" onclick="mvNav(-1)" ${mvSearch?'disabled':''}><i class="ti ti-chevron-left"></i></button>
        <strong style="min-width:140px;text-align:center;font-size:15px">${mvSearch?'Todo el historial':MESES[+m-1]+' '+y}</strong>
        <button class="iconbtn" onclick="mvNav(1)" ${mvSearch?'disabled':''}><i class="ti ti-chevron-right"></i></button>
      </div>
      <div class="act">
        <div style="max-width:200px">${accFilterSel()}</div>
        <span class="badge b-in">+ ${moneyS(inc,scopeSym())}</span><span class="badge b-out">− ${moneyS(exp,scopeSym())}</span>
        <button class="btn btn-soft btn-sm" onclick="openImport()"><i class="ti ti-file-import"></i> Importar banco</button>
        <button class="btn btn-soft btn-sm" onclick="window.print()"><i class="ti ti-printer"></i></button>
      </div></div></div>
    <div class="card">
      <div class="hd">
        <div class="chips">
          ${['all','income','expense','transfer','uncat'].map(f=>`<button class="${mvFilter===f?'on':''}" onclick="mvSetFilter('${f}')">${{all:'Todos',income:'Ingresos',expense:'Gastos',transfer:'Transfer.',uncat:'Sin categoría'}[f]}</button>`).join('')}
        </div>
        <input id="mvSearchBox" class="inp" style="max-width:260px" placeholder="Buscar en todo el historial..." value="${esc(mvSearch)}" oninput="mvSearchInput(this.value)">
      </div>
      <div class="mv-selbar">
        <label class="mv-all"><input type="checkbox" id="mvAll" ${list.length&&list.every(t=>mvSel.has(t.id))?'checked':''} onclick="mvSelectAll(this.checked)"> Seleccionar todo (${list.length})</label>
        <div id="mvBulk" class="mv-bulk ${mvSel.size?'':'hidden'}">
          <span><b id="mvSelCount">${mvSel.size}</b> seleccionados</span>
          <select id="mvBulkCat" class="inp" style="max-width:210px">${catOptionsAll()}</select>
          <button class="btn btn-soft btn-sm" onclick="bulkCat()"><i class="ti ti-tag"></i> Asignar categoría</button>
          <button class="btn btn-danger btn-sm" onclick="bulkDel()"><i class="ti ti-trash"></i> Eliminar</button>
          <button class="btn btn-ghost btn-sm" onclick="bulkClear()">Quitar selección</button>
        </div>
      </div>
      <div id="mvList">${mvRows(list)}</div>
    </div>`;
}
function mvRows(list){return list.length?list.map(t=>txnRow(t,true,true)).join(''):emptyBox('ti-inbox',mvSearch?'Sin resultados':'Sin movimientos en este mes');}
function mvList(){$('mvList').innerHTML=mvRows(mvFiltered());}
function mvSearchInput(v){mvSearch=v;renderMovements();const el=$('mvSearchBox');if(el){el.focus();el.setSelectionRange(el.value.length,el.value.length);}}
function mvSetFilter(f){mvFilter=f;renderMovements();}
function mvNav(d){if(mvSearch)return;const dt=new Date(mvMonth+'-01T00:00:00');dt.setMonth(dt.getMonth()+d);mvMonth=dt.toISOString().slice(0,7);renderMovements();}

/* selección múltiple */
function toggleSel(id){mvSel.has(id)?mvSel.delete(id):mvSel.add(id);updateBulkBar();
  const chk=document.querySelector(`.row-chk[onclick*="${id}"]`);if(chk)chk.closest('.row-item').classList.toggle('row-sel',mvSel.has(id));}
function mvSelectAll(on){const ids=mvFiltered().map(t=>t.id);if(on)ids.forEach(i=>mvSel.add(i));else ids.forEach(i=>mvSel.delete(i));mvList();updateBulkBar();}
function updateBulkBar(){const b=$('mvBulk');if(!b)return;b.classList.toggle('hidden',!mvSel.size);const c=$('mvSelCount');if(c)c.textContent=mvSel.size;}
function bulkClear(){mvSel.clear();renderMovements();}
async function bulkCat(){if(!mvSel.size)return;const catId=$('mvBulkCat').value;
  const r=await api('POST','transacciones/bulk/',{action:'categoria',ids:[...mvSel],categoryId:catId});
  mvSel.clear();await reload();toast(`${r.afectados} actualizados`);}
async function bulkDel(){if(!mvSel.size)return;if(!confirm(`¿Eliminar ${mvSel.size} movimientos seleccionados?`))return;
  const r=await api('POST','transacciones/bulk/',{action:'delete',ids:[...mvSel]});
  mvSel.clear();await reload();toast(`${r.afectados} eliminados`);}

/* ---------- transaction modal ---------- */
let txnType='expense';
function openTxn(id){
  const t=id?state.transactions.find(x=>x.id===String(id)):null;
  txnType=t?t.type:'expense';
  openModal(t?'Editar movimiento':'Nuevo movimiento',`
    <div class="seg" style="margin-bottom:14px">
      <button id="sgIn"  onclick="setTxnType('income')">Ingreso</button>
      <button id="sgOut" onclick="setTxnType('expense')">Gasto</button>
      <button id="sgTr"  onclick="setTxnType('transfer')">Transfer.</button>
    </div>
    <div class="fld"><label>Monto</label><input id="txAmt" class="inp" type="number" step="0.01" placeholder="0.00" value="${t?t.amount:''}"></div>
    <div class="fld"><label>Descripción</label><input id="txDesc" class="inp" placeholder="Detalle (opcional)" value="${t?esc(t.description):''}"></div>
    <div class="fld" id="txCatFld"><label>Categoría</label><select id="txCat" class="inp">${catOptions(txnType,t?t.categoryId:'')}</select></div>
    <div class="fld" id="txAccFld"><label>Cuenta</label><select id="txAcc" class="inp">${accOptions(t?t.accountId:'')}</select></div>
    <div class="fld hidden" id="txToFld"><label>Cuenta destino</label><select id="txTo" class="inp">${accOptions(t?t.toAccountId:'','— Destino —')}</select></div>
    <div class="fld"><label>Fecha</label><input id="txDate" class="inp" type="date" value="${t?t.date:today()}"></div>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="saveTxn('${id||''}')">Guardar</button>`);
  setTxnType(txnType);
}
function setTxnType(tp){txnType=tp;
  $('sgIn').className=tp==='income'?'on-in':'';$('sgOut').className=tp==='expense'?'on-out':'';$('sgTr').className=tp==='transfer'?'on-tr':'';
  const isT=tp==='transfer';
  $('txCatFld').classList.toggle('hidden',isT);
  $('txToFld').classList.toggle('hidden',!isT);
  $('txAccFld').querySelector('label').textContent=isT?'Cuenta origen':'Cuenta';
  if(!isT)$('txCat').innerHTML=catOptions(tp,$('txCat').value);
}
async function saveTxn(id){
  const amt=parseFloat($('txAmt').value);
  if(!amt||amt<=0){return shake('txAmt');}
  const d={type:txnType,amount:amt,description:$('txDesc').value.trim(),
    accountId:$('txAcc').value,date:$('txDate').value||today(),
    categoryId:txnType==='transfer'?'':$('txCat').value,
    toAccountId:txnType==='transfer'?$('txTo').value:''};
  if(txnType==='transfer'&&(!d.accountId||!d.toAccountId||d.accountId===d.toAccountId)){toast('Elige cuentas distintas');return;}
  if(id)await api('PUT','transacciones/'+id+'/',d);else await api('POST','transacciones/',d);
  closeModal();await reload();toast('Guardado');
}
async function delTxn(id){if(!confirm('¿Eliminar este movimiento?'))return;await api('DELETE','transacciones/'+id+'/');await reload();toast('Eliminado');}
async function quickCat(id,catId){
  const t=state.transactions.find(x=>x.id===String(id));if(!t)return;
  await api('PUT','transacciones/'+id+'/',{type:t.type,amount:t.amount,description:t.description,
    categoryId:catId,accountId:t.accountId,toAccountId:t.toAccountId,date:t.date});
  await reload();toast('Categoría actualizada');
}

/* ======================= ACCOUNTS ======================= */
function renderAccounts(){
  const list=state.accounts;
  $('sec-accounts').innerHTML=`
    <div class="card kpi k-net" style="margin-bottom:18px"><div class="ic"><i class="ti ti-businessplan"></i></div>
      <div class="lbl">Patrimonio total</div><div class="val">${money(patrimonio())}</div></div>
    <div class="card"><div class="hd"><h3>Cuentas</h3>
      <div class="act">
        <button class="btn btn-soft btn-sm" onclick="openImport()"><i class="ti ti-file-import"></i> Importar banco</button>
        <button class="btn btn-pri btn-sm" onclick="openAccount()"><i class="ti ti-plus"></i> Nueva cuenta</button>
      </div></div>
    <div class="grid g-3">${list.length?list.map(accCard).join(''):emptyBox('ti-wallet','Sin cuentas')}</div></div>`;
}
function accCard(a){return `<div class="acct" style="background:linear-gradient(135deg,${a.color},${shade(a.color,-22)})${a.archived?';opacity:.55':''}">
  <div class="tools"><button class="tbtn" onclick="openAccount('${a.id}')"><i class="ti ti-pencil"></i></button>
    <button class="tbtn" onclick="delAccount('${a.id}')"><i class="ti ti-trash"></i></button></div>
  <div class="top"><i class="ti ${a.icon}"></i><div><div class="nm">${esc(a.name)}</div><div class="ty">${TIPO_CUENTA[a.type]||''}${a.archived?' · archivada':''}</div></div></div>
  <div><div class="ty">${a.type==='loan'?'Deuda':'Saldo'}</div><div class="bal">${moneyS(a.balance,a.currency)}</div></div></div>`;}
function shade(hex,p){const n=parseInt(hex.slice(1),16);let r=(n>>16)+p,g=(n>>8&255)+p,b=(n&255)+p;
  r=Math.max(0,Math.min(255,r));g=Math.max(0,Math.min(255,g));b=Math.max(0,Math.min(255,b));
  return '#'+(r<<16|g<<8|b).toString(16).padStart(6,'0');}
let accColor=COLORS[0],accIcon='ti-wallet';
function openAccount(id){
  const a=id?acc(id):null;accColor=a?a.color:COLORS[0];accIcon=a?a.icon:'ti-wallet';
  openModal(a?'Editar cuenta':'Nueva cuenta',`
    <div class="fld"><label>Nombre</label><input id="acName" class="inp" placeholder="Ej. Banco Atlántida" value="${a?esc(a.name):''}"></div>
    <div class="row2">
      <div class="fld"><label>Tipo</label><select id="acType" class="inp">${Object.entries(TIPO_CUENTA).map(([k,v])=>`<option value="${k}" ${a&&a.type===k?'selected':''}>${v}</option>`).join('')}</select></div>
      <div class="fld"><label>Moneda</label><select id="acCur" class="inp">
        <option value="L" ${!a||a.currency==='L'?'selected':''}>Lempira (L)</option>
        <option value="$" ${a&&a.currency==='$'?'selected':''}>Dólar ($)</option>
      </select></div>
    </div>
    <div class="fld"><label>Saldo inicial</label><input id="acInit" class="inp" type="number" step="0.01" value="${a?a.initial:0}"></div>
    <div class="fld"><label>Color</label><div class="swatches" id="acSw">${COLORS.map(c=>`<div class="swatch ${c===accColor?'sel':''}" style="background:${c}" onclick="pickAccColor('${c}')"></div>`).join('')}</div></div>
    <div class="fld"><label>Ícono</label><div class="icons" id="acIc">${ICONS.map(i=>`<div class="ic ${i===accIcon?'sel':''}" onclick="pickAccIcon('${i}')"><i class="ti ${i}"></i></div>`).join('')}</div></div>
    ${a?`<div class="fld"><label><input type="checkbox" id="acArch" ${a.archived?'checked':''}> Archivar cuenta</label></div>`:''}
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="saveAccount('${id||''}')">Guardar</button>`);
}
function pickAccColor(c){accColor=c;document.querySelectorAll('#acSw .swatch').forEach(s=>s.classList.toggle('sel',s.style.background===hex2rgb(c)||s.style.background===c));}
function pickAccIcon(i){accIcon=i;document.querySelectorAll('#acIc .ic').forEach(e=>e.classList.remove('sel'));event.currentTarget.classList.add('sel');}
function hex2rgb(h){const n=parseInt(h.slice(1),16);return `rgb(${n>>16}, ${n>>8&255}, ${n&255})`;}
async function saveAccount(id){
  const name=$('acName').value.trim();if(!name)return shake('acName');
  const d={name,type:$('acType').value,currency:$('acCur').value,initial:parseFloat($('acInit').value)||0,color:accColor,icon:accIcon};
  if(id)d.archived=$('acArch')&&$('acArch').checked;
  if(id)await api('PUT','cuentas/'+id+'/',d);else await api('POST','cuentas/',d);
  closeModal();await reload();toast('Cuenta guardada');
}
async function delAccount(id){if(!confirm('¿Eliminar la cuenta? Los movimientos quedarán sin cuenta.'))return;
  await api('DELETE','cuentas/'+id+'/');await reload();toast('Cuenta eliminada');}

/* ======================= RECURRENTS ======================= */
function renderRecurrents(){
  const list=state.recurrents;
  $('sec-recurrents').innerHTML=`<div class="card"><div class="hd"><h3>Movimientos recurrentes</h3>
    <button class="btn btn-pri btn-sm" onclick="openRec()"><i class="ti ti-plus"></i> Nuevo</button></div>
    <p style="color:var(--muted);margin:-6px 0 14px;font-size:13px">Se generan automáticamente al llegar su fecha.</p>
    <div>${list.length?list.map(recRow).join(''):emptyBox('ti-rotate-clockwise','Sin recurrentes')}</div></div>`;
}
function recRow(r){const c=cat(r.categoryId),a=acc(r.accountId);
  return `<div class="row-item"><div class="av" style="background:${r.type==='income'?'#2fae6b':'#e1574c'}"><i class="ti ti-rotate-clockwise"></i></div>
    <div><div class="nm">${esc(r.name)}</div><div class="mt">${FREQ[r.freq]} · próx. ${fmtDate(r.next)}${c?' · '+esc(c.name):''}${a?' · '+esc(a.name):''}</div></div>
    <div class="amt ${r.type==='income'?'pos':'neg'}">${r.type==='income'?'+':'−'}${money(r.amount)}</div>
    <div class="tools">
      <button class="tbtn" onclick="toggleRec('${r.id}',${r.active})" title="${r.active?'Pausar':'Activar'}"><i class="ti ${r.active?'ti-player-pause':'ti-player-play'}"></i></button>
      <button class="tbtn" onclick="openRec('${r.id}')"><i class="ti ti-pencil"></i></button>
      <button class="tbtn del" onclick="delRec('${r.id}')"><i class="ti ti-trash"></i></button></div></div>`;}
let recType='expense';
function openRec(id){const r=id?state.recurrents.find(x=>x.id===String(id)):null;recType=r?r.type:'expense';
  openModal(r?'Editar recurrente':'Nuevo recurrente',`
    <div class="seg" style="margin-bottom:14px">
      <button id="rgIn" onclick="setRecType('income')">Ingreso</button>
      <button id="rgOut" onclick="setRecType('expense')">Gasto</button></div>
    <div class="fld"><label>Nombre</label><input id="rcName" class="inp" placeholder="Ej. Salario, Renta" value="${r?esc(r.name):''}"></div>
    <div class="row2">
      <div class="fld"><label>Monto</label><input id="rcAmt" class="inp" type="number" step="0.01" value="${r?r.amount:''}"></div>
      <div class="fld"><label>Frecuencia</label><select id="rcFreq" class="inp">${Object.entries(FREQ).map(([k,v])=>`<option value="${k}" ${r&&r.freq===k?'selected':''}>${v}</option>`).join('')}</select></div>
    </div>
    <div class="fld" id="rcCatFld"><label>Categoría</label><select id="rcCat" class="inp">${catOptions(recType,r?r.categoryId:'')}</select></div>
    <div class="fld"><label>Cuenta</label><select id="rcAcc" class="inp">${accOptions(r?r.accountId:'')}</select></div>
    <div class="fld"><label>Próxima fecha</label><input id="rcNext" class="inp" type="date" value="${r?r.next:today()}"></div>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="saveRec('${id||''}')">Guardar</button>`);
  setRecType(recType);
}
function setRecType(tp){recType=tp;$('rgIn').className=tp==='income'?'on-in':'';$('rgOut').className=tp==='expense'?'on-out':'';
  $('rcCat').innerHTML=catOptions(tp,$('rcCat').value);}
async function saveRec(id){const name=$('rcName').value.trim();const amt=parseFloat($('rcAmt').value);
  if(!name)return shake('rcName');if(!amt||amt<=0)return shake('rcAmt');
  const d={type:recType,name,amount:amt,freq:$('rcFreq').value,categoryId:$('rcCat').value,accountId:$('rcAcc').value,next:$('rcNext').value||today()};
  if(id)await api('PUT','recurrentes/'+id+'/',d);else await api('POST','recurrentes/',d);
  closeModal();await reload();toast('Recurrente guardado');}
async function toggleRec(id,active){await api('PUT','recurrentes/'+id+'/',{active:!active});await reload();}
async function delRec(id){if(!confirm('¿Eliminar recurrente?'))return;await api('DELETE','recurrentes/'+id+'/');await reload();toast('Eliminado');}

/* ======================= PENDINGS ======================= */
let pdFilter='all';
function renderPendings(){
  let list=state.pendings;if(pdFilter!=='all')list=list.filter(p=>p.type===pdFilter);
  const cobrar=state.pendings.filter(p=>p.type==='income').reduce((s,p)=>s+p.amount,0);
  const pagar=state.pendings.filter(p=>p.type==='expense').reduce((s,p)=>s+p.amount,0);
  $('sec-pendings').innerHTML=`
    <div class="grid g-2" style="margin-bottom:18px">
      ${kpi('k-in','ti-arrow-down-left','Por cobrar',money(cobrar))}
      ${kpi('k-out','ti-arrow-up-right','Por pagar',money(pagar))}
    </div>
    <div class="card"><div class="hd">
      <div class="chips">${['all','income','expense'].map(f=>`<button class="${pdFilter===f?'on':''}" onclick="pdSet('${f}')">${{all:'Todos',income:'Por cobrar',expense:'Por pagar'}[f]}</button>`).join('')}</div>
      <button class="btn btn-pri btn-sm" onclick="openPending()"><i class="ti ti-plus"></i> Nuevo</button></div>
      <div>${list.length?list.map(pdRow).join(''):emptyBox('ti-clock-hour-4','Sin pendientes')}</div></div>`;
}
function pdRow(p){return `<div class="row-item"><div class="av" style="background:${p.type==='income'?'#2fae6b':'#e1574c'}"><i class="ti ${p.type==='income'?'ti-arrow-down-left':'ti-arrow-up-right'}"></i></div>
  <div><div class="nm">${esc(p.name)}</div><div class="mt">${p.type==='income'?'Por cobrar':'Por pagar'} · ${fmtDate(p.date)}</div></div>
  <div class="amt ${p.type==='income'?'pos':'neg'}">${money(p.amount)}</div>
  <div class="tools"><button class="tbtn" onclick="confirmPending('${p.id}')" title="Marcar realizado"><i class="ti ti-check"></i></button>
    <button class="tbtn del" onclick="delPending('${p.id}')"><i class="ti ti-trash"></i></button></div></div>`;}
function pdSet(f){pdFilter=f;renderPendings();}
let pdType='income';
function openPending(){pdType='income';openModal('Nuevo pendiente',`
  <div class="seg" style="margin-bottom:14px">
    <button id="pgIn" class="on-in" onclick="setPdType('income')">Por cobrar</button>
    <button id="pgOut" onclick="setPdType('expense')">Por pagar</button></div>
  <div class="fld"><label>Nombre</label><input id="pdName" class="inp" placeholder="Ej. Préstamo a Juan"></div>
  <div class="row2"><div class="fld"><label>Monto</label><input id="pdAmt" class="inp" type="number" step="0.01"></div>
    <div class="fld"><label>Fecha</label><input id="pdDate" class="inp" type="date" value="${today()}"></div></div>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="savePending()">Guardar</button>`);}
function setPdType(tp){pdType=tp;$('pgIn').className=tp==='income'?'on-in':'';$('pgOut').className=tp==='expense'?'on-out':'';}
async function savePending(){const name=$('pdName').value.trim();const amt=parseFloat($('pdAmt').value);
  if(!name)return shake('pdName');if(!amt||amt<=0)return shake('pdAmt');
  await api('POST','pendientes/',{type:pdType,name,amount:amt,date:$('pdDate').value||today()});
  closeModal();await reload();toast('Pendiente agregado');}
async function delPending(id){if(!confirm('¿Eliminar pendiente?'))return;await api('DELETE','pendientes/'+id+'/');await reload();}
async function confirmPending(id){
  const opts=accOptions('');
  openModal('Marcar como realizado',`<p style="color:var(--muted);margin-top:0">Se convertirá en un movimiento real.</p>
    <div class="fld"><label>Cuenta</label><select id="cpAcc" class="inp">${opts}</select></div>`,
    `<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="doConfirmPending('${id}')">Confirmar</button>`);}
async function doConfirmPending(id){await api('POST','pendientes/'+id+'/confirmar/',{accountId:$('cpAcc').value});
  closeModal();await reload();toast('Convertido en movimiento');}

/* ======================= BUDGETS ======================= */
function renderBudgets(){
  const mk=curMonth();
  $('sec-budgets').innerHTML=`<div class="card"><div class="hd"><h3>Presupuestos del mes</h3>
    <button class="btn btn-pri btn-sm" onclick="openBudget()"><i class="ti ti-plus"></i> Nuevo</button></div>
    <div class="grid g-2">${state.budgets.length?state.budgets.map(b=>budgetCard(b,mk)).join(''):emptyBox('ti-chart-pie','Sin presupuestos')}</div></div>`;
}
function budgetCard(b,mk){
  const catIds=b.items.map(i=>i.catId);
  const spent=state.transactions.filter(t=>t.type==='expense'&&monthKey(t.date)===mk&&catIds.includes(t.categoryId)).reduce((s,t)=>s+t.amount,0);
  const pct=b.limit>0?Math.min(100,spent/b.limit*100):0;
  const over=spent>b.limit;const col=over?'#e1574c':(pct>80?'#C9A84C':'#2fae6b');
  const names=catIds.map(id=>{const c=cat(id);return c?esc(c.name):'';}).filter(Boolean).join(', ')||'Sin categorías';
  return `<div class="card" style="background:var(--surface-2)"><div class="hd mb0" style="margin-bottom:8px">
    <strong>${esc(b.name)}</strong>
    <button class="tbtn del" onclick="delBudget('${b.id}')"><i class="ti ti-trash"></i></button></div>
    <div class="mt" style="color:var(--muted);font-size:12px;margin-bottom:10px">${names}</div>
    <div class="bar"><span style="width:${pct}%;background:${col}"></span></div>
    <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:13px">
      <span style="color:${col};font-weight:700">${money(spent)}</span>
      <span style="color:var(--muted)">de ${money(b.limit)}</span></div>
    ${over?`<div style="color:#e1574c;font-size:12px;margin-top:5px;font-weight:600"><i class="ti ti-alert-triangle"></i> Excedido por ${money(spent-b.limit)}</div>`:''}</div>`;
}
let budCats=[];
function openBudget(){budCats=[];openModal('Nuevo presupuesto',`
  <div class="fld"><label>Nombre</label><input id="buName" class="inp" placeholder="Ej. Gastos fijos"></div>
  <div class="fld"><label>Límite mensual</label><input id="buLimit" class="inp" type="number" step="0.01"></div>
  <div class="fld"><label>Categorías (gastos)</label>
    <div class="icons" style="max-height:160px">${state.categories.filter(c=>c.type==='expense').map(c=>`
      <label class="ic" style="width:auto;padding:6px 10px;gap:6px"><input type="checkbox" value="${c.id}" class="buCat"> ${esc(c.name)}</label>`).join('')||'<span style="color:var(--muted)">Crea categorías de gasto primero</span>'}</div></div>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="saveBudget()">Guardar</button>`);}
async function saveBudget(){const name=$('buName').value.trim();const limit=parseFloat($('buLimit').value);
  if(!name)return shake('buName');if(!limit||limit<=0)return shake('buLimit');
  const items=[...document.querySelectorAll('.buCat:checked')].map(c=>({catId:c.value}));
  await api('POST','presupuestos/',{name,limit,items});closeModal();await reload();toast('Presupuesto creado');}
async function delBudget(id){if(!confirm('¿Eliminar presupuesto?'))return;await api('DELETE','presupuestos/'+id+'/');await reload();}

/* ======================= GOALS ======================= */
function renderGoals(){
  $('sec-goals').innerHTML=`<div class="card"><div class="hd"><h3>Metas de ahorro</h3>
    <button class="btn btn-pri btn-sm" onclick="openGoal()"><i class="ti ti-plus"></i> Nueva meta</button></div>
    <div class="grid g-3">${state.goals.length?state.goals.map(goalCard).join(''):emptyBox('ti-target','Sin metas')}</div></div>`;
}
function goalCard(g){const pct=g.target>0?Math.min(100,g.saved/g.target*100):0;const done=g.saved>=g.target;
  return `<div class="card" style="background:var(--surface-2)">
    <div class="hd mb0" style="margin-bottom:8px"><div style="font-size:26px">${g.emoji}</div>
      <div class="tools" style="opacity:1"><button class="tbtn" onclick="openGoal('${g.id}')"><i class="ti ti-pencil"></i></button>
        <button class="tbtn del" onclick="delGoal('${g.id}')"><i class="ti ti-trash"></i></button></div></div>
    <div class="nm" style="font-weight:700;margin-bottom:4px">${esc(g.name)}</div>
    <div class="bar"><span style="width:${pct}%;background:${done?'#2fae6b':'#C9A84C'}"></span></div>
    <div style="display:flex;justify-content:space-between;margin-top:8px;font-size:13px">
      <strong>${money(g.saved)}</strong><span style="color:var(--muted)">de ${money(g.target)}</span></div>
    ${g.deadline?`<div class="mt" style="color:var(--muted);font-size:12px;margin-top:4px">Meta: ${fmtDate(g.deadline)}</div>`:''}
    ${done?'<div style="color:#2fae6b;font-weight:700;font-size:13px;margin-top:8px"><i class="ti ti-circle-check"></i> ¡Completada!</div>':
      `<button class="btn btn-soft btn-sm" style="width:100%;justify-content:center;margin-top:10px" onclick="openSave('${g.id}')"><i class="ti ti-plus"></i> Abonar</button>`}</div>`;}
const EMOJIS=['🎯','🏠','🚗','✈️','💍','🎓','💻','📱','🏖️','💰','🎁','⚽'];
let goalEmoji='🎯';
function openGoal(id){const g=id?state.goals.find(x=>x.id===String(id)):null;goalEmoji=g?g.emoji:'🎯';
  openModal(g?'Editar meta':'Nueva meta',`
    <div class="fld"><label>Emoji</label><div class="swatches" id="goEm">${EMOJIS.map(e=>`<div class="swatch ${e===goalEmoji?'sel':''}" style="font-size:20px;text-align:center;background:var(--surface-2)" onclick="pickEmoji('${e}')">${e}</div>`).join('')}</div></div>
    <div class="fld"><label>Nombre</label><input id="goName" class="inp" value="${g?esc(g.name):''}" placeholder="Ej. Viaje"></div>
    <div class="row2"><div class="fld"><label>Objetivo</label><input id="goTarget" class="inp" type="number" step="0.01" value="${g?g.target:''}"></div>
      <div class="fld"><label>Fecha límite</label><input id="goDeadline" class="inp" type="date" value="${g&&g.deadline?g.deadline:''}"></div></div>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="saveGoal('${id||''}')">Guardar</button>`);}
function pickEmoji(e){goalEmoji=e;document.querySelectorAll('#goEm .swatch').forEach(s=>s.classList.remove('sel'));event.currentTarget.classList.add('sel');}
async function saveGoal(id){const name=$('goName').value.trim();const target=parseFloat($('goTarget').value);
  if(!name)return shake('goName');if(!target||target<=0)return shake('goTarget');
  const d={name,target,deadline:$('goDeadline').value||'',emoji:goalEmoji};
  if(id)await api('PUT','metas/'+id+'/',d);else await api('POST','metas/',d);closeModal();await reload();toast('Meta guardada');}
async function delGoal(id){if(!confirm('¿Eliminar meta?'))return;await api('DELETE','metas/'+id+'/');await reload();}
function openSave(id){openModal('Abonar a la meta',`
  <div class="fld"><label>Monto a abonar</label><input id="svAmt" class="inp" type="number" step="0.01"></div>
  <div class="fld"><label>Desde la cuenta</label><select id="svAcc" class="inp">${accOptions('')}</select></div>
  <p style="color:var(--muted);font-size:12px">Se registra como un gasto "Ahorro".</p>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="doSave('${id}')">Abonar</button>`);}
async function doSave(id){const amt=parseFloat($('svAmt').value);if(!amt||amt<=0)return shake('svAmt');
  await api('POST','metas/'+id+'/ahorrar/',{amount:amt,accountId:$('svAcc').value});closeModal();await reload();toast('Abono registrado');}

/* ======================= REPORTS ======================= */
function renderReports(){
  const fromD=new Date();fromD.setMonth(fromD.getMonth()-1);
  $('sec-reports').innerHTML=`
    <div class="card" style="margin-bottom:18px"><div class="hd"><h3>Generar reporte</h3></div>
      <div class="row2">
        <div class="fld"><label>Desde</label><input id="rpFrom" class="inp" type="date" value="${fromD.toISOString().slice(0,10)}"></div>
        <div class="fld"><label>Hasta</label><input id="rpTo" class="inp" type="date" value="${today()}"></div>
      </div>
      <div style="display:flex;gap:10px;flex-wrap:wrap">
        <button class="btn btn-pri" onclick="dlReport('pdf')"><i class="ti ti-file-type-pdf"></i> PDF</button>
        <button class="btn btn-soft" onclick="dlReport('xlsx')"><i class="ti ti-file-spreadsheet"></i> Excel</button>
        <button class="btn btn-soft" onclick="dlReport('csv')"><i class="ti ti-file-text"></i> CSV</button>
      </div>
    </div>
    <div class="card"><div class="hd"><h3>Vista previa del período</h3></div>
      <div class="chartbox sm"><canvas id="chRep"></canvas></div>
      <div id="rpSummary" style="margin-top:14px"></div></div>`;
  drawReportPreview();
}
function reportRange(){return{from:$('rpFrom').value,to:$('rpTo').value};}
function inRange(d,f,t){return (!f||d>=f)&&(!t||d<=t);}
function drawReportPreview(){
  const {from,to}=reportRange();
  const list=state.transactions.filter(t=>inRange(t.date,from,to)&&!catExcluded(t));
  const inc=list.filter(t=>t.type==='income').reduce((s,t)=>s+t.amount,0);
  const exp=list.filter(t=>t.type==='expense').reduce((s,t)=>s+t.amount,0);
  charts.rep&&charts.rep.destroy();
  charts.rep=new Chart($('chRep'),{type:'bar',data:{labels:['Ingresos','Gastos','Balance'],
    datasets:[{data:[inc,exp,inc-exp],backgroundColor:['#2fae6b','#e1574c','#3a8fb7'],borderRadius:8,maxBarThickness:60}]},
    options:{...chartOpts(false)}});
  $('rpSummary').innerHTML=`<div class="grid g-3">
    ${kpi('k-in','ti-trending-up','Ingresos',money(inc))}
    ${kpi('k-out','ti-trending-down','Gastos',money(exp))}
    ${kpi('k-bal','ti-scale','Balance',money(inc-exp),inc-exp>=0?'pos':'neg')}</div>
    <p style="color:var(--muted);margin-top:12px;font-size:13px">${list.length} movimientos en el período.</p>`;
}
function dlReport(fmt){const {from,to}=reportRange();
  const url=`${API}reporte/?format=${fmt}&from=${from}&to=${to}`;
  window.open(url,'_blank');}
['rpFrom','rpTo'].forEach(()=>{});
document.addEventListener('change',e=>{if(e.target&&(e.target.id==='rpFrom'||e.target.id==='rpTo'))drawReportPreview();});

/* ======================= CATEGORIES ======================= */
function renderCategories(){
  const inc=state.categories.filter(c=>c.type==='income'),exp=state.categories.filter(c=>c.type==='expense');
  $('sec-categories').innerHTML=`
    <div class="card" style="margin-bottom:18px"><div class="hd"><h3><i class="ti ti-arrow-down-left" style="color:var(--pos)"></i> Ingresos</h3>
      <button class="btn btn-pri btn-sm" onclick="openCat('income')"><i class="ti ti-plus"></i> Nueva</button></div>
      <div>${inc.length?inc.map(catRow).join(''):emptyBox('ti-tags','Sin categorías de ingreso')}</div></div>
    <div class="card"><div class="hd"><h3><i class="ti ti-arrow-up-right" style="color:var(--neg)"></i> Gastos</h3>
      <button class="btn btn-pri btn-sm" onclick="openCat('expense')"><i class="ti ti-plus"></i> Nueva</button></div>
      <div>${exp.length?exp.map(catRow).join(''):emptyBox('ti-tags','Sin categorías de gasto')}</div></div>`;
}
function catRow(c){return `<div class="row-item"><div class="av" style="background:${c.color}"><i class="ti ${c.icon}"></i></div>
  <div class="nm">${esc(c.name)}</div>
  <div class="tools" style="margin-left:auto"><button class="tbtn" onclick="openCat('${c.type}','${c.id}')"><i class="ti ti-pencil"></i></button>
    <button class="tbtn del" onclick="delCat('${c.id}')"><i class="ti ti-trash"></i></button></div></div>`;}
let catColor=COLORS[0],catIcon='ti-tag',catType='expense';
function openCat(type,id){const c=id?cat(id):null;catType=type;catColor=c?c.color:COLORS[0];catIcon=c?c.icon:'ti-tag';
  openModal(c?'Editar categoría':'Nueva categoría',`
    <div class="fld"><label>Nombre</label><input id="ctName" class="inp" value="${c?esc(c.name):''}" placeholder="Ej. Restaurantes"></div>
    <div class="fld"><label>Color</label><div class="swatches" id="ctSw">${COLORS.map(x=>`<div class="swatch ${x===catColor?'sel':''}" style="background:${x}" onclick="pickCatColor('${x}')"></div>`).join('')}</div></div>
    <div class="fld"><label>Ícono</label><div class="icons" id="ctIc">${ICONS.map(i=>`<div class="ic ${i===catIcon?'sel':''}" onclick="pickCatIcon('${i}')"><i class="ti ${i}"></i></div>`).join('')}</div></div>
  `,`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
     <button class="btn btn-pri" onclick="saveCat('${id||''}')">Guardar</button>`);}
function pickCatColor(c){catColor=c;document.querySelectorAll('#ctSw .swatch').forEach(s=>s.classList.toggle('sel',s.style.background===hex2rgb(c)));}
function pickCatIcon(i){catIcon=i;document.querySelectorAll('#ctIc .ic').forEach(e=>e.classList.remove('sel'));event.currentTarget.classList.add('sel');}
async function saveCat(id){const name=$('ctName').value.trim();if(!name)return shake('ctName');
  const d={name,type:catType,color:catColor,icon:catIcon};
  if(id)await api('PUT','categorias/'+id+'/',d);else await api('POST','categorias/',d);closeModal();await reload();toast('Categoría guardada');}
async function delCat(id){if(!confirm('¿Eliminar categoría? Sus movimientos quedarán sin categoría.'))return;
  await api('DELETE','categorias/'+id+'/');await reload();}

/* ======================= SETTINGS ======================= */
function renderSettings(){
  $('sec-settings').innerHTML=`
    <div class="grid g-2">
      <div class="card"><div class="hd"><h3>Preferencias</h3></div>
        <div class="fld"><label>Moneda predeterminada</label><select id="stCur" class="inp">
          <option value="L" ${state.settings.currency==='L'?'selected':''}>Lempira (L)</option>
          <option value="$" ${state.settings.currency==='$'?'selected':''}>Dólar ($)</option>
        </select>
        <div class="text-muted" style="font-size:12px;margin-top:4px;color:var(--muted)">Cada cuenta puede tener su propia moneda (ej. Banco en L, cuenta en $).</div></div>
        <div class="fld"><label>Tema</label><select id="stTheme" class="inp">
          <option value="dark" ${state.settings.theme==='dark'?'selected':''}>Oscuro</option>
          <option value="light" ${state.settings.theme==='light'?'selected':''}>Claro</option></select></div>
        <button class="btn btn-pri" onclick="saveSettings()"><i class="ti ti-device-floppy"></i> Guardar</button>
      </div>
      <div class="card"><div class="hd"><h3>Respaldo de datos</h3></div>
        <p style="color:var(--muted);font-size:13px;margin-top:0">Exporta o restaura toda tu información.</p>
        <button class="btn btn-soft" style="width:100%;justify-content:center;margin-bottom:10px" onclick="exportJSON()"><i class="ti ti-download"></i> Exportar JSON</button>
        <label class="btn btn-soft" style="width:100%;justify-content:center;margin-bottom:10px;cursor:pointer"><i class="ti ti-upload"></i> Importar JSON
          <input type="file" accept="application/json" class="hidden" onchange="importJSON(this)"></label>
        <button class="btn btn-danger" style="width:100%;justify-content:center" onclick="clearAll()"><i class="ti ti-trash"></i> Borrar todo y reiniciar</button>
      </div>
    </div>`;
}
async function saveSettings(){const cur=$('stCur').value.trim()||'L';const theme=$('stTheme').value;
  state.settings.currency=cur;state.settings.theme=theme;applyTheme();
  await api('POST','configuracion/',{currency:cur,theme});toast('Preferencias guardadas');render();}
function exportJSON(){const blob=new Blob([JSON.stringify(state,null,2)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download='finanzas_backup.json';a.click();}
function importJSON(input){const f=input.files[0];if(!f)return;const r=new FileReader();
  r.onload=async()=>{try{const data=JSON.parse(r.result);if(!confirm('Esto reemplazará TODOS tus datos. ¿Continuar?'))return;
    await api('POST','importar/',data);await reload();toast('Datos importados');}catch(e){toast('Archivo inválido');}};r.readAsText(f);}
async function clearAll(){if(!confirm('¿Borrar TODOS los datos y reiniciar? No se puede deshacer.'))return;
  await api('POST','limpiar/');await reload();toast('Datos reiniciados');}

/* ======================= IMPORTAR ESTADO DE CUENTA ======================= */
let impFile=null;
function openImport(){
  impFile=null;
  const def=(state.accounts.find(a=>a.type==='bank'&&!a.archived)||state.accounts.find(a=>!a.archived)||{}).id||'';
  openModal('Importar estado de cuenta',`
    <p style="color:var(--muted);font-size:13px;margin-top:0">Sube tu estado de cuenta del banco en <b>PDF, Excel o CSV</b>. Se leerán los movimientos automáticamente y se omitirán los que ya existan.</p>
    <div class="fld"><label>Cuenta destino</label><select id="impAcc" class="inp">${accOptions(def)}</select></div>
    <label class="imp-drop" id="impDrop">
      <input id="impFile" type="file" accept=".pdf,.xlsx,.xlsm,.xls,.csv" class="hidden" onchange="impPick(this)">
      <i class="ti ti-cloud-upload"></i>
      <div id="impDropTxt"><b>Haz clic para elegir el archivo</b><br><span style="color:var(--muted);font-size:12px">PDF, Excel o CSV del banco</span></div>
    </label>
    <div id="impResult"></div>
  `,impFootAnalyze(true));
}
function impFootAnalyze(disabled){return `<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
  <button class="btn btn-pri" id="impGo" onclick="impAnalyze()" ${disabled?'disabled':''}><i class="ti ti-search"></i> Analizar</button>`;}
function impPick(inp){
  impFile=inp.files[0]||null;
  $('impResult').innerHTML='';
  if(impFile){$('impDropTxt').innerHTML=`<b>${esc(impFile.name)}</b><br><span style="color:var(--muted);font-size:12px">Listo para analizar</span>`;
    $('impDrop').classList.add('has');}
  $('mFoot').innerHTML=impFootAnalyze(!impFile);
}
async function impAnalyze(){
  if(!impFile)return toast('Elige un archivo');
  const acc=$('impAcc').value;if(!acc)return toast('Elige una cuenta');
  const fd=new FormData();fd.append('archivo',impFile);fd.append('cuenta',acc);fd.append('commit','0');
  const btn=$('impGo');btn.disabled=true;btn.innerHTML='<i class="ti ti-loader-2"></i> Analizando…';
  let res;try{res=await apiUpload('importar-estado/',fd);}catch(e){btn.disabled=false;btn.innerHTML='<i class="ti ti-search"></i> Analizar';return;}
  impPreview(res);
}
function impPreview(res){
  const s=res.summary;
  const rows=res.rows.map(r=>`<tr class="${r.transfer?'imp-dup':''}">
    <td>${fmtDate(r.date)}</td><td class="imp-desc">${esc(r.description)}</td>
    <td class="${r.type==='income'?'pos':'neg'}" style="text-align:right;white-space:nowrap">${r.type==='income'?'+':'−'}${money(r.amount)}</td>
    <td style="text-align:center">${r.transfer?'<span class="imp-tag dup">Transfer.</span>':''}</td></tr>`).join('');
  $('impResult').innerHTML=`
    <div class="imp-sum">
      <div><span>Movimientos</span><b>${s.total}</b></div>
      <div><span>Ingresos</span><b class="pos">+${money(s.ingresos)}</b></div>
      <div><span>Gastos</span><b class="neg">−${money(s.gastos)}</b></div>
      <div><span>Transferencias</span><b style="color:var(--info)">${money(s.transferencias)}</b></div>
    </div>
    <div style="font-size:12px;color:var(--muted);margin:-4px 0 10px">Periodo: ${fmtDate(s.desde)} – ${fmtDate(s.hasta)}. Las transferencias entre cuentas no cuentan como ingreso/gasto.</div>
    <div class="fld"><label>Saldo final de la cuenta (se ajusta a este monto)</label>
      <input id="impSaldo" class="inp" type="number" step="0.01" value="${s.sugerido!=null?s.sugerido:''}">
      <div style="font-size:12px;color:var(--muted);margin-top:4px">
        ${s.disponible!=null?`Disponible en banco: <b>${money(s.disponible)}</b>. `:''}${s.cierre!=null?`En libros: ${money(s.cierre)}.`:''}</div>
    </div>
    <label class="imp-adj"><input type="checkbox" id="impReempl" checked>
      Reemplazar lo ya importado de este periodo (recomendado)${s.en_rango?` — hay ${s.en_rango} importados`:''}</label>
    <div class="imp-tablewrap"><table class="imp-table"><thead><tr><th>Fecha</th><th>Descripción</th><th style="text-align:right">Monto</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>`;
  $('mFoot').innerHTML=`<button class="btn btn-ghost" onclick="closeModal()">Cancelar</button>
    <button class="btn btn-pri" id="impGo" onclick="impCommit()"><i class="ti ti-download"></i> Importar ${s.total}</button>`;
}
async function impCommit(){
  if(!impFile)return;
  const fd=new FormData();fd.append('archivo',impFile);fd.append('cuenta',$('impAcc').value);fd.append('commit','1');
  fd.append('reemplazar',($('impReempl')&&$('impReempl').checked)?'1':'0');
  fd.append('ajustar','1');
  const sv=$('impSaldo');if(sv&&sv.value!=='')fd.append('saldo_objetivo',sv.value);
  const btn=$('impGo');btn.disabled=true;btn.innerHTML='<i class="ti ti-loader-2"></i> Importando…';
  let res;try{res=await apiUpload('importar-estado/',fd);}catch(e){btn.disabled=false;return;}
  closeModal();await reload();
  toast(`${res.creados} ${res.creados===1?'movimiento importado':'movimientos importados'}`);
}

/* ======================= MODAL / utils ======================= */
function openModal(title,body,foot){$('mTitle').textContent=title;$('mBody').innerHTML=body;$('mFoot').innerHTML=foot||'';$('ov').classList.add('show');}
function closeModal(){$('ov').classList.remove('show');}
function shake(id){const e=$(id);if(e){e.classList.add('shake');e.focus();setTimeout(()=>e.classList.remove('shake'),350);}}

/* ======================= BOOT ======================= */
async function reload(){state=await api('GET','data/');applyTheme();render();}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeModal();});
document.querySelectorAll('.nav a[data-go]').forEach(a=>a.addEventListener('click',()=>goTo(a.dataset.go)));
(async()=>{try{state=await api('GET','data/');}catch(e){return;}applyTheme();goTo('dashboard');})();
window.goTo=goTo;window.openTxn=openTxn;window.toggleTheme=toggleTheme;window.toggleSidebar=toggleSidebar;
window.openImport=openImport;window.impPick=impPick;window.impAnalyze=impAnalyze;window.impCommit=impCommit;
window.quickCat=quickCat;
window.mvSearchInput=mvSearchInput;window.toggleSel=toggleSel;window.mvSelectAll=mvSelectAll;window.setAccFilter=setAccFilter;
window.bulkCat=bulkCat;window.bulkDel=bulkDel;window.bulkClear=bulkClear;
