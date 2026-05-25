(function () {
  const _cfg = document.getElementById('page-config');
  if (!_cfg) return;
  const CSRF = _cfg.dataset.csrf;

  // ── Modal ver usuarios del grupo ──
  const modalUsuarios = new bootstrap.Modal(document.getElementById('modalUsuariosGrupo'));
  document.querySelectorAll('.btn-ver-usuarios').forEach(btn => {
    btn.addEventListener('click', async function () {
      const pk     = this.dataset.pk;
      const nombre = this.dataset.nombre;
      document.getElementById('modal-grupo-nombre').textContent = nombre;
      document.getElementById('modal-usuarios-loading').classList.remove('d-none');
      document.getElementById('modal-usuarios-empty').classList.add('d-none');
      document.getElementById('modal-usuarios-lista').innerHTML = '';
      modalUsuarios.show();
      const res  = await fetch(`/accounts/settings/grupos/${pk}/usuarios/`);
      const data = await res.json();
      document.getElementById('modal-usuarios-loading').classList.add('d-none');
      if (!data.ok || !data.usuarios.length) {
        document.getElementById('modal-usuarios-empty').classList.remove('d-none');
        return;
      }
      const lista = document.getElementById('modal-usuarios-lista');
      data.usuarios.forEach(u => {
        const fullname = [u.first_name, u.last_name].filter(Boolean).join(' ');
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex align-items-center gap-3 py-2';
        li.innerHTML = `
          <span class="avatar avatar-sm bg-blue-lt text-blue">
            <i class="ti ti-user"></i>
          </span>
          <div>
            <div class="fw-semibold">${u.username}</div>
            ${fullname ? `<div class="small text-muted">${fullname}</div>` : ''}
          </div>
          <span class="ms-auto badge ${u.is_active ? 'bg-success-lt text-success' : 'bg-danger-lt text-danger'}">
            ${u.is_active ? 'Activo' : 'Inactivo'}
          </span>`;
        lista.appendChild(li);
      });
    });
  });

  // ── Modal eliminar grupo ──
  let activePk = null;
  document.querySelectorAll('.btn-del-grupo').forEach(btn => {
    btn.addEventListener('click', function () {
      activePk = this.dataset.pk;
      document.getElementById('del-grupo-nombre').textContent = this.dataset.nombre;
      new bootstrap.Modal(document.getElementById('modalDelGrupo')).show();
    });
  });
  document.getElementById('btn-confirm-del-grupo').addEventListener('click', async function () {
    const res  = await fetch(`/accounts/settings/grupos/${activePk}/eliminar/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ csrfmiddlewaretoken: CSRF }),
    });
    const data = await res.json();
    if (data.ok) location.reload();
    else alert(data.error || 'Error al eliminar.');
  });
})();
