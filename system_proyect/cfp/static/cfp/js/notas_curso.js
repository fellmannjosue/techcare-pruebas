/* notas_curso.js — <--- hecho por claude code: extraído del template.
   Los datos de Django llegan por la isla JSON #notas-curso-data. */
const DATA = JSON.parse(document.getElementById('notas-curso-data').textContent);

const CURSO_PK = DATA.cursoPk;
const URL_MOD_GUARDAR = DATA.urlModGuardar;
const URL_MOD_ELIMINAR = DATA.urlModEliminar;
const URL_NOTAS_GUARDAR = DATA.urlNotasGuardar;
const URL_HORAS_GUARDAR = DATA.urlHorasGuardar;
const CSRF = document.querySelector('[name=csrfmiddlewaretoken]').value;
const MODULOS = DATA.modulos;

function post(url, data) {
  return fetch(url, {method:'POST', headers:{'Content-Type':'application/json','X-CSRFToken':CSRF},
    body:JSON.stringify(data)}).then(r => r.json());
}

// ── Colores Tab 1 (intento con que aprobó) ──
function umbralKind(kind) { return kind === 'p' ? 100 : 90; }  // práctico aprueba con 100
function recolor(inp) {
  const mod = inp.dataset.modulo, per = inp.dataset.persona, kind = inp.dataset.kind;
  const grupo = document.querySelectorAll(`.nt-input[data-modulo="${mod}"][data-persona="${per}"][data-kind="${kind}"]`);
  const umb = umbralKind(kind);
  let win = -1;
  grupo.forEach((el, i) => { if (win < 0 && el.value !== '' && parseFloat(el.value) >= umb) win = i; });
  const cls = ['nota-verde','nota-azul','nota-rojo'];
  grupo.forEach((el, i) => {
    el.classList.remove('nota-verde','nota-azul','nota-rojo','nota-negro');
    if (i === win) el.classList.add(cls[i]);
    else if (el.value !== '') el.classList.add('nota-negro');
  });
}

// ── Compilación (Tab 2) y Módulos (Tab 3) en vivo ──
const N_MODULOS = DATA.nModulos;
function primerAprobado(vals, umbral) {  // primer intento que aprueba, si no 0
  for (const v of vals) { if (v !== '' && v != null && parseFloat(v) >= umbral) return parseFloat(v); }
  return 0;
}
function recompute() {
  const data = {};
  document.querySelectorAll('#tab-prog .nt-input').forEach(el => {
    const k = el.dataset.modulo + '_' + el.dataset.persona;
    if (!data[k]) data[k] = {modulo:el.dataset.modulo, persona:el.dataset.persona, t:['','',''], p:['','','']};
    data[k][el.dataset.kind][parseInt(el.dataset.idx)] = el.value;
  });
  const acc = {};
  Object.values(data).forEach(g => {
    const cT = primerAprobado(g.t, 90), cP = primerAprobado(g.p, 100);
    const res = Math.round((cT + cP) / 2 * 100) / 100;
    setComp('T', g.modulo, g.persona, cT);
    setComp('P', g.modulo, g.persona, cP);
    const r = document.querySelector(`[data-res][data-modulo="${g.modulo}"][data-persona="${g.persona}"]`);
    if (r) r.textContent = res;
    acc[g.persona] = (acc[g.persona] || 0) + res;
  });
  Object.keys(acc).forEach(per => {
    const nf = N_MODULOS ? Math.round(acc[per] / N_MODULOS * 100) / 100 : 0;
    const el = document.querySelector(`[data-final][data-persona="${per}"]`);
    if (el) el.textContent = nf;
  });
}
function setComp(kind, mod, per, val) {
  const td = document.querySelector(`[data-comp="${kind}"][data-modulo="${mod}"][data-persona="${per}"]`);
  if (!td) return;
  td.textContent = val;
  td.classList.toggle('nota-verde', val > 0);
}

// ── Autoguardado (debounce) ──
let saveTimer = null;
function setStatus(html) { document.getElementById('autosave-status').innerHTML = html; }
function onNotaInput(inp) {
  recolor(inp); recompute();
  setStatus('<i class="ti ti-pencil me-1"></i>Editando…');
  clearTimeout(saveTimer);
  saveTimer = setTimeout(guardarNotas, 900);
}
document.querySelectorAll('#tab-prog .nt-input').forEach(recolor);
recompute();

// ── Módulos ──
let modBs;
function abrirModulo() {
  document.getElementById('modModuloTitle').textContent = 'Nuevo módulo';
  document.getElementById('mod_pk').value = '';
  document.getElementById('mod_codigo').value = '';
  document.getElementById('mod_puntaje').value = '100';
  document.getElementById('mod_fini').value = '';
  document.getElementById('mod_ffin').value = '';
  document.getElementById('mod_del').classList.add('d-none');
  modBs = modBs || new bootstrap.Modal('#modModulo'); modBs.show();
}
function editarModulo(id) {
  const m = MODULOS.find(x => x.id === id); if (!m) return;
  document.getElementById('modModuloTitle').textContent = 'Editar ' + m.codigo;
  document.getElementById('mod_pk').value = m.id;
  document.getElementById('mod_codigo').value = m.codigo;
  document.getElementById('mod_puntaje').value = m.puntaje;
  document.getElementById('mod_fini').value = m.fini || '';
  document.getElementById('mod_ffin').value = m.ffin || '';
  document.getElementById('mod_del').classList.remove('d-none');
  modBs = modBs || new bootstrap.Modal('#modModulo'); modBs.show();
}
function guardarModulo(btn) {
  btn.disabled = true;
  post(URL_MOD_GUARDAR, {curso_pk:CURSO_PK, pk:document.getElementById('mod_pk').value || null,
    prefijo:document.getElementById('mod_prefijo').value,
    codigo:document.getElementById('mod_codigo').value,
    puntaje:document.getElementById('mod_puntaje').value,
    fecha_inicio:document.getElementById('mod_fini').value || null,
    fecha_fin:document.getElementById('mod_ffin').value || null
  }).then(r => { if (r.ok) location.reload(); else { alert(r.error || 'Error'); btn.disabled = false; } })
    .catch(() => { alert('Error de red'); btn.disabled = false; });
}
function eliminarModulo() {
  if (!confirm('¿Eliminar este módulo y sus notas?')) return;
  post(URL_MOD_ELIMINAR, {pk:document.getElementById('mod_pk').value}).then(r => { if (r.ok) location.reload(); });
}

// ── Guardar notas (Tab 1) — silencioso, sin recargar ──
function guardarNotas() {
  const grupos = {};
  document.querySelectorAll('#tab-prog .nt-input').forEach(el => {
    const k = el.dataset.modulo + '_' + el.dataset.persona;
    if (!grupos[k]) {
      const tr = el.closest('tr');
      grupos[k] = {modulo:parseInt(el.dataset.modulo), persona:parseInt(el.dataset.persona),
        nombre:tr.dataset.nombre, identidad:tr.dataset.identidad};
    }
    grupos[k][el.dataset.kind + (parseInt(el.dataset.idx)+1)] = el.value === '' ? null : el.value;
  });
  setStatus('<i class="ti ti-loader me-1"></i>Guardando…');
  post(URL_NOTAS_GUARDAR, {curso_pk:CURSO_PK, notas:Object.values(grupos)})
    .then(r => { setStatus(r.ok ? '<i class="ti ti-circle-check me-1 text-green"></i>Guardado'
                                : '<i class="ti ti-alert-triangle me-1 text-red"></i>Error al guardar'); })
    .catch(() => setStatus('<i class="ti ti-alert-triangle me-1 text-red"></i>Sin conexión'));
}

// ── Horas (Tab 4) ──
function recalcHoras() {
  let metaTotal = 0;
  document.querySelectorAll('.meta-input').forEach(el => metaTotal += parseFloat(el.value || 0));
  document.getElementById('meta-total').textContent = (Math.round(metaTotal*100)/100);
  document.querySelectorAll('.tot-part').forEach(td => {
    const per = td.dataset.persona; let t = 0;
    document.querySelectorAll(`.hora-input[data-persona="${per}"]`).forEach(el => t += parseFloat(el.value || 0));
    td.textContent = (Math.round(t*100)/100);
    const pct = metaTotal ? Math.round(t/metaTotal*1000)/10 : 0;
    document.querySelector(`.pct-part[data-persona="${per}"]`).textContent = pct + '%';
  });
}
function guardarHoras(btn) {
  const meta = {};
  document.querySelectorAll('.meta-input').forEach(el => meta[el.dataset.mes] = el.value || 0);
  const part = [];
  document.querySelectorAll('.hora-input').forEach(el => part.push(
    {persona:parseInt(el.dataset.persona), mes:parseInt(el.dataset.mes), horas:el.value || 0}));
  btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
  post(URL_HORAS_GUARDAR, {curso_pk:CURSO_PK, meta:meta, part:part})
    .then(r => { if (r.ok) location.reload(); else { alert('Error'); btn.disabled = false; } })
    .catch(() => { alert('Error de red'); btn.disabled = false; });
}
