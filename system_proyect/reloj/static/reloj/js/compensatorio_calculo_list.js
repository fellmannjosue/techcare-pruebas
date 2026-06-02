// ── Cálculo compensatorio — 5 tabs ──  // <--- hecho por claude code
const CSRF = window._PAGE.csrf;
const minToH = m => +(m / 60).toFixed(1);

function jpost(url, payload) {
  return fetch(url, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
    body: JSON.stringify(payload || {}),
  }).then(r => r.json());
}

// ── DataTables + tabs + año ──
let dt1 = null, dt2 = null;
document.addEventListener('DOMContentLoaded', function () {
  if (typeof $.fn.DataTable !== 'undefined') {
    const lang = { url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json' };
    if (document.getElementById('tabla-calculo'))  dt1 = $('#tabla-calculo').DataTable({ order: [], pageLength: 25, language: lang });
    if (document.getElementById('tabla-calculo2')) dt2 = $('#tabla-calculo2').DataTable({ order: [], pageLength: 25, language: lang });
  }

  // Activar tab desde el hash
  const hash = location.hash;
  if (hash) {
    const tb = document.querySelector(`#comp-tabs button[data-bs-target="${hash}"]`);
    if (tb) new bootstrap.Tab(tb).show();
  }
  // Guardar tab activo + ajustar DataTables
  document.querySelectorAll('#comp-tabs button[data-bs-toggle="tab"]').forEach(b => {
    b.addEventListener('shown.bs.tab', function (e) {
      history.replaceState(null, '', e.target.dataset.bsTarget);
      if (e.target.dataset.bsTarget === '#tab1' && dt1) dt1.columns.adjust();
      if (e.target.dataset.bsTarget === '#tab2' && dt2) dt2.columns.adjust();
    });
  });
  // Selector de año (recarga preservando tab)
  const anioSel = document.getElementById('anio-sel');
  if (anioSel) anioSel.addEventListener('change', function () {
    const u = new URL(location.href);
    u.searchParams.set('anio', this.value);
    u.hash = location.hash || '#tab3';
    location.href = u.toString();
  });
});

// ══════════════ TABS 1-2: edición de adeudados ══════════════
(function () {
  function updateSaldoBadge(pk, saldoMin) {
    const b = document.querySelector(`.saldo-badge-${pk}`);
    if (!b) return;
    if (saldoMin === 0) {
      b.className = `badge bg-green-lt text-green saldo-badge-${pk}`;
      b.innerHTML = '<i class="ti ti-circle-check me-1"></i>Completado';
    } else {
      b.className = `badge bg-red-lt text-red saldo-badge-${pk}`;
      b.textContent = `${minToH(saldoMin)} h`;
    }
  }
  function updateRowTotals(pk, data) {
    document.querySelectorAll(`.total-hrs-${pk}`).forEach(c => c.textContent = `${data.total_hrs} h`);
    const row = document.querySelector(`tr[data-pk="${pk}"]`);
    if (row) row.dataset.totalMin = data.total_min;
    if (data.saldo_min !== undefined) updateSaldoBadge(pk, data.saldo_min);
    const hab = document.querySelector(`.dias-hab-badge-${pk}`);
    if (hab && data.dias_hab !== undefined) hab.textContent = `${data.dias_hab} días`;
  }

  // helper genérico para modales de un solo campo
  function bindEditModal(opts) {
    let modal = null, activePk = null;
    document.querySelectorAll(opts.btnSel).forEach(btn => {
      btn.addEventListener('click', function () {
        activePk = this.dataset.pk;
        document.getElementById(opts.nombreEl).textContent = this.dataset.nombre || '';
        document.getElementById(opts.inputEl).value = this.dataset.valor || '';
        if (!modal) modal = new bootstrap.Modal(document.getElementById(opts.modalId));
        modal.show();
      });
    });
    document.getElementById(opts.saveBtn)?.addEventListener('click', async function () {
      const inp = document.getElementById(opts.inputEl);
      const raw = inp.value;
      const btn = this; btn.disabled = true;
      const data = await jpost(opts.url.replace('{pk}', activePk), opts.payload(raw));
      btn.disabled = false;
      if (data.ok) { opts.onOk(activePk, raw, data); if (modal) modal.hide(); }
      else { inp.classList.add('is-invalid'); }
    });
  }

  // Días adeudados (informativo)
  bindEditModal({
    btnSel: '.btn-set-dias-adeudados', modalId: 'modalDiasAdeudados', nombreEl: 'da-nombre',
    inputEl: 'da-input', saveBtn: 'btn-guardar-dias-adeudados',
    url: '/reloj/compensatorio-calculo/{pk}/set-dias-adeudados/',
    payload: raw => ({ dias: parseFloat(raw) || 0 }),
    onOk: (pk, raw, data) => {
      document.querySelector(`.dias-adeudados-badge-${pk}`).textContent = data.dias;
      const b = document.querySelector(`.btn-set-dias-adeudados[data-pk="${pk}"]`); if (b) b.dataset.valor = data.dias;
      updateRowTotals(pk, data);
    },
  });
  // Horas adeudadas (directo)
  bindEditModal({
    btnSel: '.btn-set-horas-adeudadas', modalId: 'modalHorasAdeudadas', nombreEl: 'ha-nombre',
    inputEl: 'ha-input', saveBtn: 'btn-guardar-horas-adeudadas',
    url: window._PAGE.urlSetHorasAdeudadas,
    payload: raw => ({ horas: parseFloat(raw) || 0 }),
    onOk: (pk, raw, data) => {
      const hc = document.querySelector(`.horas-adeudadas-${pk}`); if (hc) hc.textContent = `${data.horas_adeudadas} h`;
      const b = document.querySelector(`.btn-set-horas-adeudadas[data-pk="${pk}"]`); if (b) b.dataset.valor = data.horas_adeudadas;
      updateRowTotals(pk, data);
    },
  });
  // Permisos extras
  bindEditModal({
    btnSel: '.btn-set-permisos-extras', modalId: 'modalPermisosExtras', nombreEl: 'pe-nombre',
    inputEl: 'pe-input', saveBtn: 'btn-guardar-permisos-extras',
    url: '/reloj/compensatorio-calculo/{pk}/set-permisos-extras/',
    payload: raw => ({ horas: parseFloat(raw) || 0 }),
    onOk: (pk, raw, data) => {
      const v = parseFloat(raw) || 0;
      const badge = document.querySelector(`.permisos-extras-badge-${pk}`); if (badge) badge.textContent = v > 0 ? `${v} h` : '—';
      const b = document.querySelector(`.btn-set-permisos-extras[data-pk="${pk}"]`); if (b) b.dataset.valor = v;
      updateRowTotals(pk, data);
    },
  });
  // Tiempo extra tomado (detalle permiso compensatorio + override)
  let modalTom = null, tomPk = null;
  function renderTomado(entries) {
    const tbody = document.getElementById('tom-tbody'), empty = document.getElementById('tom-empty');
    tbody.querySelectorAll('tr:not(#tom-empty)').forEach(r => r.remove());
    if (!entries.length) { empty.style.display = ''; return; }
    empty.style.display = 'none';
    entries.forEach(e => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="text-center font-monospace small">${e.fecha}</td><td class="text-center fw-semibold text-pink">${e.horas} h</td><td class="text-muted small">${e.razon}</td>`;
      tbody.appendChild(tr);
    });
  }
  document.querySelectorAll('.btn-set-tomado').forEach(btn => {
    btn.addEventListener('click', async function () {
      tomPk = this.dataset.pk;
      document.getElementById('tom-nombre').textContent = this.dataset.nombre || '';
      const inp = document.getElementById('tom-input');
      if (inp) inp.value = this.dataset.valor || '';
      if (!modalTom) modalTom = new bootstrap.Modal(document.getElementById('modalTomado'));
      modalTom.show();
      const d = await (await fetch(window._PAGE.urlGetTomado.replace('{pk}', tomPk))).json();
      if (d.ok) {
        renderTomado(d.entries);
        document.getElementById('tom-total-permiso').textContent = d.total_permiso;
        if (inp) inp.placeholder = `Vacío = usar permiso (${d.total_permiso} h)`;
      }
    });
  });
  document.getElementById('btn-guardar-tomado')?.addEventListener('click', async function () {
    const inp = document.getElementById('tom-input');
    const raw = inp.value;
    this.disabled = true;
    const data = await jpost(window._PAGE.urlSetTomado.replace('{pk}', tomPk), { horas: raw === '' ? '' : (parseFloat(raw) || 0) });
    this.disabled = false;
    if (data.ok) {
      const badge = document.querySelector(`.tomado-badge-${tomPk}`);
      if (badge) {
        badge.className = `badge ${data.es_override ? 'bg-yellow-lt text-yellow' : 'bg-pink-lt text-pink'} tomado-badge-${tomPk}`;
        badge.innerHTML = `<i class="ti ti-calendar-minus me-1"></i>${data.tomado_hrs > 0 ? data.tomado_hrs + ' h' : '—'}`;
      }
      const b = document.querySelector(`.btn-set-tomado[data-pk="${tomPk}"]`); if (b) b.dataset.valor = data.es_override ? data.tomado_hrs : '';
      const row = document.querySelector(`tr[data-pk="${tomPk}"]`); if (row) row.dataset.tomadoMin = data.tomado_hrs * 60;
      updateSaldoBadge(tomPk, data.saldo_min);
      if (modalTom) modalTom.hide();
    }
  });

  // Min. autorizados/día (POST form-urlencoded)
  let modalMD = null, mdPk = null;
  document.querySelectorAll('.btn-set-min-dia').forEach(btn => {
    btn.addEventListener('click', function () {
      mdPk = this.dataset.pk;
      document.getElementById('min-dia-nombre').textContent = this.dataset.nombre;
      document.getElementById('min-dia-input').value = this.dataset.valor || '';
      if (!modalMD) modalMD = new bootstrap.Modal(document.getElementById('modalMinDia'));
      modalMD.show();
    });
  });
  document.getElementById('btn-guardar-min-dia')?.addEventListener('click', async function () {
    const valor = parseInt(document.getElementById('min-dia-input').value);
    if (!valor || valor <= 0) { document.getElementById('min-dia-input').classList.add('is-invalid'); return; }
    const btn = this; btn.disabled = true;
    const res = await fetch(`/reloj/compensatorio-calculo/${mdPk}/set-min-dia/`, {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ csrfmiddlewaretoken: CSRF, minutos: valor }),
    });
    const data = await res.json(); btn.disabled = false;
    if (data.ok) {
      document.querySelectorAll(`.min-dia-badge-${mdPk}`).forEach(b => b.textContent = `${data.minutos_dia} min`);
      const hab = document.querySelector(`.dias-hab-badge-${mdPk}`); if (hab) hab.textContent = `${data.dias_habiles} días`;
      document.querySelectorAll(`.fecha-fin-badge-${mdPk}`).forEach(ff => { ff.className = `badge bg-green-lt text-green fecha-fin-badge-${mdPk}`; ff.innerHTML = `<i class="ti ti-calendar-check me-1"></i>${data.fecha_fin}`; });
      if (modalMD) modalMD.hide();
    }
  });

  // ── Días no laborables ANA (modal lista) ──
  let modalDNL = null, dnlPk = null;
  const canEdit = window._PAGE.canEdit;
  function renderDNL(dias) {
    const tbody = document.getElementById('dnl-tbody'), empty = document.getElementById('dnl-empty');
    tbody.querySelectorAll('tr:not(#dnl-empty)').forEach(r => r.remove());
    if (!dias.length) { empty.style.display = ''; return; }
    empty.style.display = 'none';
    dias.forEach(d => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="text-muted small">${d.descripcion || '—'}</td><td class="text-center fw-semibold text-orange">${d.horas} h</td>${canEdit ? `<td class="text-center"><button class="btn btn-sm btn-ghost-danger btn-dnl-del" data-id="${d.id}"><i class="ti ti-trash"></i></button></td>` : ''}`;
      tbody.appendChild(tr);
    });
  }
  function updateDNLTotals(totalHrs) {
    const dias = totalHrs > 0 ? +(totalHrs / 8).toFixed(2) : 0;
    document.getElementById('dnl-total-hrs').textContent = totalHrs;
    document.getElementById('dnl-total-dias').textContent = dias;
    const badge = document.querySelector(`.dias-no-lab-badge-${dnlPk}`);
    if (badge) badge.innerHTML = `<i class="ti ti-edit me-1"></i>${dias > 0 ? dias + ' días' : '—'}`;
  }
  async function reloadDNL() {
    const d = await (await fetch(`/reloj/compensatorio-calculo/${dnlPk}/dias-no-lab/`)).json();
    if (d.ok) { renderDNL(d.dias); updateDNLTotals(d.total_hrs); }
  }
  document.querySelectorAll('.btn-dias-no-lab').forEach(btn => {
    btn.addEventListener('click', async function () {
      dnlPk = this.dataset.pk;
      document.getElementById('dnl-nombre').textContent = this.dataset.nombre;
      if (document.getElementById('dnl-horas')) document.getElementById('dnl-horas').value = '8.8';
      if (document.getElementById('dnl-desc')) document.getElementById('dnl-desc').value = '';
      if (!modalDNL) modalDNL = new bootstrap.Modal(document.getElementById('modalDiasNoLab'));
      modalDNL.show(); reloadDNL();
    });
  });
  document.getElementById('btn-dnl-add')?.addEventListener('click', async function () {
    const horas = parseFloat(document.getElementById('dnl-horas').value);
    const desc = document.getElementById('dnl-desc').value;
    const err = document.getElementById('dnl-add-error');
    if (!horas || horas <= 0) { err.querySelector('.alert').textContent = 'Horas inválidas.'; err.classList.remove('d-none'); return; }
    err.classList.add('d-none'); this.disabled = true;
    await jpost(`/reloj/compensatorio-calculo/${dnlPk}/dias-no-lab/add/`, { horas, descripcion: desc });
    this.disabled = false;
    document.getElementById('dnl-horas').value = '8.8'; document.getElementById('dnl-desc').value = '';
    reloadDNL();
  });
  document.getElementById('dnl-tbody')?.addEventListener('click', async function (e) {
    const btn = e.target.closest('.btn-dnl-del'); if (!btn) return;
    btn.disabled = true;
    await fetch(`/reloj/compensatorio-dias-no-lab/${btn.dataset.id}/delete/`, { method: 'POST', headers: { 'X-CSRFToken': CSRF } });
    reloadDNL();
  });

  // ── Tiempo extra autorizado (modal lista, informativo) ──
  let modalTE = null, tePk = null;
  function renderTE(entries) {
    const tbody = document.getElementById('te-tbody'), empty = document.getElementById('te-empty');
    tbody.querySelectorAll('tr:not(#te-empty)').forEach(r => r.remove());
    if (!entries.length) { empty.style.display = ''; return; }
    empty.style.display = 'none';
    entries.forEach(e => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="text-center font-monospace small">${e.fecha}</td><td class="text-center fw-semibold text-cyan">${e.minutos} min</td><td class="text-muted small">${e.razon}</td>${canEdit ? `<td class="text-center"><button class="btn btn-sm btn-ghost-danger btn-te-del" data-te-pk="${e.pk}"><i class="ti ti-trash"></i></button></td>` : ''}`;
      tbody.appendChild(tr);
    });
  }
  function updateTEBadge(totalMin, totalHrs) {
    document.getElementById('te-total-min').textContent = totalMin;
    document.getElementById('te-total-hrs').textContent = totalHrs;
    const badge = document.querySelector(`.te-badge-${tePk}`);
    if (badge) badge.innerHTML = `<i class="ti ti-clock-bolt me-1"></i>${totalMin > 0 ? totalHrs + ' h' : '—'}`;
  }
  document.querySelectorAll('.btn-te-modal').forEach(btn => {
    btn.addEventListener('click', async function () {
      tePk = this.dataset.pk;
      document.getElementById('te-nombre').textContent = this.dataset.nombre;
      if (!modalTE) modalTE = new bootstrap.Modal(document.getElementById('modalTiempoExtra'));
      modalTE.show();
      const d = await (await fetch(window._PAGE.urlTeGet.replace('{pk}', tePk))).json();
      if (d.ok) { renderTE(d.entries); updateTEBadge(d.total_min, d.total_hrs); }
    });
  });
  document.getElementById('te-tbody')?.addEventListener('click', async function (e) {
    const btn = e.target.closest('.btn-te-del'); if (!btn) return;
    btn.disabled = true;
    const d = await (await fetch(window._PAGE.urlTeDel.replace('{te_pk}', btn.dataset.tePk), { method: 'POST', headers: { 'X-CSRFToken': CSRF } })).json();
    if (d.ok) { renderTE(d.entries); updateTEBadge(d.total_min, d.total_hrs); }
  });
})();

// ══════════════ Bulk (tab 1) ══════════════
if (window._PAGE.canEdit) (function () {
  const getChecked = () => [...document.querySelectorAll('.chk-emp:checked')];
  function updateBar() {
    const n = getChecked().length, bar = document.getElementById('bulk-bar');
    if (bar) { bar.style.display = n > 0 ? 'flex' : 'none'; document.getElementById('bulk-count').textContent = n; }
  }
  document.getElementById('chk-all')?.addEventListener('change', function () {
    document.querySelectorAll('.chk-emp').forEach(c => c.checked = this.checked); updateBar();
  });
  document.querySelectorAll('.chk-emp').forEach(c => c.addEventListener('change', updateBar));

  let modalBulk = null;
  document.getElementById('btn-bulk-dias-no-lab')?.addEventListener('click', function () {
    const n = getChecked().length; if (!n) return;
    document.getElementById('bulk-dnl-count').textContent = n;
    document.getElementById('bulk-dnl-horas').value = '8.8';
    document.getElementById('bulk-dnl-desc').value = '';
    document.getElementById('bulk-dnl-error').classList.add('d-none');
    document.getElementById('bulk-dnl-progress').classList.add('d-none');
    if (!modalBulk) modalBulk = new bootstrap.Modal(document.getElementById('modalBulkDiasNoLab'));
    modalBulk.show();
  });
  document.getElementById('btn-bulk-dnl-apply')?.addEventListener('click', async function () {
    const horas = parseFloat(document.getElementById('bulk-dnl-horas').value);
    const desc = document.getElementById('bulk-dnl-desc').value.trim();
    const err = document.getElementById('bulk-dnl-error');
    if (!horas || horas <= 0) { err.querySelector('.alert').textContent = 'Horas inválidas.'; err.classList.remove('d-none'); return; }
    const checked = getChecked(); this.disabled = true;
    const prog = document.getElementById('bulk-dnl-progress'), bar = document.getElementById('bulk-dnl-bar'), st = document.getElementById('bulk-dnl-status');
    prog.classList.remove('d-none');
    for (let i = 0; i < checked.length; i++) {
      const pk = checked[i].dataset.pk;
      st.textContent = `Procesando ${i + 1} de ${checked.length}...`;
      bar.style.width = `${Math.round((i / checked.length) * 100)}%`;
      await jpost(`/reloj/compensatorio-calculo/${pk}/dias-no-lab/add/`, { horas, descripcion: desc });
      const d2 = await (await fetch(`/reloj/compensatorio-calculo/${pk}/dias-no-lab/`)).json();
      if (d2.ok) {
        const dias = d2.total_hrs > 0 ? +(d2.total_hrs / 8).toFixed(2) : 0;
        const badge = document.querySelector(`.dias-no-lab-badge-${pk}`);
        if (badge) badge.innerHTML = `<i class="ti ti-edit me-1"></i>${dias > 0 ? dias + ' días' : '—'}`;
      }
    }
    bar.style.width = '100%'; st.textContent = '¡Completado!'; this.disabled = false;
    setTimeout(() => { if (modalBulk) modalBulk.hide(); }, 800);
  });

  document.getElementById('btn-bulk-3dias')?.addEventListener('click', async function () {
    const checked = getChecked(); if (!checked.length) return;
    this.disabled = true; this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Aplicando...';
    for (const chk of checked) {
      const pk = chk.dataset.pk, factor = parseFloat(chk.dataset.factor) || 8.0;
      const horas = Math.round(3 * factor * 100) / 100;
      const data = await jpost(`/reloj/compensatorio-calculo/${pk}/set-permisos-extras/`, { horas });
      if (data.ok) {
        const badge = document.querySelector(`.permisos-extras-badge-${pk}`); if (badge) badge.textContent = `${horas} h`;
        const b = document.querySelector(`.btn-set-permisos-extras[data-pk="${pk}"]`); if (b) b.dataset.valor = horas;
        document.querySelectorAll(`.total-hrs-${pk}`).forEach(c => c.textContent = `${data.total_hrs} h`);
        const hab = document.querySelector(`.dias-hab-badge-${pk}`); if (hab) hab.textContent = `${data.dias_hab} días`;
        const saldo = document.querySelector(`.saldo-badge-${pk}`);
        if (saldo && data.saldo_min !== undefined) {
          if (data.saldo_min === 0) { saldo.className = `badge bg-green-lt text-green saldo-badge-${pk}`; saldo.innerHTML = '<i class="ti ti-circle-check me-1"></i>Completado'; }
          else { saldo.className = `badge bg-red-lt text-red saldo-badge-${pk}`; saldo.textContent = `${minToH(data.saldo_min)} h`; }
        }
      }
    }
    this.disabled = false; this.innerHTML = '<i class="ti ti-clock-plus me-1"></i>Aplicar 3 días perm. extras';
  });
})();

// ══════════════ Buscador empleados ZKBio (agregar) ══════════════
if (window._PAGE.canEdit) (function () {
  let modal = null, destino = null, timer = null;
  function open(dest, titulo) {
    destino = dest;
    document.getElementById('ae-titulo').textContent = titulo;
    document.getElementById('ae-buscar').value = '';
    document.getElementById('ae-resultados').innerHTML = '<div class="text-muted small p-2">Escribe para buscar…</div>';
    document.getElementById('ae-error').classList.add('d-none');
    if (!modal) modal = new bootstrap.Modal(document.getElementById('modalAgregarEmp'));
    modal.show();
  }
  document.getElementById('btn-add-mensual')?.addEventListener('click', () => open('mensual', 'Agregar empleado'));
  document.getElementById('btn-add-instructor')?.addEventListener('click', () => open('instructor', 'Agregar instructor'));

  document.getElementById('ae-buscar')?.addEventListener('input', function () {
    clearTimeout(timer);
    const q = this.value.trim();
    timer = setTimeout(async () => {
      const cont = document.getElementById('ae-resultados');
      cont.innerHTML = '<div class="text-muted small p-2">Buscando…</div>';
      const d = await (await fetch(`${window._PAGE.urlEmpBuscar}?q=${encodeURIComponent(q)}`)).json();
      if (!d.ok) { cont.innerHTML = `<div class="text-danger small p-2">${d.error || 'Error'}</div>`; return; }
      if (!d.empleados.length) { cont.innerHTML = '<div class="text-muted small p-2">Sin resultados.</div>'; return; }
      cont.innerHTML = '';
      d.empleados.forEach(e => {
        const a = document.createElement('button');
        a.type = 'button';
        a.className = 'list-group-item list-group-item-action ae-item';
        a.dataset.emp = e.emp_code; a.dataset.nombre = e.nombre;
        a.innerHTML = `<span class="fw-semibold">${e.nombre}</span> <span class="text-muted small">· ${e.emp_code}</span>`;
        cont.appendChild(a);
      });
    }, 300);
  });
  document.getElementById('ae-resultados')?.addEventListener('click', async function (e) {
    const it = e.target.closest('.ae-item'); if (!it) return;
    const url = destino === 'instructor' ? window._PAGE.urlInstructorAdd : window._PAGE.urlMensualAdd;
    const d = await jpost(url, { emp_code: it.dataset.emp, nombre: it.dataset.nombre });
    if (d.ok) { location.reload(); }
    else { const err = document.getElementById('ae-error'); err.querySelector('.alert') && (err.querySelector('.alert').textContent = d.error || 'Error'); err.classList.remove('d-none'); }
  });
})();

// ══════════════ Tabs 3-4: grilla mensual ══════════════
if (window._PAGE.canEdit) (function () {
  const ANIO = window._PAGE.anio;
  function sumRow(tr, sel, totalSel) {
    let s = 0;
    tr.querySelectorAll(sel).forEach(inp => { s += parseFloat(inp.value) || 0; });
    const tot = document.querySelector(totalSel);
    if (tot) tot.textContent = (Math.round(s * 100) / 100).toFixed(2);
  }
  // Horas trabajadas
  document.querySelectorAll('.cell-trab').forEach(inp => {
    inp.addEventListener('change', async function () {
      const empId = this.dataset.emp, mes = this.dataset.mes;
      await jpost(window._PAGE.urlMensualCell, { empleado_id: empId, anio: ANIO, mes, campo: 'trabajadas', valor: this.value });
      sumRow(this.closest('tr'), '.cell-trab', `.mtot-trab-${empId}`);
    });
  });
  // Horas tomadas (override; vacío vuelve al permiso)
  document.querySelectorAll('.cell-tom').forEach(inp => {
    inp.addEventListener('change', async function () {
      const empId = this.dataset.emp, mes = this.dataset.mes;
      const raw = this.value;
      await jpost(window._PAGE.urlMensualCell, { empleado_id: empId, anio: ANIO, mes, campo: 'tomadas', valor: raw });
      if (raw === '') this.value = this.dataset.permiso && parseFloat(this.dataset.permiso) ? this.dataset.permiso : '';
      sumRow(this.closest('tr'), '.cell-tom', `.mtot-tom-${empId}`);
    });
  });
  // Eliminar empleado mensual
  document.querySelectorAll('.btn-del-mensual').forEach(btn => {
    btn.addEventListener('click', async function () {
      if (!confirm(`¿Eliminar a ${this.dataset.nombre} de la matriz mensual?`)) return;
      const d = await jpost(window._PAGE.urlMensualDel.replace('{pk}', this.dataset.pk));
      if (d.ok) location.reload();
    });
  });
})();

// ══════════════ Tab 5: instructores ══════════════
if (window._PAGE.canEdit) (function () {
  function recompute(id) {
    const tr = document.querySelector(`tr[data-inst-id="${id}"]`); if (!tr) return;
    const comp = parseFloat(tr.dataset.compHrs) || 0;
    const teMin = parseFloat(tr.querySelector('.inst-te')?.value) || 0;
    const tomado = parseFloat(tr.querySelector('.inst-tomado')?.value) || 0;
    const total = Math.round((comp + teMin / 60) * 100) / 100;
    const saldo = Math.max(0, Math.round((total - tomado) * 100) / 100);
    const tCell = document.querySelector(`.inst-total-${id}`); if (tCell) tCell.textContent = `${total.toFixed(2)} h`;
    const sCell = document.querySelector(`.inst-saldo-${id}`);
    if (sCell) {
      if (saldo === 0) { sCell.className = `badge bg-green-lt text-green inst-saldo-${id}`; sCell.innerHTML = '<i class="ti ti-circle-check me-1"></i>0 h'; }
      else { sCell.className = `badge bg-red-lt text-red inst-saldo-${id}`; sCell.textContent = `${saldo.toFixed(2)} h`; }
    }
  }
  document.querySelectorAll('.inst-te').forEach(inp => {
    inp.addEventListener('change', async function () {
      const id = this.dataset.id;
      await jpost(window._PAGE.urlInstructorSet.replace('{pk}', id), { campo: 'te', valor: this.value });
      recompute(id);
    });
  });
  document.querySelectorAll('.inst-tomado').forEach(inp => {
    inp.addEventListener('change', async function () {
      const id = this.dataset.id, raw = this.value;
      await jpost(window._PAGE.urlInstructorSet.replace('{pk}', id), { campo: 'tomado', valor: raw });
      if (raw === '') this.value = this.dataset.permiso && parseFloat(this.dataset.permiso) ? this.dataset.permiso : '';
      recompute(id);
    });
  });
  document.querySelectorAll('.btn-del-instructor').forEach(btn => {
    btn.addEventListener('click', async function () {
      if (!confirm(`¿Eliminar al instructor ${this.dataset.nombre}?`)) return;
      const d = await jpost(window._PAGE.urlInstructorDel.replace('{pk}', this.dataset.pk));
      if (d.ok) location.reload();
    });
  });
})();
