// ── DataTables init ──
document.addEventListener('DOMContentLoaded', function () {
  if (typeof $.fn.DataTable !== 'undefined') {
    $('#tabla-calculo').DataTable({
      order: [], pageLength: 25,
      language: { url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json' }
    });
  }
});

// ── Main IIFE ──
(function(){
  const CSRF   = window._PAGE.csrf;
  const minToH = m => +(m / 60).toFixed(1);

  // ── Saldo badge ──
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

  // ── Actualizar total y saldo en la fila ──
  function updateRowTotals(pk, data) {
    const totalCell = document.querySelector(`.total-hrs-${pk}`);
    if (totalCell) totalCell.textContent = `${data.total_hrs} h`;
    const row = document.querySelector(`tr[data-pk="${pk}"]`);
    if (row) row.dataset.totalMin = data.total_min;
    updateSaldoBadge(pk, data.saldo_min);
    const habBadge = document.querySelector(`.dias-hab-badge-${pk}`);
    if (habBadge) habBadge.textContent = `${data.dias_hab} días`;
  }

  // ─────────────────────────────────────────────
  // MODAL: Días no laborables ANA
  // ─────────────────────────────────────────────
  let modalDNL = null, dnlActivePk = null;
  const dnlCanEdit = window._PAGE.canEdit;

  function renderDNLRows(dias) {
    const tbody = document.getElementById('dnl-tbody');
    const empty = document.getElementById('dnl-empty');
    tbody.querySelectorAll('tr:not(#dnl-empty)').forEach(r => r.remove());
    if (!dias.length) { empty.style.display = ''; return; }
    empty.style.display = 'none';
    dias.forEach(d => {
      const tr = document.createElement('tr');
      tr.dataset.id = d.id;
      tr.innerHTML = `
        <td class="text-muted small">${d.descripcion || '—'}</td>
        <td class="text-center fw-semibold text-orange">${d.horas} h</td>
        ${dnlCanEdit ? `<td class="text-center"><button class="btn btn-sm btn-ghost-danger btn-dnl-del" data-id="${d.id}"><i class="ti ti-trash"></i></button></td>` : ''}
      `;
      tbody.appendChild(tr);
    });
  }

  function updateDNLTotals(totalHrs) {
    const diasEquiv = totalHrs > 0 ? +(totalHrs / 8).toFixed(2) : 0;
    document.getElementById('dnl-total-hrs').textContent  = totalHrs;
    document.getElementById('dnl-total-dias').textContent = diasEquiv;
    const badge = document.querySelector(`.dias-no-lab-badge-${dnlActivePk}`);
    if (badge) badge.innerHTML = diasEquiv > 0
      ? `<i class="ti ti-edit me-1"></i>${diasEquiv} días`
      : `<i class="ti ti-edit me-1"></i>—`;
  }

  document.querySelectorAll('.btn-dias-no-lab').forEach(btn => {
    btn.addEventListener('click', async function() {
      dnlActivePk = this.dataset.pk;
      document.getElementById('dnl-nombre').textContent = this.dataset.nombre;
      if (document.getElementById('dnl-horas')) document.getElementById('dnl-horas').value = '8.8';
      if (document.getElementById('dnl-desc'))  document.getElementById('dnl-desc').value  = '';
      document.getElementById('dnl-add-error')?.classList.add('d-none');
      if (!modalDNL) modalDNL = new bootstrap.Modal(document.getElementById('modalDiasNoLab'));
      modalDNL.show();
      const res = await fetch(`/reloj/compensatorio-calculo/${dnlActivePk}/dias-no-lab/`);
      const data = await res.json();
      if (data.ok) { renderDNLRows(data.dias); updateDNLTotals(data.total_hrs); }
    });
  });

  document.getElementById('btn-dnl-add')?.addEventListener('click', async function() {
    const horas  = document.getElementById('dnl-horas').value;
    const desc   = document.getElementById('dnl-desc').value;
    const errDiv = document.getElementById('dnl-add-error');
    errDiv.classList.add('d-none');
    if (!horas || parseFloat(horas) <= 0) {
      errDiv.querySelector('.alert').textContent = 'Ingresa un valor de horas válido.';
      errDiv.classList.remove('d-none'); return;
    }
    const btn = this; btn.disabled = true;
    const res  = await fetch(`/reloj/compensatorio-calculo/${dnlActivePk}/dias-no-lab/add/`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
      body: JSON.stringify({ horas: parseFloat(horas), descripcion: desc }),
    });
    btn.disabled = false;
    const data = await res.json();
    if (data.ok) {
      document.getElementById('dnl-horas').value = '8.8';
      document.getElementById('dnl-desc').value  = '';
      const r2 = await fetch(`/reloj/compensatorio-calculo/${dnlActivePk}/dias-no-lab/`);
      const d2 = await r2.json();
      if (d2.ok) { renderDNLRows(d2.dias); updateDNLTotals(d2.total_hrs); }
    } else {
      errDiv.querySelector('.alert').textContent = data.error || 'Error al agregar.';
      errDiv.classList.remove('d-none');
    }
  });

  document.getElementById('dnl-tbody').addEventListener('click', async function(e) {
    const btn = e.target.closest('.btn-dnl-del');
    if (!btn) return;
    btn.disabled = true;
    const res  = await fetch(`/reloj/compensatorio-dias-no-lab/${btn.dataset.id}/delete/`, {
      method: 'POST', headers: {'X-CSRFToken': CSRF},
    });
    const data = await res.json();
    if (data.ok) {
      const r2 = await fetch(`/reloj/compensatorio-calculo/${dnlActivePk}/dias-no-lab/`);
      const d2 = await r2.json();
      if (d2.ok) { renderDNLRows(d2.dias); updateDNLTotals(d2.total_hrs); }
    }
    btn.disabled = false;
  });

  // ─────────────────────────────────────────────
  // MODAL: Días adeudados
  // ─────────────────────────────────────────────
  let modalDA = null, daActivePk = null;

  document.querySelectorAll('.btn-set-dias-adeudados').forEach(btn => {
    btn.addEventListener('click', function() {
      daActivePk = this.dataset.pk;
      document.getElementById('da-nombre').textContent = this.dataset.nombre;
      document.getElementById('da-input').value = this.dataset.valor || '';
      if (!modalDA) modalDA = new bootstrap.Modal(document.getElementById('modalDiasAdeudados'));
      modalDA.show();
    });
  });

  document.getElementById('btn-guardar-dias-adeudados').addEventListener('click', async function() {
    const val = parseFloat(document.getElementById('da-input').value);
    if (isNaN(val) || val < 0) { document.getElementById('da-input').classList.add('is-invalid'); return; }
    document.getElementById('da-input').classList.remove('is-invalid');
    const btn = this; btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>';
    const res  = await fetch(`/reloj/compensatorio-calculo/${daActivePk}/set-dias-adeudados/`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
      body: JSON.stringify({ dias: val }),
    });
    const data = await res.json();
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
    if (data.ok) {
      const badge = document.querySelector(`.dias-adeudados-badge-${daActivePk}`);
      if (badge) badge.textContent = data.dias;
      const daBtn = document.querySelector(`.btn-set-dias-adeudados[data-pk="${daActivePk}"]`);
      if (daBtn) daBtn.dataset.valor = data.dias;
      const hCell = document.querySelector(`.horas-adeudadas-${daActivePk}`);
      if (hCell) hCell.textContent = `${data.horas_adeudadas} h`;
      updateRowTotals(daActivePk, data);
      if (modalDA) modalDA.hide();
    }
  });

  // ─────────────────────────────────────────────
  // MODAL: Factor h/día
  // ─────────────────────────────────────────────
  let modalFac = null, facActivePk = null;

  document.querySelectorAll('.btn-set-factor').forEach(btn => {
    btn.addEventListener('click', function() {
      facActivePk = this.dataset.pk;
      document.getElementById('fac-nombre').textContent = this.dataset.nombre;
      document.getElementById('fac-input').value = this.dataset.valor || '8';
      if (!modalFac) modalFac = new bootstrap.Modal(document.getElementById('modalFactor'));
      modalFac.show();
    });
  });

  document.getElementById('btn-guardar-factor').addEventListener('click', async function() {
    const val = parseFloat(document.getElementById('fac-input').value);
    if (isNaN(val) || val <= 0) { document.getElementById('fac-input').classList.add('is-invalid'); return; }
    document.getElementById('fac-input').classList.remove('is-invalid');
    const btn = this; btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>';
    const res  = await fetch(`/reloj/compensatorio-calculo/${facActivePk}/set-factor/`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
      body: JSON.stringify({ factor: val }),
    });
    const data = await res.json();
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
    if (data.ok) {
      const badge = document.querySelector(`.factor-badge-${facActivePk}`);
      if (badge) badge.textContent = `${data.factor} h/d`;
      const facBtn = document.querySelector(`.btn-set-factor[data-pk="${facActivePk}"]`);
      if (facBtn) facBtn.dataset.valor = data.factor;
      const hCell = document.querySelector(`.horas-adeudadas-${facActivePk}`);
      if (hCell) hCell.textContent = `${data.horas_adeudadas} h`;
      updateRowTotals(facActivePk, data);
      if (modalFac) modalFac.hide();
    }
  });

  // ─────────────────────────────────────────────
  // MODAL: Permisos extras (horas directas)
  // ─────────────────────────────────────────────
  let modalPE = null, peActivePk = null;

  document.querySelectorAll('.btn-set-permisos-extras').forEach(btn => {
    btn.addEventListener('click', function() {
      peActivePk = this.dataset.pk;
      document.getElementById('pe-nombre').textContent = this.dataset.nombre;
      document.getElementById('pe-input').value = this.dataset.valor || '';
      if (!modalPE) modalPE = new bootstrap.Modal(document.getElementById('modalPermisosExtras'));
      modalPE.show();
    });
  });

  document.getElementById('btn-guardar-permisos-extras').addEventListener('click', async function() {
    const val = parseFloat(document.getElementById('pe-input').value);
    if (isNaN(val) || val < 0) { document.getElementById('pe-input').classList.add('is-invalid'); return; }
    document.getElementById('pe-input').classList.remove('is-invalid');
    const btn = this; btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>';
    const res  = await fetch(`/reloj/compensatorio-calculo/${peActivePk}/set-permisos-extras/`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
      body: JSON.stringify({ horas: val }),
    });
    const data = await res.json();
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
    if (data.ok) {
      const badge = document.querySelector(`.permisos-extras-badge-${peActivePk}`);
      if (badge) badge.textContent = val > 0 ? `${val} h` : '—';
      const peBtn = document.querySelector(`.btn-set-permisos-extras[data-pk="${peActivePk}"]`);
      if (peBtn) peBtn.dataset.valor = val;
      updateRowTotals(peActivePk, data);
      if (modalPE) modalPE.hide();
    }
  });

  // ─────────────────────────────────────────────
  // MODAL: Min. autorizados/día
  // ─────────────────────────────────────────────
  let modalMD = null, mdActivePk = null;

  document.querySelectorAll('.btn-set-min-dia').forEach(btn => {
    btn.addEventListener('click', function() {
      mdActivePk = this.dataset.pk;
      document.getElementById('min-dia-nombre').textContent = this.dataset.nombre;
      document.getElementById('min-dia-input').value = this.dataset.valor || '';
      if (!modalMD) modalMD = new bootstrap.Modal(document.getElementById('modalMinDia'));
      modalMD.show();
    });
  });

  document.getElementById('btn-guardar-min-dia').addEventListener('click', async function() {
    const valor = parseInt(document.getElementById('min-dia-input').value);
    if (!valor || valor <= 0) { document.getElementById('min-dia-input').classList.add('is-invalid'); return; }
    document.getElementById('min-dia-input').classList.remove('is-invalid');
    const btn = this; btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';
    const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, minutos: valor });
    const res  = await fetch(`/reloj/compensatorio-calculo/${mdActivePk}/set-min-dia/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    const data = await res.json();
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
    if (data.ok) {
      const minBadge = document.querySelector(`.min-dia-badge-${mdActivePk}`);
      if (minBadge) minBadge.textContent = `${data.minutos_dia} min`;
      const habBadge = document.querySelector(`.dias-hab-badge-${mdActivePk}`);
      if (habBadge) habBadge.textContent = `${data.dias_habiles} días`;
      const ffBadge = document.querySelector(`.fecha-fin-badge-${mdActivePk}`);
      if (ffBadge) {
        ffBadge.className = `badge bg-green-lt text-green fs-6 px-3 fecha-fin-badge-${mdActivePk}`;
        ffBadge.innerHTML = `<i class="ti ti-calendar-check me-1"></i>${data.fecha_fin}`;
      }
      const row = document.querySelector(`tr[data-pk="${mdActivePk}"]`);
      const totalMin = parseInt(row?.dataset.totalMin) || 0;
      if (data.saldo !== undefined) updateSaldoBadge(mdActivePk, data.saldo);
      if (modalMD) modalMD.hide();
    }
  });

})();

// ── Bulk actions IIFE (only when canEdit) ──
if (window._PAGE.canEdit) {
(function(){
  const CSRF = window._PAGE.csrf;

  const getChecked = () => [...document.querySelectorAll('.chk-emp:checked')];

  function updateBulkBar() {
    const n = getChecked().length;
    const bar = document.getElementById('bulk-bar');
    bar.style.display = n > 0 ? 'flex' : 'none';
    document.getElementById('bulk-count').textContent = n;
  }

  document.getElementById('chk-all').addEventListener('change', function() {
    document.querySelectorAll('.chk-emp').forEach(c => c.checked = this.checked);
    updateBulkBar();
  });

  document.querySelectorAll('.chk-emp').forEach(c => c.addEventListener('change', updateBulkBar));

  // ── Bulk: días no laborables ──
  let modalBulkDNL = null;

  document.getElementById('btn-bulk-dias-no-lab').addEventListener('click', function() {
    const n = getChecked().length;
    if (!n) return;
    document.getElementById('bulk-dnl-count').textContent = n;
    document.getElementById('bulk-dnl-horas').value = '8.8';
    document.getElementById('bulk-dnl-desc').value  = '';
    document.getElementById('bulk-dnl-error').classList.add('d-none');
    document.getElementById('bulk-dnl-progress').classList.add('d-none');
    if (!modalBulkDNL) modalBulkDNL = new bootstrap.Modal(document.getElementById('modalBulkDiasNoLab'));
    modalBulkDNL.show();
  });

  document.getElementById('btn-bulk-dnl-apply').addEventListener('click', async function() {
    const horas = parseFloat(document.getElementById('bulk-dnl-horas').value);
    const desc  = document.getElementById('bulk-dnl-desc').value.trim();
    const errDiv = document.getElementById('bulk-dnl-error');
    errDiv.classList.add('d-none');
    if (!horas || horas <= 0) {
      errDiv.querySelector('.alert').textContent = 'Ingresa un valor de horas válido.';
      errDiv.classList.remove('d-none'); return;
    }
    const checked = getChecked();
    const btn = this; btn.disabled = true;
    const progDiv = document.getElementById('bulk-dnl-progress');
    const progBar = document.getElementById('bulk-dnl-bar');
    const progStatus = document.getElementById('bulk-dnl-status');
    progDiv.classList.remove('d-none');

    for (let i = 0; i < checked.length; i++) {
      const pk = checked[i].dataset.pk;
      progStatus.textContent = `Procesando ${i + 1} de ${checked.length}...`;
      progBar.style.width = `${Math.round((i / checked.length) * 100)}%`;
      await fetch(`/reloj/compensatorio-calculo/${pk}/dias-no-lab/add/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
        body: JSON.stringify({horas, descripcion: desc}),
      });
      // refresh badge for this row
      const r2 = await fetch(`/reloj/compensatorio-calculo/${pk}/dias-no-lab/`);
      const d2 = await r2.json();
      if (d2.ok) {
        const diasEquiv = d2.total_hrs > 0 ? +(d2.total_hrs / 8).toFixed(2) : 0;
        const badge = document.querySelector(`.dias-no-lab-badge-${pk}`);
        if (badge) badge.innerHTML = diasEquiv > 0
          ? `<i class="ti ti-edit me-1"></i>${diasEquiv} días`
          : `<i class="ti ti-edit me-1"></i>—`;
      }
    }
    progBar.style.width = '100%';
    progStatus.textContent = '¡Completado!';
    btn.disabled = false;
    setTimeout(() => { if (modalBulkDNL) modalBulkDNL.hide(); }, 800);
  });

  // ── Bulk: 3 días permisos extras ──
  document.getElementById('btn-bulk-3dias').addEventListener('click', async function() {
    const checked = getChecked();
    if (!checked.length) return;
    const btn = this; btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Aplicando...';

    for (const chk of checked) {
      const pk     = chk.dataset.pk;
      const factor = parseFloat(chk.dataset.factor) || 8.0;
      const horas  = Math.round(3 * factor * 100) / 100;
      const res    = await fetch(`/reloj/compensatorio-calculo/${pk}/set-permisos-extras/`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-CSRFToken': CSRF},
        body: JSON.stringify({horas}),
      });
      const data = await res.json();
      if (data.ok) {
        const badge = document.querySelector(`.permisos-extras-badge-${pk}`);
        if (badge) badge.textContent = `${horas} h`;
        const peBtn = document.querySelector(`.btn-set-permisos-extras[data-pk="${pk}"]`);
        if (peBtn) peBtn.dataset.valor = horas;
        const totalCell = document.querySelector(`.total-hrs-${pk}`);
        if (totalCell && data.total_hrs !== undefined) totalCell.textContent = `${data.total_hrs} h`;
        const habBadge = document.querySelector(`.dias-hab-badge-${pk}`);
        if (habBadge && data.dias_hab !== undefined) habBadge.textContent = `${data.dias_hab} días`;
        const row = document.querySelector(`tr[data-pk="${pk}"]`);
        if (row && data.total_min !== undefined) row.dataset.totalMin = data.total_min;
        // update saldo badge
        const saldoBadge = document.querySelector(`.saldo-badge-${pk}`);
        if (saldoBadge && data.saldo_min !== undefined) {
          if (data.saldo_min === 0) {
            saldoBadge.className = `badge bg-green-lt text-green saldo-badge-${pk}`;
            saldoBadge.innerHTML = '<i class="ti ti-circle-check me-1"></i>Completado';
          } else {
            saldoBadge.className = `badge bg-red-lt text-red saldo-badge-${pk}`;
            saldoBadge.textContent = `${+(data.saldo_min / 60).toFixed(1)} h`;
          }
        }
      }
    }
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-clock-plus me-1"></i>Aplicar 3 días perm. extras';
  });

})();
}
