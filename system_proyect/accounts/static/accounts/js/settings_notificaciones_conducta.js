(function(){
  const _cfg = document.getElementById('page-config');
  if (!_cfg) return;
  const CSRF = _cfg.dataset.csrf;
  let eliminarPk = null;

  window.abrirNuevo = function() {
    document.getElementById('notif-modal-title').textContent = 'Nueva regla de notificación';
    document.getElementById('notif-pk').value = '';
    document.getElementById('notif-area').value = 'bilingue';
    document.getElementById('notif-coord').value = '';
    ['notif-conductual','notif-infac','notif-infco','notif-progress'].forEach(id => document.getElementById(id).checked = false);
    document.getElementById('notif-activo').checked = true;
  };

  window.abrirEditar = function(pk, area, coordId, conductual, infAc, infCo, progress, activo) {
    document.getElementById('notif-modal-title').textContent = 'Editar regla';
    document.getElementById('notif-pk').value    = pk;
    document.getElementById('notif-area').value  = area;
    document.getElementById('notif-coord').value = coordId;
    document.getElementById('notif-conductual').checked = conductual;
    document.getElementById('notif-infac').checked      = infAc;
    document.getElementById('notif-infco').checked      = infCo;
    document.getElementById('notif-progress').checked   = progress;
    document.getElementById('notif-activo').checked     = activo;
    new bootstrap.Modal(document.getElementById('modalNotif')).show();
  };

  document.querySelectorAll('.btn-eliminar').forEach(btn => {
    btn.addEventListener('click', function() {
      eliminarPk = this.dataset.pk;
      document.getElementById('del-nombre').textContent = '"' + this.dataset.nombre + '"';
      new bootstrap.Modal(document.getElementById('modalEliminar')).show();
    });
  });

  document.getElementById('btn-confirmar-eliminar').addEventListener('click', async function() {
    this.disabled = true;
    this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Eliminando...';
    const res  = await fetch(`/accounts/settings/conducta/notificaciones/${eliminarPk}/eliminar/`, {
      method: 'POST', headers: { 'X-CSRFToken': CSRF }
    });
    const data = await res.json();
    if (data.ok) location.reload();
    else { alert('Error: ' + data.error); this.disabled = false; this.textContent = 'Sí, eliminar'; }
  });
})();
