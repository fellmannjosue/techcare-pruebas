// CRUD genérico para las entidades de inventario de cámaras.
// Un solo modal (#modalForm) se reutiliza para crear y editar.
$(function () {
  const SPANISH = {
    lengthMenu: "Mostrar _MENU_", zeroRecords: "Sin resultados",
    info: "Mostrando _START_ a _END_ de _TOTAL_", infoEmpty: "Sin registros",
    infoFiltered: "(de _MAX_)", search: "Buscar:",
    paginate: { first: "«", last: "»", next: "›", previous: "‹" }
  };

  $('.ic-table').each(function () {
    try { $(this).DataTable({ pageLength: 15, language: SPANISH }); }
    catch (e) { console.warn('DataTable:', e); }
  });

  const modalEl = document.getElementById('modalForm');
  if (!modalEl) return;
  const modal = bootstrap.Modal.getOrCreateInstance(modalEl);
  const form  = document.getElementById('entityForm');
  const createUrl = window.location.pathname;

  function clearForm() {
    form.reset();
    form.querySelectorAll('select[multiple] option').forEach(o => o.selected = false);
  }

  // ── Nuevo ──
  $('#btnNuevo').on('click', function () {
    clearForm();
    form.action = createUrl;
    $('#modalFormTitle').html('<i class="ti ti-plus me-2 text-primary"></i>Nuevo registro');
    modal.show();
  });

  // ── Editar ──
  $(document).on('click', '.btn-edit', function () {
    const url = $(this).data('url');
    $.getJSON(url, function (d) {
      clearForm();
      Object.keys(d).forEach(function (k) {
        const el = document.getElementById('id_' + k);
        if (!el) return;
        const val = d[k];
        if (el.multiple && Array.isArray(val)) {
          const set = val.map(String);
          Array.from(el.options).forEach(o => { o.selected = set.includes(o.value); });
        } else {
          el.value = (val === null || val === undefined) ? '' : val;
        }
      });
      form.action = url;  // POST a la URL de edición
      $('#modalFormTitle').html('<i class="ti ti-pencil me-2 text-primary"></i>Editar registro');
      modal.show();
    }).fail(() => Swal.fire('Error', 'No se pudo cargar el registro.', 'error'));
  });

  // ── Eliminar ──
  $(document).on('click', '.btn-delete', function () {
    const url = $(this).data('url');
    const id  = $(this).data('id') || 'registro';
    Swal.fire({
      title: '¿Eliminar ' + id + '?',
      text: 'Esta acción no se puede deshacer.',
      icon: 'warning', showCancelButton: true,
      confirmButtonText: 'Sí, eliminar', cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d63939',
    }).then(r => {
      if (r.isConfirmed) {
        const f = $('<form method="post">').attr('action', url);
        f.append($('<input type="hidden" name="csrfmiddlewaretoken">').val(window.CSRF_TOKEN));
        $('body').append(f); f.submit();
      }
    });
  });
});
