function abrirEditarGrupos(userId, nombre, gruposActivos) {
  document.getElementById('grp-user-id').value = userId;
  document.getElementById('grp-nombre').textContent = nombre;
  document.querySelectorAll('.grp-check').forEach(cb => {
    cb.checked = gruposActivos.includes(parseInt(cb.dataset.grpId));
  });
  new bootstrap.Modal(document.getElementById('modalGrupos')).show();
}

document.getElementById('buscar-usuario').addEventListener('input', function() {
  const q = this.value.toLowerCase();
  document.querySelectorAll('#tabla-roles .fila-usuario').forEach(fila => {
    const texto = fila.textContent.toLowerCase();
    fila.style.display = texto.includes(q) ? '' : 'none';
  });
});
