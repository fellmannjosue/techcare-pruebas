(function () {
  const _cfg = document.getElementById('page-config');
  if (!_cfg) return;
  const CSRF = _cfg.dataset.csrf;
  const URL_ASIGNAR_GRUPOS = _cfg.dataset.urlAsignarGrupos;

  // ── Selección múltiple ────────────────────────────────────
  const barra      = document.getElementById('barra-seleccion');
  const selCount   = document.getElementById('sel-count');
  const selPlural  = document.getElementById('sel-plural');
  const modalAG    = new bootstrap.Modal(document.getElementById('modalAsignarGrupos'));

  function getSelected() {
    return [...document.querySelectorAll('.chk-user:checked')].map(c => c.value);
  }

  function updateBarra() {
    const sel = getSelected();
    if (sel.length > 0) {
      selCount.textContent = sel.length;
      selPlural.textContent = sel.length > 1 ? 's' : '';
      barra.classList.remove('d-none');
      barra.style.display = 'flex';
    } else {
      barra.classList.add('d-none');
      barra.style.display = 'none';
    }
  }

  document.querySelectorAll('.chk-user').forEach(c =>
    c.addEventListener('change', updateBarra)
  );

  document.querySelectorAll('.chk-all').forEach(chkAll => {
    chkAll.addEventListener('change', function () {
      const table = this.closest('table');
      table.querySelectorAll('.chk-user').forEach(c => { c.checked = this.checked; });
      updateBarra();
    });
  });

  document.getElementById('btn-deselect-all').addEventListener('click', function () {
    document.querySelectorAll('.chk-user, .chk-all').forEach(c => { c.checked = false; });
    updateBarra();
  });

  document.getElementById('btn-abrir-asignar-grupos').addEventListener('click', function () {
    const n = getSelected().length;
    document.getElementById('asignar-count').textContent = n;
    document.getElementById('asignar-plural').textContent = n > 1 ? 's' : '';
    document.querySelectorAll('.chk-grupo-asignar').forEach(c => { c.checked = false; });
    document.getElementById('filtro-grupos-asignar').value = '';
    document.querySelectorAll('.grupo-asignar-item').forEach(el => { el.style.display = ''; });
    modalAG.show();
  });

  document.getElementById('filtro-grupos-asignar').addEventListener('input', function () {
    const q = this.value.toLowerCase();
    document.querySelectorAll('.grupo-asignar-item').forEach(el => {
      el.style.display = el.dataset.nombre.toLowerCase().includes(q) ? '' : 'none';
    });
  });

  document.getElementById('btn-confirmar-asignar-grupos').addEventListener('click', async function () {
    const userPks  = getSelected();
    const groupPks = [...document.querySelectorAll('.chk-grupo-asignar:checked')].map(c => c.value);
    const modo     = document.querySelector('input[name="modo-asignar"]:checked').value;
    if (!groupPks.length) { alert('Selecciona al menos un grupo.'); return; }
    const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, modo });
    userPks.forEach(pk  => body.append('user_pks',  pk));
    groupPks.forEach(pk => body.append('group_pks', pk));
    const res  = await fetch(URL_ASIGNAR_GRUPOS, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body,
    });
    const data = await res.json();
    if (data.ok) {
      modalAG.hide();
      location.reload();
    } else {
      alert(data.error || 'Error al asignar grupos.');
    }
  });

  // ── Eliminar usuario ──────────────────────────────────────
  let activePk = null;
  document.querySelectorAll('.btn-del-user').forEach(btn => {
    btn.addEventListener('click', function () {
      activePk = this.dataset.pk;
      document.getElementById('del-user-nombre').textContent = this.dataset.nombre;
      new bootstrap.Modal(document.getElementById('modalDelUser')).show();
    });
  });
  document.getElementById('btn-confirm-del-user').addEventListener('click', async function () {
    const res  = await fetch(`/accounts/settings/usuarios/${activePk}/eliminar/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ csrfmiddlewaretoken: CSRF }),
    });
    const data = await res.json();
    if (data.ok) location.reload();
    else alert(data.error || 'Error al eliminar.');
  });

  // ── Toggle permisos (solo superuser) ─────────────────────
  let togglePk = null;
  document.querySelectorAll('.btn-toggle-perms').forEach(btn => {
    btn.addEventListener('click', function () {
      togglePk = this.dataset.pk;
      const nombre   = this.dataset.nombre;
      const puedeVer = this.dataset.puede === 'true';
      const msg = document.getElementById('toggle-perms-msg');
      if (msg) {
        msg.innerHTML = puedeVer
          ? `¿<strong>Quitar</strong> acceso a Usuarios/Grupos de <strong>${nombre}</strong>?`
          : `¿<strong>Conceder</strong> acceso a Usuarios/Grupos a <strong>${nombre}</strong>?`;
      }
      const btnConfirm = document.getElementById('btn-confirm-toggle-perms');
      if (btnConfirm) {
        btnConfirm.className = puedeVer
          ? 'btn btn-danger'
          : 'btn btn-success';
        btnConfirm.innerHTML = puedeVer
          ? '<i class="ti ti-shield-off me-1"></i>Quitar permiso'
          : '<i class="ti ti-shield-check me-1"></i>Conceder permiso';
      }
      new bootstrap.Modal(document.getElementById('modalTogglePerms')).show();
    });
  });

  const btnConfirmToggle = document.getElementById('btn-confirm-toggle-perms');
  if (btnConfirmToggle) {
    btnConfirmToggle.addEventListener('click', async function () {
      const res  = await fetch(`/accounts/settings/usuarios/${togglePk}/toggle-perms/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams({ csrfmiddlewaretoken: CSRF }),
      });
      const data = await res.json();
      if (data.ok) {
        // Update badge in-place without reload
        const badge = document.querySelector(`.perm-badge-${togglePk}`);
        const toggleBtn = document.querySelector(`.btn-toggle-perms[data-pk="${togglePk}"]`);
        if (badge) {
          if (data.puede_ver) {
            badge.className = `badge bg-green-lt text-green perm-badge-${togglePk}`;
            badge.innerHTML = '<i class="ti ti-check me-1"></i>Habilitado';
          } else {
            badge.className = `badge bg-muted-lt text-muted perm-badge-${togglePk}`;
            badge.innerHTML = 'No';
          }
        }
        if (toggleBtn) {
          toggleBtn.dataset.puede = data.puede_ver ? 'true' : 'false';
        }
        bootstrap.Modal.getInstance(document.getElementById('modalTogglePerms')).hide();
      } else {
        alert(data.error || 'Error al cambiar permiso.');
      }
    });
  }
})();

// ── Filtro cliente por grupo (tabla Usuarios) ─────────────
(function () {
  const sel   = document.getElementById('filtro-grupo-reg');
  const badge = document.getElementById('reg-count-badge');
  if (!sel) return;

  sel.addEventListener('change', function () {
    const val = this.value.toLowerCase();
    const tabla = document.querySelector('#tabla-reg-users');
    if (!tabla) return;
    let visible = 0;
    tabla.querySelectorAll('tr[data-grupos]').forEach(tr => {
      const grupos = tr.dataset.grupos.toLowerCase();
      const show = !val || grupos.includes(val);
      tr.style.display = show ? '' : 'none';
      if (show) visible++;
    });
    if (badge) badge.textContent = visible;
  });
})();
