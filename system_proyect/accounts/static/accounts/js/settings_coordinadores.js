(function(){
  const _cfg = document.getElementById('page-config');
  if (!_cfg) return;
  const CSRF = _cfg.dataset.csrf;
  let eliminarPk = null;

  window.abrirNuevo = function() {
    document.getElementById('coord-modal-title').textContent = 'Nuevo coordinador';
    document.getElementById('coord-pk').value     = '';
    document.getElementById('coord-area').value   = 'bilingue';
    document.getElementById('coord-codigo').value = '';
    document.getElementById('coord-nombre').value = '';
    document.getElementById('coord-usuario').value = '';
    document.getElementById('coord-activo').checked = true;
  };

  window.abrirEditar = function(pk, area, codigo, nombre, usuarioId, activo) {
    document.getElementById('coord-modal-title').textContent = 'Editar coordinador';
    document.getElementById('coord-pk').value      = pk;
    document.getElementById('coord-area').value    = area;
    document.getElementById('coord-codigo').value  = codigo;
    document.getElementById('coord-nombre').value  = nombre;
    document.getElementById('coord-usuario').value = usuarioId || '';
    document.getElementById('coord-activo').checked = activo;
    new bootstrap.Modal(document.getElementById('modalCoord')).show();
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
    const res  = await fetch(`/accounts/settings/conducta/coordinadores/${eliminarPk}/eliminar/`, {
      method: 'POST', headers: { 'X-CSRFToken': CSRF }
    });
    const data = await res.json();
    if (data.ok) location.reload();
    else { alert('Error: ' + data.error); this.disabled = false; this.textContent = 'Sí, eliminar'; }
  });
})();
