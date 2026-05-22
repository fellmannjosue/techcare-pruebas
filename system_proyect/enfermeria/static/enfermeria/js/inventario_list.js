/* enfermeria/js/inventario_list.js */
$(function () {
  // Mensaje de éxito desde sesión Django (via window._PAGE)
  if (window._PAGE && window._PAGE.mensajeExito) {
    Swal.fire({
      icon: 'success',
      title: '¡Éxito!',
      text: window._PAGE.mensajeExito,
      timer: 2000,
      showConfirmButton: false
    });
  }

  $('#inventario-table').DataTable({
    pageLength: 15,
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });
});
