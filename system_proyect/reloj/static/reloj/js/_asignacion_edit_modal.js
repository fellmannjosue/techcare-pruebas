(function () {
  // Select2 en el select de empleado dentro del modal
  if (window.jQuery && $.fn.select2) {
    $('#editarAsignacionModal #id_emp_dropdown').select2({
      theme: 'bootstrap-5',
      width: '100%',
      placeholder: 'Selecciona un empleado...',
      allowClear: true,
      dropdownParent: $('#editarAsignacionModal')
    });
  }

  // Validación fecha fin >= inicio
  document.getElementById('formEditarAsignacion').addEventListener('submit', function (e) {
    const fi = this.querySelector('[name="fecha_inicio"]')?.value;
    const ff = this.querySelector('[name="fecha_fin"]')?.value;
    if (fi && ff && ff < fi) {
      e.preventDefault();
      alert('La Fecha fin debe ser mayor o igual que la Fecha inicio.');
    }
  });
})();
