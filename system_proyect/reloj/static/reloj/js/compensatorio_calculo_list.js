/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #compensatorio_calculo_list-config (un .js no lo procesa Django). */
const CFG_COMPENSATORIO_CALCULO_LIST = (function(){
  var d = document.getElementById("compensatorio_calculo_list-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
    v4: d.v4,
    j4: j(d.v4),
    v5: d.v5,
    j5: j(d.v5),
    v6: d.v6,
    j6: j(d.v6),
    v7: d.v7,
    j7: j(d.v7),
    v8: d.v8,
    j8: j(d.v8),
    v9: d.v9,
    j9: j(d.v9),
    v10: d.v10,
    j10: j(d.v10),
    v11: d.v11,
    j11: j(d.v11),
    v12: d.v12,
    j12: j(d.v12),
  };
})();

// Reactivar el tab de Gilma tras filtrar (?tab=gilma)
  (function () {
    var p = new URLSearchParams(window.location.search);
    var map = { gilma: 'tab-gilma-btn' };
    var id = map[p.get('tab')];
    if (id) {
      var btn = document.getElementById(id);
      if (btn && window.bootstrap) new bootstrap.Tab(btn).show();
    }
  })();
  // Atajos de rango: Mes / Quincena 1 (1–15) / Quincena 2 (16–fin), según el mes de "Hasta"
  (function () {
    function fmt(y, m, d) { return y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0'); }
    document.querySelectorAll('[data-grange]').forEach(function (b) {
      b.addEventListener('click', function () {
        var base = document.getElementById('g_fin').value || document.getElementById('g_ini').value || new Date().toISOString().slice(0, 10);
        var dt = new Date(base + 'T00:00:00'), y = dt.getFullYear(), m = dt.getMonth();
        var last = new Date(y, m + 1, 0).getDate(), r = this.dataset.grange, ini, fin;
        if (r === 'mes') { ini = fmt(y, m, 1); fin = fmt(y, m, last); }
        else if (r === 'q1') { ini = fmt(y, m, 1); fin = fmt(y, m, 15); }
        else { ini = fmt(y, m, 16); fin = fmt(y, m, last); }
        document.getElementById('g_ini').value = ini;
        document.getElementById('g_fin').value = fin;
        document.getElementById('gilmaRangoForm').submit();
      });
    });
  })();

window._PAGE = {
  csrf:         CFG_COMPENSATORIO_CALCULO_LIST.v0,
  canEdit:      CFG_COMPENSATORIO_CALCULO_LIST.j8,
  canEditExtra:   CFG_COMPENSATORIO_CALCULO_LIST.j9,
  canDeleteExtra: CFG_COMPENSATORIO_CALCULO_LIST.j10,
  isSuperuser:    CFG_COMPENSATORIO_CALCULO_LIST.j11,
  anio:         CFG_COMPENSATORIO_CALCULO_LIST.j12,
  urlTeGet:     '/reloj/compensatorio-calculo/{pk}/tiempo-extra/',
  urlTeAdd:     '/reloj/compensatorio-calculo/{pk}/tiempo-extra/add/',
  urlTeDel:     '/reloj/compensatorio-te/{te_pk}/delete/',
  urlEmpBuscar: CFG_COMPENSATORIO_CALCULO_LIST.v1,
  urlSetHorasAdeudadas: '/reloj/compensatorio-calculo/{pk}/set-horas-adeudadas/',
  urlSetTomado: '/reloj/compensatorio-calculo/{pk}/set-tomado/',
  urlGetTomado: '/reloj/compensatorio-calculo/{pk}/tomado/',
  urlTomManualAdd: '/reloj/compensatorio-calculo/{pk}/tomado-manual/add/',
  urlTomManualDel: '/reloj/compensatorio-tomado-manual/{pk}/delete/',
  urlMensualAdd:    CFG_COMPENSATORIO_CALCULO_LIST.v2,
  urlMensualCell:   CFG_COMPENSATORIO_CALCULO_LIST.v3,
  urlMensualComentario: CFG_COMPENSATORIO_CALCULO_LIST.v4,
  urlDetGet: CFG_COMPENSATORIO_CALCULO_LIST.v5,
  urlDetAdd: CFG_COMPENSATORIO_CALCULO_LIST.v6,
  urlDetDel: '/reloj/compensatorio-mensual-detalle/{pk}/delete/',
  urlMensualDel:    '/reloj/compensatorio-mensual/{pk}/delete/',
  urlInstructorAdd: CFG_COMPENSATORIO_CALCULO_LIST.v7,
  urlInstructorSet: '/reloj/compensatorio-instructor/{pk}/set/',
  urlInstructorDel: '/reloj/compensatorio-instructor/{pk}/delete/',
  urlInstTeGet:  '/reloj/compensatorio-instructor/{pk}/te/',
  urlInstTeAdd:  '/reloj/compensatorio-instructor/{pk}/te/add/',
  urlInstTeDel:  '/reloj/compensatorio-instructor-te/{pk}/delete/',
  urlInstTomGet: '/reloj/compensatorio-instructor/{pk}/tomado/',
  urlInstTomAdd: '/reloj/compensatorio-instructor/{pk}/tomado/add/',
  urlInstTomDel: '/reloj/compensatorio-instructor-tomado/{pk}/delete/',
};


/* <--- hecho por claude code: lógica recuperada de d5d2026 (se había perdido al
   extraer el JS: quedaba solo el puente de config y los 18 botones de la pantalla
   -agregar mensual, fijar tomado/compensado, TE instructor, días no laborables,
   checkboxes- no hacían nada). Envuelta en IIFE para no filtrar globales. */
(function(){
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
      return;
    }
    // Saldo hasta la fecha: texto negro normal
    b.className = `fw-semibold font-monospace saldo-badge-${pk}`;
    b.textContent = `${minToH(saldoMin)} h`;
  }
  function updateRowTotals(pk, data) {
    document.querySelectorAll(`.total-hrs-${pk}`).forEach(c => c.textContent = `${data.total_hrs} h`);
    const row = document.querySelector(`tr[data-pk="${pk}"]`);
    if (row) row.dataset.totalMin = data.total_min;
    if (data.saldo_min !== undefined) updateSaldoBadge(pk, data.saldo_min);
    const hab = document.querySelector(`.dias-hab-badge-${pk}`);
    if (hab && data.dias_hab !== undefined) hab.textContent = `${data.dias_hab} días`;
    const ctCell = document.querySelector(`.comp-te-${pk}`); if (ctCell && data.comp_mas_te_hrs !== undefined) ctCell.textContent = `${data.comp_mas_te_hrs} h`;
    const netoCell = document.querySelector(`.neto-${pk}`); if (netoCell && data.neto_hrs !== undefined) netoCell.textContent = `${data.neto_hrs} h`;
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
      const hc = document.querySelector(`.horas-adeudadas-${pk}`); if (hc && data.horas_adeudadas !== undefined) hc.textContent = `${data.horas_adeudadas} h`;
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
  // Tiempo tomado: detalle permiso (lectura) + tabla manual (agregar/eliminar)
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
  function renderTomManual(manual) {
    const tbody = document.getElementById('tomm-tbody'), empty = document.getElementById('tomm-empty');
    tbody.querySelectorAll('tr:not(#tomm-empty)').forEach(r => r.remove());
    if (!manual.length) { empty.style.display = ''; return; }
    empty.style.display = 'none';
    manual.forEach(m => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="text-center font-monospace small">${m.fecha}</td><td class="text-center fw-semibold text-pink">${m.horas} h</td><td class="text-muted small">${m.razon}</td>${window._PAGE.isSuperuser ? `<td class="text-center"><button class="btn btn-sm btn-ghost-danger btn-tomm-del" data-pk="${m.pk}"><i class="ti ti-trash"></i></button></td>` : ''}`;
      tbody.appendChild(tr);
    });
  }
  function renderReceso(receso) {
    const wrap = document.getElementById('tom-receso-wrap');
    const tbody = document.getElementById('tom-receso-tbody');
    if (!wrap || !tbody) return;
    tbody.innerHTML = '';
    if (!receso || !receso.length) { wrap.style.display = 'none'; return; }
    wrap.style.display = '';
    let tot = 0;
    receso.forEach(r => {
      tot += r.minutos;
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="small">${r.mes}</td><td class="text-center fw-semibold text-orange">+${r.minutos} min</td>`;
      tbody.appendChild(tr);
    });
    document.getElementById('tom-receso-total').textContent = tot;
    document.getElementById('tom-receso-hrs').textContent = (Math.round(tot / 60 * 100) / 100);
  }
  function refreshTomCells(d) {
    // Actualiza badge tomado, neto y saldo en la fila de Tab 2
    if (d.tomado_hrs !== undefined) {
      const badge = document.querySelector(`.tomado-badge-${tomPk}`);
      if (badge) badge.innerHTML = `<i class="ti ti-calendar-minus me-1"></i>${d.tomado_hrs > 0 ? d.tomado_hrs + ' h' : '—'}`;
      const row = document.querySelector(`tr[data-pk="${tomPk}"]`); if (row) row.dataset.tomadoMin = d.tomado_hrs * 60;
    }
    const netoCell = document.querySelector(`.neto-${tomPk}`); if (netoCell && d.neto_hrs !== undefined) netoCell.textContent = `${d.neto_hrs} h`;
    if (d.saldo_min !== undefined) updateSaldoBadge(tomPk, d.saldo_min);
    const tt = (d.total_tomado !== undefined) ? d.total_tomado : d.tomado_hrs;
    if (tt !== undefined) document.getElementById('tom-total-tomado').textContent = tt;
  }
  // Saldo deuda = Total a compensar − (Compensado + T. extra)
  function updateSaldoDeuda(pk, compTeHrs) {
    const sf = document.querySelector(`.saldo-fecha-${pk}`);
    if (!sf || compTeHrs === undefined) return;
    const totalHrs = parseFloat(sf.closest('td').dataset.totalHrs) || 0;
    const val = Math.round((totalHrs - compTeHrs) * 100) / 100;
    // <--- hecho por claude code: sin deuda → excedente (horas de más); con deuda → la deuda
    if (val <= 0) {
      sf.className = `badge bg-green-lt text-green saldo-fecha-${pk}`;
      const exc = Math.round((-val) * 100) / 100;
      if (exc > 0) { sf.innerHTML = `<i class="ti ti-arrow-up-right me-1"></i>+${exc} h de más`; sf.setAttribute('title', 'Horas de más ya trabajadas por encima del total'); }
      else { sf.innerHTML = '<i class="ti ti-circle-check me-1"></i>0 h'; }
    } else { sf.className = `badge bg-red-lt text-red saldo-fecha-${pk}`; sf.textContent = `${val} h`; }
  }
  document.querySelectorAll('.btn-set-tomado').forEach(btn => {
    btn.addEventListener('click', async function () {
      tomPk = this.dataset.pk;
      document.getElementById('tom-nombre').textContent = this.dataset.nombre || '';
      ['tomm-fecha', 'tomm-horas', 'tomm-razon'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
      document.getElementById('tomm-error')?.classList.add('d-none');
      if (!modalTom) modalTom = new bootstrap.Modal(document.getElementById('modalTomado'));
      modalTom.show();
      const d = await (await fetch(window._PAGE.urlGetTomado.replace('{pk}', tomPk))).json();
      if (d.ok) {
        renderTomado(d.entries);
        renderTomManual(d.manual || []);
        renderReceso(d.receso || []);
        document.getElementById('tom-total-permiso').textContent = d.total_permiso;
        document.getElementById('tom-total-tomado').textContent = d.total_tomado;
      }
    });
  });
  document.getElementById('btn-tomm-add')?.addEventListener('click', async function () {
    const fecha = document.getElementById('tomm-fecha').value;
    const horas = parseFloat(document.getElementById('tomm-horas').value);
    const razon = document.getElementById('tomm-razon').value.trim();
    const err = document.getElementById('tomm-error');
    if (!fecha) { err.querySelector('.alert').textContent = 'Selecciona una fecha.'; err.classList.remove('d-none'); return; }
    if (!horas || horas <= 0) { err.querySelector('.alert').textContent = 'Ingresa horas válidas.'; err.classList.remove('d-none'); return; }
    err.classList.add('d-none'); this.disabled = true;
    const d = await jpost(window._PAGE.urlTomManualAdd.replace('{pk}', tomPk), { fecha, horas, razon });
    this.disabled = false;
    if (d.ok) {
      document.getElementById('tomm-horas').value = ''; document.getElementById('tomm-razon').value = '';
      renderTomManual(d.manual); refreshTomCells(d);
    } else { err.querySelector('.alert').textContent = d.error || 'Error'; err.classList.remove('d-none'); }
  });
  document.getElementById('tomm-tbody')?.addEventListener('click', async function (e) {
    const btn = e.target.closest('.btn-tomm-del'); if (!btn) return;
    btn.disabled = true;
    const d = await jpost(window._PAGE.urlTomManualDel.replace('{pk}', btn.dataset.pk));
    if (d.ok) { renderTomManual(d.manual); refreshTomCells(d); }
  });

  // Compensado hasta hoy (manual)
  let modalComp = null, compPk = null;
  document.querySelectorAll('.btn-set-compensado').forEach(btn => {
    btn.addEventListener('click', function () {
      compPk = this.dataset.pk;
      document.getElementById('comp-nombre').textContent = this.dataset.nombre || '';
      document.getElementById('comp-input').value = this.dataset.valor || '';
      if (!modalComp) modalComp = new bootstrap.Modal(document.getElementById('modalCompensado'));
      modalComp.show();
    });
  });
  document.getElementById('btn-guardar-compensado')?.addEventListener('click', async function () {
    const raw = document.getElementById('comp-input').value;
    const minutos = raw === '' ? '' : Math.round((parseFloat(raw) || 0) * 60);
    this.disabled = true;
    const res = await fetch(`/reloj/compensatorio-calculo/${compPk}/set-compensado/`, {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ csrfmiddlewaretoken: CSRF, minutos }),
    });
    const data = await res.json(); this.disabled = false;
    if (data.ok) {
      const hrs = data.horas_compensados != null ? data.horas_compensados : 0;
      const cb = document.querySelector(`.compensado-badge-${compPk}`);
      if (cb) { cb.className = `badge bg-teal-lt text-teal compensado-badge-${compPk}`; cb.innerHTML = `<i class="ti ti-progress me-1"></i>${hrs} h`; }
      const ct = document.querySelector(`.comp-te-${compPk}`); if (ct && data.comp_mas_te_hrs !== undefined) ct.textContent = `${data.comp_mas_te_hrs} h`;
      if (data.saldo_min !== undefined) updateSaldoBadge(compPk, data.saldo_min);
      updateSaldoDeuda(compPk, data.comp_mas_te_hrs);
      const b = document.querySelector(`.btn-set-compensado[data-pk="${compPk}"]`); if (b) b.dataset.valor = data.es_manual ? hrs : '';
      if (modalComp) modalComp.hide();
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
    const _inp = document.getElementById('min-dia-input');
    const raw = (_inp.value || '').trim();
    const valor = parseInt(raw, 10);
    // 0 permitido (empleado manual, solo tiempo extra); rechaza vacío/negativo/NaN
    if (raw === '' || isNaN(valor) || valor < 0) { _inp.classList.add('is-invalid'); return; }
    _inp.classList.remove('is-invalid');
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
  function updateTEBadge(totalMin, totalHrs, data) {
    document.getElementById('te-total-min').textContent = totalMin;
    document.getElementById('te-total-hrs').textContent = totalHrs;
    const badge = document.querySelector(`.te-badge-${tePk}`);
    if (badge) badge.innerHTML = `<i class="ti ti-clock-bolt me-1"></i>${totalMin > 0 ? totalHrs + ' h' : '—'}`;
    // Refrescar columnas dependientes del tiempo extra (Tab 2)
    if (data) {
      const ct = document.querySelector(`.comp-te-${tePk}`); if (ct && data.comp_mas_te_hrs !== undefined) ct.textContent = `${data.comp_mas_te_hrs} h`;
      const nt = document.querySelector(`.neto-${tePk}`); if (nt && data.neto_hrs !== undefined) nt.textContent = `${data.neto_hrs} h`;
      if (data.saldo_min !== undefined) updateSaldoBadge(tePk, data.saldo_min);
      updateSaldoDeuda(tePk, data.comp_mas_te_hrs);
    }
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
    if (d.ok) { renderTE(d.entries); updateTEBadge(d.total_min, d.total_hrs, d); }
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
        if (data.saldo_min !== undefined) updateSaldoBadge(pk, data.saldo_min);
      }
    }
    this.disabled = false; this.innerHTML = '<i class="ti ti-clock-plus me-1"></i>Aplicar 3 días perm. extras';
  });
})();

// ══════════════ Buscador empleados ZKBio (agregar) ══════════════
if (window._PAGE.canEditExtra || window._PAGE.canDeleteExtra) (function () {
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

// ══════════════ Tab fusionado: Tiempo compensatorio general ══════════════
if (window._PAGE.canEditExtra || window._PAGE.canDeleteExtra) (function () {
  const ANIO = window._PAGE.anio;
  // Total = Σ trabajadas ; Tomado: lo edita quien tenga Control Compensatorio→Editar (si no, fijo del permiso) ; Saldo = Tr − To
  function recompRow(tr, empId) {
    let st = 0, so = 0;
    tr.querySelectorAll('.cell-trab').forEach(i => st += parseFloat(i.value) || 0);
    const tomInputs = tr.querySelectorAll('.cell-tom');
    if (tomInputs.length) tomInputs.forEach(i => so += parseFloat(i.value) || 0);
    else so = parseFloat(tr.dataset.totalTom) || 0;
    const tot = document.querySelector(`.mtot-trab-${empId}`);
    if (tot) tot.textContent = (Math.round(st * 100) / 100).toFixed(2);
    const tomEl = document.querySelector(`.mtot-tomado-${empId}`);
    if (tomEl && tomInputs.length) tomEl.textContent = (Math.round(so * 100) / 100).toFixed(2);
    const sal = document.querySelector(`.mtot-saldo-${empId}`);
    if (sal) sal.textContent = (Math.round((st - so) * 100) / 100).toFixed(2);
  }
  document.querySelectorAll('.cell-trab').forEach(inp => {
    inp.addEventListener('change', async function () {
      const empId = this.dataset.emp, mes = this.dataset.mes;
      await jpost(window._PAGE.urlMensualCell, { empleado_id: empId, anio: ANIO, mes, campo: 'trabajadas', valor: this.value });
      recompRow(this.closest('tr'), empId);
    });
  });
  // To (tomado): editable con permiso calculo_comp:editar — el template solo pinta inputs si can_edit_extra
  document.querySelectorAll('.cell-tom').forEach(inp => {
    inp.addEventListener('change', async function () {
      const empId = this.dataset.emp, mes = this.dataset.mes;
      const raw = this.value;
      await jpost(window._PAGE.urlMensualCell, { empleado_id: empId, anio: ANIO, mes, campo: 'tomadas', valor: raw });
      if (raw === '') this.value = this.dataset.permiso && parseFloat(this.dataset.permiso) ? this.dataset.permiso : '';
      recompRow(this.closest('tr'), empId);
    });
  });
  // Comentarios con horas (modal estilo tiempo extra)
  let modalCmt = null, cmtEmp = null, cmtTipo = null;
  function setCmtBadge(total) {
    const badge = document.querySelector(`.cmt-badge-${cmtTipo}-${cmtEmp}`);
    if (badge) badge.innerHTML = `<i class="ti ti-message-2"></i>${total > 0 ? ' ' + total : ''}`;
  }
  function renderCmt(entries) {
    const tbody = document.getElementById('cmt-tbody'), empty = document.getElementById('cmt-empty');
    tbody.querySelectorAll('tr:not(#cmt-empty)').forEach(r => r.remove());
    if (!entries.length) { empty.style.display = ''; return; }
    empty.style.display = 'none';
    entries.forEach(en => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="text-center font-monospace small">${en.fecha}</td><td class="text-center fw-semibold text-blue">${en.horas} h</td><td class="text-muted small">${en.comentario}</td>${window._PAGE.isSuperuser ? `<td class="text-center"><button class="btn btn-sm btn-ghost-danger btn-cmt-del" data-pk="${en.pk}"><i class="ti ti-trash"></i></button></td>` : ''}`;
      tbody.appendChild(tr);
    });
  }
  document.querySelectorAll('.btn-cmt-det').forEach(btn => {
    btn.addEventListener('click', async function () {
      cmtEmp = this.dataset.emp; cmtTipo = this.dataset.tipo;
      document.getElementById('cmt-nombre').textContent = this.dataset.nombre || '';
      document.getElementById('cmt-tipo-label').textContent = cmtTipo === 'trab' ? 'Comentarios (Trabajadas)' : 'Comentarios (Tomadas)';
      ['cmt-fecha', 'cmt-horas', 'cmt-coment'].forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });
      document.getElementById('cmt-add-error')?.classList.add('d-none');
      if (!modalCmt) modalCmt = new bootstrap.Modal(document.getElementById('modalComentarioDet'));
      modalCmt.show();
      const d = await (await fetch(`${window._PAGE.urlDetGet}?empleado_id=${cmtEmp}&anio=${ANIO}&tipo=${cmtTipo}`)).json();
      if (d.ok) { renderCmt(d.entries); document.getElementById('cmt-total').textContent = d.total; setCmtBadge(d.total); }
    });
  });
  document.getElementById('btn-cmt-add')?.addEventListener('click', async function () {
    const fecha = document.getElementById('cmt-fecha').value;
    const horas = parseFloat(document.getElementById('cmt-horas').value);
    const coment = document.getElementById('cmt-coment').value.trim();
    const err = document.getElementById('cmt-add-error');
    if (!fecha) { err.querySelector('.alert').textContent = 'Selecciona una fecha.'; err.classList.remove('d-none'); return; }
    if (!horas || horas <= 0) { err.querySelector('.alert').textContent = 'Ingresa horas válidas.'; err.classList.remove('d-none'); return; }
    err.classList.add('d-none'); this.disabled = true;
    const d = await jpost(window._PAGE.urlDetAdd, { empleado_id: cmtEmp, anio: ANIO, tipo: cmtTipo, fecha, horas, comentario: coment });
    this.disabled = false;
    if (d.ok) {
      document.getElementById('cmt-horas').value = ''; document.getElementById('cmt-coment').value = '';
      renderCmt(d.entries); document.getElementById('cmt-total').textContent = d.total; setCmtBadge(d.total);
    } else { err.querySelector('.alert').textContent = d.error || 'Error'; err.classList.remove('d-none'); }
  });
  document.getElementById('cmt-tbody')?.addEventListener('click', async function (e) {
    const btn = e.target.closest('.btn-cmt-del'); if (!btn) return;
    btn.disabled = true;
    const d = await jpost(window._PAGE.urlDetDel.replace('{pk}', btn.dataset.pk));
    if (d.ok) { renderCmt(d.entries); document.getElementById('cmt-total').textContent = d.total; setCmtBadge(d.total); }
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
if (window._PAGE.canEditExtra || window._PAGE.canDeleteExtra) (function () {
  const ANIO = window._PAGE.anio;
  function recompute(id) {
    const tr = document.querySelector(`tr[data-inst-id="${id}"]`); if (!tr) return;
    const comp   = parseFloat(tr.dataset.compHrs) || 0;
    const teMin  = parseFloat(tr.dataset.teMin) || 0;
    const tomado = parseFloat(tr.dataset.tomadoHrs) || 0;
    const total = Math.round((comp + teMin / 60) * 100) / 100;
    const saldo = Math.max(0, Math.round((total - tomado) * 100) / 100);
    const tCell = document.querySelector(`.inst-total-${id}`); if (tCell) tCell.textContent = `${total.toFixed(2)} h`;
    const sCell = document.querySelector(`.inst-saldo-${id}`);
    if (sCell) {
      if (saldo === 0) { sCell.className = `badge bg-green-lt text-green inst-saldo-${id}`; sCell.innerHTML = '<i class="ti ti-circle-check me-1"></i>0 h'; }
      else { sCell.className = `badge bg-red-lt text-red inst-saldo-${id}`; sCell.textContent = `${saldo.toFixed(2)} h`; }
    }
  }

  // ── Modal Tiempo extra autorizado (entradas) ──
  let modalITE = null, iteId = null;
  function renderITE(entries) {
    const tb = document.getElementById('instte-tbody'), em = document.getElementById('instte-empty');
    tb.querySelectorAll('tr:not(#instte-empty)').forEach(r => r.remove());
    if (!entries.length) { em.style.display = ''; return; }
    em.style.display = 'none';
    entries.forEach(e => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="text-center font-monospace small">${e.fecha}</td><td class="text-center fw-semibold text-cyan">${e.minutos} min</td><td class="text-muted small">${e.comentario}</td>${window._PAGE.canEditExtra ? `<td class="text-center"><button class="btn btn-sm btn-ghost-danger btn-instte-del" data-pk="${e.pk}"><i class="ti ti-trash"></i></button></td>` : ''}`;
      tb.appendChild(tr);
    });
  }
  function applyITE(d) {
    document.getElementById('instte-total-min').textContent = d.total_min;
    document.getElementById('instte-total-hrs').textContent = d.total_hrs;
    const badge = document.querySelector(`.inst-te-badge-${iteId}`);
    if (badge) badge.innerHTML = `<i class="ti ti-clock-bolt me-1"></i>${d.total_min > 0 ? d.total_min + ' min' : 'Agregar'}`;
    const tr = document.querySelector(`tr[data-inst-id="${iteId}"]`); if (tr) tr.dataset.teMin = d.total_min;
    recompute(iteId);
  }
  document.querySelectorAll('.btn-inst-te').forEach(btn => {
    btn.addEventListener('click', async function () {
      iteId = this.dataset.id;
      document.getElementById('instte-nombre').textContent = this.dataset.nombre || '';
      ['instte-fecha', 'instte-min', 'instte-coment'].forEach(i => { const el = document.getElementById(i); if (el) el.value = ''; });
      document.getElementById('instte-error')?.classList.add('d-none');
      if (!modalITE) modalITE = new bootstrap.Modal(document.getElementById('modalInstTE'));
      modalITE.show();
      const d = await (await fetch(window._PAGE.urlInstTeGet.replace('{pk}', iteId))).json();
      if (d.ok) { renderITE(d.entries); applyITE(d); }
    });
  });
  document.getElementById('btn-instte-add')?.addEventListener('click', async function () {
    const fecha = document.getElementById('instte-fecha').value;
    const minutos = parseInt(document.getElementById('instte-min').value);
    const coment = document.getElementById('instte-coment').value.trim();
    const err = document.getElementById('instte-error');
    if (!fecha) { err.querySelector('.alert').textContent = 'Selecciona una fecha.'; err.classList.remove('d-none'); return; }
    if (!minutos || minutos <= 0) { err.querySelector('.alert').textContent = 'Minutos inválidos.'; err.classList.remove('d-none'); return; }
    err.classList.add('d-none'); this.disabled = true;
    const d = await jpost(window._PAGE.urlInstTeAdd.replace('{pk}', iteId), { fecha, minutos, comentario: coment });
    this.disabled = false;
    if (d.ok) { document.getElementById('instte-min').value = ''; document.getElementById('instte-coment').value = ''; renderITE(d.entries); applyITE(d); }
    else { err.querySelector('.alert').textContent = d.error || 'Error'; err.classList.remove('d-none'); }
  });
  document.getElementById('instte-tbody')?.addEventListener('click', async function (e) {
    const b = e.target.closest('.btn-instte-del'); if (!b) return;
    const d = await jpost(window._PAGE.urlInstTeDel.replace('{pk}', b.dataset.pk));
    if (d.ok) { renderITE(d.entries); applyITE(d); }
  });

  // ── Modal Permiso tomado (permiso + manual superuser) ──
  let modalITom = null, itomId = null;
  function renderITom(manual) {
    const tb = document.getElementById('insttom-tbody'), em = document.getElementById('insttom-empty');
    tb.querySelectorAll('tr:not(#insttom-empty)').forEach(r => r.remove());
    if (!manual.length) { em.style.display = ''; return; }
    em.style.display = 'none';
    manual.forEach(m => {
      const tr = document.createElement('tr');
      tr.innerHTML = `<td class="text-center font-monospace small">${m.fecha}</td><td class="text-center fw-semibold text-pink">${m.horas} h</td><td class="text-muted small">${m.razon}</td>${window._PAGE.isSuperuser ? `<td class="text-center"><button class="btn btn-sm btn-ghost-danger btn-insttom-del" data-pk="${m.pk}"><i class="ti ti-trash"></i></button></td>` : ''}`;
      tb.appendChild(tr);
    });
  }
  function applyITom(d) {
    document.getElementById('insttom-permiso').textContent = d.permiso;
    document.getElementById('insttom-total').textContent = d.total_tomado;
    const badge = document.querySelector(`.inst-tomado-badge-${itomId}`);
    if (badge) badge.innerHTML = `<i class="ti ti-calendar-minus me-1"></i>${d.total_tomado} h`;
    const tr = document.querySelector(`tr[data-inst-id="${itomId}"]`); if (tr) tr.dataset.tomadoHrs = d.total_tomado;
    recompute(itomId);
  }
  document.querySelectorAll('.btn-inst-tomado').forEach(btn => {
    btn.addEventListener('click', async function () {
      itomId = this.dataset.id;
      document.getElementById('insttom-nombre').textContent = this.dataset.nombre || '';
      ['insttom-fecha', 'insttom-horas', 'insttom-razon'].forEach(i => { const el = document.getElementById(i); if (el) el.value = ''; });
      document.getElementById('insttom-error')?.classList.add('d-none');
      if (!modalITom) modalITom = new bootstrap.Modal(document.getElementById('modalInstTomado'));
      modalITom.show();
      const d = await (await fetch(`${window._PAGE.urlInstTomGet.replace('{pk}', itomId)}?anio=${ANIO}`)).json();
      if (d.ok) { renderITom(d.manual); applyITom(d); }
    });
  });
  document.getElementById('btn-insttom-add')?.addEventListener('click', async function () {
    const fecha = document.getElementById('insttom-fecha').value;
    const horas = parseFloat(document.getElementById('insttom-horas').value);
    const razon = document.getElementById('insttom-razon').value.trim();
    const err = document.getElementById('insttom-error');
    if (!fecha) { err.querySelector('.alert').textContent = 'Selecciona una fecha.'; err.classList.remove('d-none'); return; }
    if (!horas || horas <= 0) { err.querySelector('.alert').textContent = 'Horas inválidas.'; err.classList.remove('d-none'); return; }
    err.classList.add('d-none'); this.disabled = true;
    const d = await jpost(window._PAGE.urlInstTomAdd.replace('{pk}', itomId), { anio: ANIO, fecha, horas, razon });
    this.disabled = false;
    if (d.ok) { document.getElementById('insttom-horas').value = ''; document.getElementById('insttom-razon').value = ''; renderITom(d.manual); applyITom(d); }
    else { err.querySelector('.alert').textContent = d.error || 'Error'; err.classList.remove('d-none'); }
  });
  document.getElementById('insttom-tbody')?.addEventListener('click', async function (e) {
    const b = e.target.closest('.btn-insttom-del'); if (!b) return;
    const d = await jpost(window._PAGE.urlInstTomDel.replace('{pk}', b.dataset.pk));
    if (d.ok) { renderITom(d.manual); applyITom(d); }
  });

  // Fecha inicio → recarga (afecta el compensado). Fecha fin → solo guarda.
  document.querySelectorAll('.inst-fecha-inicio').forEach(inp => {
    inp.addEventListener('change', async function () {
      const d = await jpost(window._PAGE.urlInstructorSet.replace('{pk}', this.dataset.id), { campo: 'fecha_inicio', valor: this.value });
      if (d.ok) location.reload();
    });
  });
  document.querySelectorAll('.inst-fecha-fin').forEach(inp => {
    inp.addEventListener('change', async function () {
      await jpost(window._PAGE.urlInstructorSet.replace('{pk}', this.dataset.id), { campo: 'fecha_fin', valor: this.value });
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

})();
