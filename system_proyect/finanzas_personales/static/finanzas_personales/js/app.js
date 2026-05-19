'use strict';

const COLORS = ['#C9A84C','#2A7A4F','#B84040','#3A6FA8','#7B5EA7','#D4843C','#4A8F7F','#B05C87','#5A7A3A','#8A6040'];
const MONTHS  = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];
const API     = '/finanzas/api/';

let state = {
  categories: [], transactions: [], pendings: [],
  budgets: [], quickEntries: [], goals: [],
  settings: { currency: 'L', theme: 'light' }
};

let currentSection = 'inicio';
let currentMonth   = new Date().getMonth();
let currentYear    = new Date().getFullYear();
let movFilter = 'all', pendFilter = 'all';
let pendingQE = null;
let editTxnId = null, editCatId = null, editPendingId = null, editGoalId = null;
let txnType = 'income', qeType = 'expense', catType = 'expense', pendingType = 'income';

// ── API HELPER ──────────────────────────────────────────
function csrfToken() {
  const m = document.cookie.match(/csrftoken=([^;]+)/);
  return m ? m[1] : '';
}

async function api(method, path, data) {
  const opts = {
    method,
    headers: { 'X-CSRFToken': csrfToken(), 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };
  if (data !== undefined) opts.body = JSON.stringify(data);
  const resp = await fetch(API + path, opts);
  if (!resp.ok) throw new Error('Error ' + resp.status);
  return resp.json();
}

async function loadFromServer() { state = await api('GET', 'data/'); }

// ── FORMATEO ────────────────────────────────────────────
function fmt(n) {
  const s = state.settings?.currency || 'L';
  return s + ' ' + Number(n).toLocaleString('es-HN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtDate(d) {
  if (!d) return '';
  return new Date(d + 'T12:00:00').toLocaleDateString('es', { day: '2-digit', month: 'short', year: 'numeric' });
}
function today() { return new Date().toISOString().slice(0, 10); }
function getCatById(id) { return state.categories.find(c => c.id === String(id)); }
function esc(s) {
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// ── MODAL HELPERS ───────────────────────────────────────
function openModal(id, typeHint) {
  if (id === 'modal-txn') {
    editTxnId = null;
    setTxnType(typeHint || 'income');
    document.getElementById('txn-amount').value = '';
    document.getElementById('txn-desc').value   = '';
    document.getElementById('txn-date').value   = today();
    document.getElementById('modal-txn-title').textContent = 'Nueva Transacción';
  }
  bootstrap.Modal.getOrCreateInstance(document.getElementById(id)).show();
}

function closeModal(id) {
  bootstrap.Modal.getInstance(document.getElementById(id))?.hide();
}

// ── NAVEGACIÓN ──────────────────────────────────────────
const SECTIONS = ['inicio','movements','pendientes','categorias','presupuestos','metas','respaldo'];
const SECTION_TITLES = {
  inicio:'Inicio', movements:'Movimientos', pendientes:'Pendientes',
  categorias:'Categorías', presupuestos:'Presupuestos', metas:'Metas de Ahorro', respaldo:'Ajustes'
};

function goTo(id) {
  SECTIONS.forEach(s => {
    document.getElementById('section-'+s)?.classList.remove('active');
    document.getElementById('nav-'+s)?.classList.remove('active');
  });
  document.getElementById('section-'+id)?.classList.add('active');
  document.getElementById('nav-'+id)?.classList.add('active');
  document.getElementById('topbar-section').textContent = SECTION_TITLES[id] || id;
  currentSection = id;
  const fab = document.getElementById('fab-btn');
  if (fab) fab.style.display = ['pendientes','categorias','presupuestos','metas'].includes(id) ? '' : 'none';
  renderSection(id);
}

function fabAction() {
  if (currentSection === 'pendientes')        openPendingModal();
  else if (currentSection === 'categorias')   openCatModal();
  else if (currentSection === 'presupuestos') openBudgetModal();
  else if (currentSection === 'metas')        openGoalModal();
}

function renderSection(id) {
  ({
    inicio:       renderDashboard,
    movements:    renderMovements,
    pendientes:   renderPendientes,
    categorias:   renderCategorias,
    presupuestos: renderPresupuestos,
    metas:        renderMetas,
    respaldo:     renderRespaldo,
  })[id]?.();
}

// ── DASHBOARD ───────────────────────────────────────────
function renderDashboard() {
  const m = new Date().getMonth(), y = new Date().getFullYear();
  const txns = state.transactions.filter(t => {
    const d = new Date(t.date + 'T12:00:00');
    return d.getMonth() === m && d.getFullYear() === y;
  });
  const income  = txns.filter(t => t.type === 'income').reduce((s,t)  => s + t.amount, 0);
  const expense = txns.filter(t => t.type === 'expense').reduce((s,t) => s + t.amount, 0);
  const balance = income - expense;

  document.getElementById('kpi-grid').innerHTML = `
    <div class="col-sm-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="subheader mb-1">Ingresos <span class="text-muted">${MONTHS[m]}</span></div>
          <div class="h1 mb-0 text-green">${fmt(income)}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="subheader mb-1">Gastos <span class="text-muted">${MONTHS[m]}</span></div>
          <div class="h1 mb-0 text-red">${fmt(expense)}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="subheader mb-1">Balance <span class="text-muted">neto del mes</span></div>
          <div class="h1 mb-0 ${balance >= 0 ? 'text-green' : 'text-red'}">${fmt(balance)}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-lg-3">
      <div class="card card-sm">
        <div class="card-body">
          <div class="subheader mb-1">Transacciones <span class="text-muted">este mes</span></div>
          <div class="h1 mb-0">${txns.length}</div>
        </div>
      </div>
    </div>`;

  const qeEl = document.getElementById('qe-list');
  if (!state.quickEntries.length) {
    qeEl.innerHTML = '<div class="p-4 text-center text-muted">Agrega accesos rápidos para un toque.</div>';
  } else {
    qeEl.innerHTML = '<div class="list-group list-group-flush">' + state.quickEntries.map(qe => {
      const cat = getCatById(qe.categoryId);
      return `<div class="list-group-item">
        <div class="row align-items-center g-2">
          <div class="col" onclick="triggerQE('${qe.id}')" style="cursor:pointer">
            <div class="d-flex align-items-center gap-2">
              <span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${cat?.color||'#999'};flex-shrink:0"></span>
              <div>
                <div class="fw-medium text-body">${esc(qe.name)}</div>
                <div class="text-muted small">${esc(cat?.name||'Sin categoría')}</div>
              </div>
            </div>
          </div>
          <div class="col-auto">
            <span class="fw-bold ${qe.type==='income' ? 'text-green' : 'text-red'}">${qe.type==='income'?'+':'-'}${fmt(qe.amount)}</span>
          </div>
          <div class="col-auto">
            <button onclick="deleteQE('${qe.id}')" class="btn btn-ghost-secondary btn-icon btn-sm" title="Eliminar">
              <i class="ti ti-x"></i>
            </button>
          </div>
        </div>
      </div>`;
    }).join('') + '</div>';
  }

  const recent = [...state.transactions]
    .sort((a,b) => b.date.localeCompare(a.date) || String(b.id).localeCompare(String(a.id)))
    .slice(0, 5);
  document.getElementById('recent-list').innerHTML = recent.length
    ? '<div class="list-group list-group-flush">' + recent.map(t => txnHTML(t, false)).join('') + '</div>'
    : '<div class="card-body text-center text-muted">Sin transacciones aún. Usa los botones de arriba.</div>';
}

function txnHTML(t, withDelete = true) {
  const cat = getCatById(t.categoryId);
  const initials = (t.description||'?').substring(0,2).toUpperCase();
  const colorClass = t.type === 'income' ? 'bg-green-lt text-green' : 'bg-red-lt text-red';
  const amtClass   = t.type === 'income' ? 'text-green' : 'text-red';
  return `<div class="list-group-item">
    <div class="row align-items-center g-2">
      <div class="col-auto">
        <span class="avatar avatar-sm ${colorClass}" style="font-size:11px;font-weight:700">${initials}</span>
      </div>
      <div class="col" onclick="openTxnEdit('${t.id}')" style="cursor:pointer">
        <div class="text-body fw-medium">${esc(t.description||'Sin descripción')}</div>
        <div class="text-muted small">${fmtDate(t.date)} · ${esc(cat?.name||'Sin cat.')}</div>
      </div>
      <div class="col-auto text-end">
        <div class="fw-bold ${amtClass}">${t.type==='income'?'+':'-'}${fmt(t.amount)}</div>
        ${withDelete ? `<a href="#" class="text-muted small" onclick="deleteTxn('${t.id}');return false">eliminar</a>` : ''}
      </div>
    </div>
  </div>`;
}

// ── MOVIMIENTOS ─────────────────────────────────────────
function renderMovements() {
  document.getElementById('month-label').textContent = `${MONTHS[currentMonth]} ${currentYear}`;
  let txns = state.transactions.filter(t => {
    const d = new Date(t.date + 'T12:00:00');
    return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
  });
  if (movFilter !== 'all') txns = txns.filter(t => t.type === movFilter);
  txns.sort((a,b) => b.date.localeCompare(a.date) || String(b.id).localeCompare(String(a.id)));
  document.getElementById('movements-list').innerHTML = txns.length
    ? '<div class="list-group list-group-flush">' + txns.map(t => txnHTML(t)).join('') + '</div>'
    : '<div class="card-body text-center text-muted">Sin movimientos para este período.</div>';
}

function setFilter(type, el) {
  movFilter = type;
  document.querySelectorAll('#section-movements .filter-chip').forEach(c => {
    c.classList.remove('btn-primary'); c.classList.add('btn-outline-primary');
  });
  el.classList.remove('btn-outline-primary'); el.classList.add('btn-primary');
  renderMovements();
}

function changeMonth(dir) {
  currentMonth += dir;
  if (currentMonth > 11) { currentMonth = 0; currentYear++; }
  if (currentMonth < 0)  { currentMonth = 11; currentYear--; }
  renderMovements();
}

function printMovements() { window.print(); }

function exportCSV() {
  const txns = state.transactions.filter(t => {
    const d = new Date(t.date + 'T12:00:00');
    return d.getMonth() === currentMonth && d.getFullYear() === currentYear;
  }).sort((a,b) => a.date.localeCompare(b.date));
  const rows = [['Fecha','Tipo','Descripcion','Categoria','Monto']];
  txns.forEach(t => {
    const cat = getCatById(t.categoryId);
    rows.push([t.date, t.type === 'income' ? 'Ingreso' : 'Gasto', t.description||'', cat?.name||'', t.amount]);
  });
  const a = document.createElement('a');
  a.href = 'data:text/csv;charset=utf-8,' + encodeURIComponent(rows.map(r => r.join(',')).join('\n'));
  a.download = `ledger_${MONTHS[currentMonth]}_${currentYear}.csv`;
  a.click();
}

// ── TRANSACCIONES CRUD ──────────────────────────────────
function openTxnEdit(id) {
  const t = state.transactions.find(x => String(x.id) === String(id));
  if (!t) return;
  editTxnId = String(t.id);
  setTxnType(t.type);
  document.getElementById('txn-amount').value = t.amount;
  document.getElementById('txn-desc').value   = t.description;
  document.getElementById('txn-date').value   = t.date;
  document.getElementById('modal-txn-title').textContent = 'Editar Transacción';
  setTimeout(() => { document.getElementById('txn-cat').value = t.categoryId; }, 30);
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-txn')).show();
}

function setTxnType(type) {
  txnType = type;
  const inc = document.getElementById('txn-type-income');
  const exp = document.getElementById('txn-type-expense');
  if (inc && exp) {
    inc.className = type === 'income' ? 'btn btn-success' : 'btn btn-outline-success';
    exp.className = type === 'expense' ? 'btn btn-danger' : 'btn btn-outline-danger';
  }
  populateCatSelect('txn-cat', type);
}

function populateCatSelect(selId, type) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const cats = state.categories.filter(c => c.type === type);
  sel.innerHTML = cats.length
    ? cats.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('')
    : '<option value="">Sin categorías</option>';
}

async function saveTxn() {
  const amount      = parseFloat(document.getElementById('txn-amount').value);
  const description = document.getElementById('txn-desc').value.trim();
  const categoryId  = document.getElementById('txn-cat').value;
  const date        = document.getElementById('txn-date').value;
  if (isNaN(amount) || amount <= 0) { shakeInput('txn-amount'); return; }
  if (!description)                 { shakeInput('txn-desc');   return; }
  if (!date)                        { shakeInput('txn-date');   return; }
  try {
    if (editTxnId) {
      const updated = await api('PUT', `transacciones/${editTxnId}/`, { type: txnType, amount, description, categoryId, date });
      const idx = state.transactions.findIndex(x => String(x.id) === editTxnId);
      if (idx >= 0) state.transactions[idx] = updated;
    } else {
      const created = await api('POST', 'transacciones/', { type: txnType, amount, description, categoryId, date });
      state.transactions.unshift(created);
    }
    closeModal('modal-txn');
    renderSection(currentSection);
  } catch(e) { alert('Error al guardar la transacción.'); }
}

async function deleteTxn(id) {
  if (!confirm('¿Eliminar esta transacción?')) return;
  try {
    await api('DELETE', `transacciones/${id}/`);
    state.transactions = state.transactions.filter(t => String(t.id) !== String(id));
    renderSection(currentSection);
  } catch(e) { alert('Error al eliminar.'); }
}

function shakeInput(id) {
  const el = document.getElementById(id);
  if (!el) return;
  el.classList.add('is-invalid');
  el.focus();
  setTimeout(() => el.classList.remove('is-invalid'), 1500);
}

// ── PENDIENTES ──────────────────────────────────────────
function renderPendientes() {
  let list = pendFilter === 'all' ? state.pendings : state.pendings.filter(p => p.type === pendFilter);
  list = [...list].sort((a,b) => a.date.localeCompare(b.date));
  document.getElementById('pendientes-list').innerHTML = list.length
    ? '<div class="list-group list-group-flush">' + list.map(p => `
      <div class="list-group-item">
        <div class="row align-items-center g-2">
          <div class="col">
            <div class="fw-medium text-body">${esc(p.name)}</div>
            <div class="text-muted small">${fmtDate(p.date)} · ${p.type === 'income' ? 'Por cobrar' : 'Por pagar'}</div>
          </div>
          <div class="col-auto">
            <span class="fw-bold ${p.type==='income' ? 'text-green' : 'text-red'}">${p.type==='income'?'+':'-'}${fmt(p.amount)}</span>
          </div>
          <div class="col-auto d-flex gap-1">
            <button class="btn btn-sm btn-success" onclick="confirmPending('${p.id}')">
              <i class="ti ti-check me-1"></i>Confirmar
            </button>
            <button class="btn btn-sm btn-icon btn-ghost-danger" onclick="deletePending('${p.id}')">
              <i class="ti ti-trash"></i>
            </button>
          </div>
        </div>
      </div>`).join('') + '</div>'
    : '<div class="card-body text-center text-muted">Sin pendientes registrados.</div>';
}

function setPendingFilter(type, el) {
  pendFilter = type;
  document.querySelectorAll('#section-pendientes .pending-chip').forEach(c => {
    c.classList.remove('btn-primary'); c.classList.add('btn-outline-primary');
  });
  el.classList.remove('btn-outline-primary'); el.classList.add('btn-primary');
  renderPendientes();
}

function openPendingModal(id) {
  editPendingId = id || null;
  const p = id ? state.pendings.find(x => String(x.id) === String(id)) : null;
  setPendingType(p?.type || 'income');
  document.getElementById('pending-name').value   = p?.name   || '';
  document.getElementById('pending-amount').value = p?.amount || '';
  document.getElementById('pending-date').value   = p?.date   || today();
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-pending')).show();
}

function setPendingType(type) {
  pendingType = type;
  const inc = document.getElementById('pending-type-income');
  const exp = document.getElementById('pending-type-expense');
  if (inc && exp) {
    inc.className = type === 'income' ? 'btn btn-success' : 'btn btn-outline-success';
    exp.className = type === 'expense' ? 'btn btn-danger' : 'btn btn-outline-danger';
  }
}

async function savePending() {
  const name   = document.getElementById('pending-name').value.trim();
  const amount = parseFloat(document.getElementById('pending-amount').value);
  const date   = document.getElementById('pending-date').value;
  if (!name || isNaN(amount) || amount <= 0 || !date) { alert('Completa todos los campos.'); return; }
  try {
    const created = await api('POST', 'pendientes/', { type: pendingType, name, amount, date });
    state.pendings.push(created);
    closeModal('modal-pending');
    renderPendientes();
  } catch(e) { alert('Error al guardar.'); }
}

async function deletePending(id) {
  try {
    await api('DELETE', `pendientes/${id}/`);
    state.pendings = state.pendings.filter(p => String(p.id) !== String(id));
    renderPendientes();
  } catch(e) { alert('Error al eliminar.'); }
}

async function confirmPending(id) {
  try {
    const txn = await api('POST', `pendientes/${id}/confirmar/`);
    state.transactions.unshift(txn);
    state.pendings = state.pendings.filter(p => String(p.id) !== String(id));
    renderPendientes();
  } catch(e) { alert('Error al confirmar pendiente.'); }
}

// ── CATEGORÍAS ──────────────────────────────────────────
function renderCategorias() {
  const el = document.getElementById('categorias-list');
  if (!state.categories.length) {
    el.innerHTML = '<div class="card-body text-center text-muted">Sin categorías.</div>';
    return;
  }
  let html = '<div class="list-group list-group-flush">';
  ['income','expense'].forEach(type => {
    const cats = state.categories.filter(c => c.type === type);
    if (!cats.length) return;
    html += `<div class="list-group-item bg-body-secondary py-2">
      <small class="text-uppercase fw-bold text-muted">${type === 'income' ? '▲ Ingresos' : '▼ Gastos'}</small>
    </div>`;
    html += cats.map(c => {
      const count = state.transactions.filter(t => String(t.categoryId) === String(c.id)).length;
      return `<div class="list-group-item">
        <div class="row align-items-center g-2">
          <div class="col-auto">
            <span style="display:inline-block;width:14px;height:14px;border-radius:50%;background:${c.color}"></span>
          </div>
          <div class="col">
            <div class="fw-medium text-body">${esc(c.name)}</div>
            <div class="text-muted small">${type === 'income' ? 'Ingreso' : 'Gasto'} · ${count} transacciones</div>
          </div>
          <div class="col-auto d-flex gap-1">
            <button class="btn btn-icon btn-sm btn-ghost-secondary" onclick="openCatModal('${c.id}')">
              <i class="ti ti-pencil"></i>
            </button>
            <button class="btn btn-icon btn-sm btn-ghost-danger" onclick="deleteCat('${c.id}')">
              <i class="ti ti-trash"></i>
            </button>
          </div>
        </div>
      </div>`;
    }).join('');
  });
  html += '</div>';
  el.innerHTML = html;
}

function openCatModal(id) {
  editCatId = id ? String(id) : null;
  const c = editCatId ? state.categories.find(x => String(x.id) === editCatId) : null;
  document.getElementById('modal-cat-title').textContent = editCatId ? 'Editar Categoría' : 'Nueva Categoría';
  setCatType(c?.type || 'expense');
  document.getElementById('cat-name').value = c?.name || '';
  renderColorPicker(c?.color || COLORS[0]);
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-cat')).show();
}

async function saveCat() {
  const name  = document.getElementById('cat-name').value.trim();
  const color = document.querySelector('.color-swatch.selected')?.dataset.color || COLORS[0];
  if (!name) { shakeInput('cat-name'); return; }
  try {
    if (editCatId) {
      const updated = await api('PUT', `categorias/${editCatId}/`, { name, type: catType, color });
      const idx = state.categories.findIndex(x => String(x.id) === editCatId);
      if (idx >= 0) state.categories[idx] = updated;
    } else {
      const created = await api('POST', 'categorias/', { name, type: catType, color });
      state.categories.push(created);
    }
    closeModal('modal-cat');
    renderCategorias();
  } catch(e) { alert('Error al guardar categoría.'); }
}

async function deleteCat(id) {
  const inUse = state.transactions.some(t => String(t.categoryId) === String(id));
  if (inUse && !confirm('Esta categoría tiene transacciones. ¿Eliminar de todas formas?')) return;
  try {
    await api('DELETE', `categorias/${id}/`);
    state.categories = state.categories.filter(c => String(c.id) !== String(id));
    renderCategorias();
  } catch(e) { alert('Error al eliminar.'); }
}

function setCatType(type) {
  catType = type;
  const inc = document.getElementById('cat-type-income');
  const exp = document.getElementById('cat-type-expense');
  if (inc && exp) {
    inc.className = type === 'income' ? 'btn btn-success' : 'btn btn-outline-success';
    exp.className = type === 'expense' ? 'btn btn-danger' : 'btn btn-outline-danger';
  }
}

function renderColorPicker(selected) {
  document.getElementById('color-picker').innerHTML = COLORS.map(c =>
    `<div class="color-swatch${c === selected ? ' selected' : ''}" data-color="${c}" style="background:${c}" onclick="selectColor('${c}')"></div>`
  ).join('');
}

function selectColor(c) {
  document.querySelectorAll('.color-swatch').forEach(s => s.classList.toggle('selected', s.dataset.color === c));
}

// ── PRESUPUESTOS ────────────────────────────────────────
function renderPresupuestos() {
  const el = document.getElementById('presupuestos-list');
  if (!state.budgets.length) {
    el.innerHTML = `<div class="card">
      <div class="card-body text-center text-muted py-5">
        <i class="ti ti-chart-pie fs-1 d-block mb-2"></i>
        <p>Sin presupuestos creados.</p>
        <button class="btn btn-primary" onclick="openBudgetModal()">
          <i class="ti ti-plus me-1"></i>Nuevo Presupuesto
        </button>
      </div>
    </div>`;
    return;
  }
  el.innerHTML = state.budgets.map(b => {
    const catIds = b.items.map(i => String(i.catId));
    const spent  = state.transactions
      .filter(t => t.type === 'expense' && catIds.includes(String(t.categoryId)))
      .reduce((s,t) => s + t.amount, 0);
    const pct      = b.limit > 0 ? Math.min((spent / b.limit) * 100, 100) : 0;
    const over     = spent > b.limit;
    const barColor = pct < 60 ? 'bg-success' : pct < 85 ? 'bg-warning' : 'bg-danger';
    const subs     = b.items.map(i => {
      const cat    = getCatById(i.catId);
      const cSpent = state.transactions.filter(t => String(t.categoryId) === String(i.catId) && t.type === 'expense').reduce((s,t) => s + t.amount, 0);
      return `<div class="d-flex justify-content-between py-1 small text-muted border-bottom">
        <span>${esc(cat?.name||'—')}</span><span>${fmt(cSpent)}</span>
      </div>`;
    }).join('');
    return `<div class="card mb-3">
      <div class="card-header">
        <h3 class="card-title">${esc(b.name)}</h3>
        <div class="card-options">
          <span class="text-muted small me-2">Límite: ${fmt(b.limit)}</span>
          <button class="btn btn-icon btn-sm btn-ghost-danger" onclick="deleteBudget('${b.id}')">
            <i class="ti ti-trash"></i>
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="progress mb-2" style="height:8px">
          <div class="progress-bar ${barColor}" style="width:${pct}%"></div>
        </div>
        <div class="d-flex justify-content-between small mb-2">
          <span class="text-muted">Gastado: ${fmt(spent)}</span>
          <span class="${over ? 'text-danger fw-bold' : 'text-success fw-bold'}">${over ? `Excedido: ${fmt(spent - b.limit)}` : `Disponible: ${fmt(b.limit - spent)}`}</span>
        </div>
        ${subs ? `<div class="mt-2">${subs}</div>` : ''}
      </div>
    </div>`;
  }).join('');
}

function openBudgetModal() {
  document.getElementById('budget-name').value  = '';
  document.getElementById('budget-limit').value = '';
  document.getElementById('budget-items-form').innerHTML = '';
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-budget')).show();
}

function addBudgetItem() {
  const div = document.createElement('div');
  div.className = 'd-flex gap-2 mb-2 align-items-center';
  const cats = state.categories.filter(c => c.type === 'expense');
  div.innerHTML = `<select class="form-select budget-item-cat">
    ${cats.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('')}
  </select>
  <button type="button" onclick="this.parentElement.remove()" class="btn btn-icon btn-sm btn-ghost-danger flex-shrink-0">
    <i class="ti ti-x"></i>
  </button>`;
  document.getElementById('budget-items-form').appendChild(div);
}

async function saveBudget() {
  const name  = document.getElementById('budget-name').value.trim();
  const limit = parseFloat(document.getElementById('budget-limit').value);
  if (!name || isNaN(limit) || limit <= 0) { alert('Completa nombre y monto límite.'); return; }
  const items = Array.from(document.querySelectorAll('.budget-item-cat')).map(s => ({ catId: s.value }));
  try {
    const created = await api('POST', 'presupuestos/', { name, limit, items });
    state.budgets.push(created);
    closeModal('modal-budget');
    renderPresupuestos();
  } catch(e) { alert('Error al guardar presupuesto.'); }
}

async function deleteBudget(id) {
  try {
    await api('DELETE', `presupuestos/${id}/`);
    state.budgets = state.budgets.filter(b => String(b.id) !== String(id));
    renderPresupuestos();
  } catch(e) { alert('Error al eliminar.'); }
}

// ── METAS DE AHORRO ─────────────────────────────────────
function renderMetas() {
  const el = document.getElementById('metas-list');
  if (!state.goals.length) {
    el.innerHTML = `<div class="card">
      <div class="card-body text-center text-muted py-5">
        <i class="ti ti-target fs-1 d-block mb-2"></i>
        <p>Sin metas de ahorro creadas.</p>
        <button class="btn btn-primary" onclick="openGoalModal()">
          <i class="ti ti-plus me-1"></i>Nueva Meta
        </button>
      </div>
    </div>`;
    return;
  }
  el.innerHTML = state.goals.map(g => {
    const pct      = g.target > 0 ? Math.min((g.saved / g.target) * 100, 100) : 0;
    const done     = g.saved >= g.target;
    const left     = Math.max(g.target - g.saved, 0);
    const barColor = done ? 'bg-success' : 'bg-warning';
    return `<div class="card mb-3">
      <div class="card-header">
        <h3 class="card-title">
          <span class="me-2" style="font-size:1.3em">${g.emoji||'🎯'}</span>${esc(g.name)}
        </h3>
        <div class="card-options">
          <button class="btn btn-icon btn-sm btn-ghost-secondary me-1" onclick="openGoalModal('${g.id}')">
            <i class="ti ti-pencil"></i>
          </button>
          <button class="btn btn-icon btn-sm btn-ghost-danger" onclick="deleteGoal('${g.id}')">
            <i class="ti ti-trash"></i>
          </button>
        </div>
      </div>
      <div class="card-body">
        <div class="progress mb-2" style="height:10px">
          <div class="progress-bar ${barColor}" style="width:${pct}%"></div>
        </div>
        <div class="d-flex justify-content-between small mb-2">
          <span>Ahorrado: <strong>${fmt(g.saved)}</strong></span>
          <span class="fw-bold ${done ? 'text-success' : 'text-warning'}">${pct.toFixed(0)}%</span>
          <span>Meta: ${fmt(g.target)}</span>
        </div>
        ${g.deadline ? `<div class="text-muted small mb-2"><i class="ti ti-calendar me-1"></i>Fecha límite: ${fmtDate(g.deadline)}</div>` : ''}
        ${done
          ? `<div class="alert alert-success py-2 mb-0">¡Meta alcanzada! 🎉</div>`
          : `<div class="input-group mt-2">
               <input type="number" placeholder="Agregar ahorro…" id="add-savings-${g.id}" class="form-control" inputmode="decimal" min="0" step="0.01">
               <button class="btn btn-warning" onclick="addSavings('${g.id}')">+ Agregar</button>
             </div>
             ${left > 0 ? `<div class="text-muted small mt-1">Faltan ${fmt(left)} para alcanzar la meta</div>` : ''}`
        }
      </div>
    </div>`;
  }).join('');
}

function openGoalModal(id) {
  editGoalId = id ? String(id) : null;
  const g = editGoalId ? state.goals.find(x => String(x.id) === editGoalId) : null;
  const titleEl = document.querySelector('#modal-goal .modal-title');
  if (titleEl) titleEl.textContent = editGoalId ? 'Editar Meta' : 'Nueva Meta de Ahorro';
  document.getElementById('goal-name').value     = g?.name     || '';
  document.getElementById('goal-target').value   = g?.target   || '';
  document.getElementById('goal-deadline').value = g?.deadline || '';
  document.getElementById('goal-emoji').value    = g?.emoji    || '🎯';
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-goal')).show();
}

async function saveGoal() {
  const name     = document.getElementById('goal-name').value.trim();
  const target   = parseFloat(document.getElementById('goal-target').value);
  const deadline = document.getElementById('goal-deadline').value;
  const emoji    = document.getElementById('goal-emoji').value.trim() || '🎯';
  if (!name || isNaN(target) || target <= 0) { alert('Completa nombre y monto objetivo.'); return; }
  try {
    if (editGoalId) {
      const updated = await api('PUT', `metas/${editGoalId}/`, { name, target, deadline, emoji });
      const idx = state.goals.findIndex(x => String(x.id) === editGoalId);
      if (idx >= 0) state.goals[idx] = updated;
    } else {
      const created = await api('POST', 'metas/', { name, target, deadline, emoji });
      state.goals.push(created);
    }
    closeModal('modal-goal');
    renderMetas();
  } catch(e) { alert('Error al guardar meta.'); }
}

async function addSavings(id) {
  const inp    = document.getElementById('add-savings-' + id);
  const amount = parseFloat(inp?.value);
  if (!inp || isNaN(amount) || amount <= 0) return;
  try {
    const result = await api('POST', `metas/${id}/ahorrar/`, { amount });
    const idx = state.goals.findIndex(x => String(x.id) === String(id));
    if (idx >= 0) state.goals[idx] = result.meta;
    state.transactions.unshift(result.txn);
    renderMetas();
  } catch(e) { alert('Error al agregar ahorro.'); }
}

async function deleteGoal(id) {
  if (!confirm('¿Eliminar esta meta?')) return;
  try {
    await api('DELETE', `metas/${id}/`);
    state.goals = state.goals.filter(g => String(g.id) !== String(id));
    renderMetas();
  } catch(e) { alert('Error al eliminar.'); }
}

// ── ENTRADAS RÁPIDAS ────────────────────────────────────
function setQEType(type) {
  qeType = type;
  const inc = document.getElementById('qe-type-income');
  const exp = document.getElementById('qe-type-expense');
  if (inc && exp) {
    inc.className = type === 'income' ? 'btn btn-success' : 'btn btn-outline-success';
    exp.className = type === 'expense' ? 'btn btn-danger' : 'btn btn-outline-danger';
  }
  populateCatSelect('qe-cat', type);
}

async function saveQE() {
  const name       = document.getElementById('qe-name').value.trim();
  const amount     = parseFloat(document.getElementById('qe-amount').value);
  const categoryId = document.getElementById('qe-cat').value;
  if (!name || isNaN(amount) || amount <= 0) { alert('Completa nombre y monto.'); return; }
  try {
    const created = await api('POST', 'quick-entries/', { name, amount, type: qeType, categoryId });
    state.quickEntries.push(created);
    closeModal('modal-qe');
    renderDashboard();
  } catch(e) { alert('Error al guardar entrada rápida.'); }
}

async function deleteQE(id) {
  try {
    await api('DELETE', `quick-entries/${id}/`);
    state.quickEntries = state.quickEntries.filter(q => String(q.id) !== String(id));
    renderDashboard();
  } catch(e) { alert('Error al eliminar.'); }
}

function triggerQE(id) {
  const qe = state.quickEntries.find(x => String(x.id) === String(id));
  if (!qe) return;
  pendingQE = qe;
  document.getElementById('qe-confirm-text').textContent = `Registrar "${qe.name}" como ${qe.type === 'income' ? 'ingreso' : 'gasto'}`;
  const amEl = document.getElementById('qe-confirm-amount');
  amEl.textContent = (qe.type === 'income' ? '+' : '-') + fmt(qe.amount);
  amEl.className = 'h2 fw-bold mb-4 ' + (qe.type === 'income' ? 'text-green' : 'text-red');
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-qe-confirm')).show();
}

async function executeQE() {
  if (!pendingQE) return;
  try {
    const txn = await api('POST', `quick-entries/${pendingQE.id}/ejecutar/`);
    state.transactions.unshift(txn);
    bootstrap.Modal.getInstance(document.getElementById('modal-qe-confirm'))?.hide();
    renderDashboard();
    pendingQE = null;
  } catch(e) { alert('Error al ejecutar entrada rápida.'); }
}

// ── RESPALDO ────────────────────────────────────────────
function renderRespaldo() {
  document.getElementById('backup-stats').innerHTML = [
    { num: state.transactions.length, label: 'Transacciones' },
    { num: state.categories.length,   label: 'Categorías'    },
    { num: state.pendings.length,      label: 'Pendientes'   },
    { num: state.goals.length,         label: 'Metas'        },
  ].map(s => `<div class="col-6 col-md-3">
    <div class="card card-sm">
      <div class="card-body text-center">
        <div class="h1 mb-0">${s.num}</div>
        <div class="text-muted small">${s.label}</div>
      </div>
    </div>
  </div>`).join('');

  document.getElementById('currency-select').value  = state.settings?.currency || 'L';
  document.getElementById('theme-checkbox').checked = (state.settings?.theme || 'light') === 'dark';
  document.getElementById('json-preview').textContent = JSON.stringify(state, null, 2).slice(0, 1500) + '\n…';

  const drop = document.getElementById('drop-area');
  if (drop && !drop._ddInit) {
    drop._ddInit = true;
    drop.addEventListener('dragover', e => { e.preventDefault(); drop.classList.add('dragover'); });
    drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
    drop.addEventListener('drop', e => {
      e.preventDefault(); drop.classList.remove('dragover');
      if (e.dataTransfer.files[0]) handleFileImport({ files: e.dataTransfer.files });
    });
  }
}

function downloadBackup() {
  const a = document.createElement('a');
  a.href = 'data:application/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(state, null, 2));
  a.download = `ledger_backup_${today()}.json`;
  a.click();
}

async function handleFileImport(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async e => {
    try {
      const data = JSON.parse(e.target.result);
      if (confirm('Esto reemplazará todos los datos actuales. ¿Continuar?')) {
        await api('POST', 'importar/', data);
        state = await api('GET', 'data/');
        applyTheme();
        renderRespaldo();
        alert('Datos restaurados correctamente.');
      }
    } catch { alert('Archivo JSON inválido o error al importar.'); }
  };
  reader.readAsText(file);
  if (input.value !== undefined) input.value = '';
}

function confirmClearAll() {
  document.getElementById('danger-modal-title').textContent = 'Eliminar todos los datos';
  document.getElementById('danger-modal-text').textContent  = 'Se borrarán todas las transacciones, categorías, metas y pendientes. Esta acción no se puede deshacer.';
  document.getElementById('danger-modal-confirm-btn').onclick = async () => {
    try {
      await api('POST', 'limpiar/');
      state = await api('GET', 'data/');
      bootstrap.Modal.getInstance(document.getElementById('modal-confirm-danger'))?.hide();
      applyTheme();
      renderSection(currentSection);
    } catch(e) { alert('Error al limpiar datos.'); }
  };
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modal-confirm-danger')).show();
}

async function setCurrency(val) {
  try {
    const cfg = await api('POST', 'configuracion/', { currency: val });
    state.settings.currency = cfg.currency;
    renderSection(currentSection);
  } catch(e) {}
}

async function toggleTheme(checked) {
  try {
    const cfg = await api('POST', 'configuracion/', { theme: checked ? 'dark' : 'light' });
    state.settings.theme = cfg.theme;
    applyTheme();
  } catch(e) {}
}

function applyTheme() {
  const dark = (state.settings?.theme || 'light') === 'dark';
  document.documentElement.setAttribute('data-bs-theme', dark ? 'dark' : 'light');
  const cb = document.getElementById('theme-checkbox');
  if (cb) cb.checked = dark;
}

document.getElementById('theme-toggle')?.addEventListener('click', () => {
  const isDark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
  toggleTheme(!isDark);
});

async function init() {
  try { await loadFromServer(); } catch(e) { console.error('Error cargando datos:', e); }
  applyTheme();
  setQEType('expense');
  setTxnType('income');
  renderDashboard();
}

init();
