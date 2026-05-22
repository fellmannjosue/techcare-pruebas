/* inventario_por_categoria.js — uses window._CAT_PAGE bridge set in template */
$(function(){
  // DataTable por cada tab — grupo tipo keys come from bridge
  window._CAT_PAGE.tipoKeys.forEach(function(key){
    $('#tabla-' + key).DataTable({
      pageLength: 25,
      columnDefs: [{ orderable: false, targets: [0,4] }],
      language: { url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
    });
  });
  $('#tabla-sincategoria').DataTable({
    pageLength: 25,
    columnDefs: [{ orderable: false, targets: [0,4] }],
    language: { url: '//cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });

  // ── Seleccionar todo ──
  $(document).on('change', '.chk-all', function(){
    const tipo = $(this).data('tipo');
    const checked = this.checked;
    $(`#panel-${tipo} .chk-item`).prop('checked', checked);
    updateBulkBar(tipo);
  });

  // ── Checkbox individual ──
  $(document).on('change', '.chk-item', function(){
    const tipo = $(this).data('tipo');
    updateBulkBar(tipo);
    // Sincronizar chk-all
    const total = $(`#panel-${tipo} .chk-item`).length;
    const checked = $(`#panel-${tipo} .chk-item:checked`).length;
    $(`#panel-${tipo} .chk-all`).prop('indeterminate', checked > 0 && checked < total);
    $(`#panel-${tipo} .chk-all`).prop('checked', checked === total && total > 0);
  });

  function updateBulkBar(tipo) {
    const count = $(`#panel-${tipo} .chk-item:checked`).length;
    $(`#bulk-bar-${tipo}`).toggleClass('d-none', count === 0);
    $(`.bulk-count-${tipo}`).text(count);
  }

  // ── Limpiar selección ──
  $(document).on('click', '.btn-bulk-clear', function(){
    const tipo = $(this).data('tipo');
    $(`#panel-${tipo} .chk-item, #panel-${tipo} .chk-all`).prop('checked', false).prop('indeterminate', false);
    updateBulkBar(tipo);
  });

  // ── Aplicar bulk ──
  $(document).on('click', '.btn-bulk-apply', async function(){
    const tipo = $(this).data('tipo');
    const categoria = $(`#bulk-cat-${tipo}`).val();
    if (!categoria) { alert('Selecciona una categoría primero.'); return; }

    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Aplicando...';

    const CSRF     = window._CAT_PAGE.csrf;
    const BULK_URL = window._CAT_PAGE.bulkUrl;

    if (tipo === 'sincategoria') {
      // Agrupar por tipo_real
      const grupos = {};
      $(`#panel-sincategoria .chk-item:checked`).each(function(){
        const tipoReal = $(this).data('tipo-real');
        const id = $(this).data('id');
        if (!grupos[tipoReal]) grupos[tipoReal] = [];
        grupos[tipoReal].push(id);
      });

      const promesas = Object.entries(grupos).map(([tipoReal, ids]) => {
        const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, tipo: tipoReal, categoria });
        ids.forEach(id => body.append('ids', id));
        return fetch(BULK_URL, { method: 'POST', body });
      });
      await Promise.all(promesas);
    } else {
      const ids = [];
      $(`#panel-${tipo} .chk-item:checked`).each(function(){ ids.push($(this).data('id')); });
      const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, tipo, categoria });
      ids.forEach(id => body.append('ids', id));
      await fetch(BULK_URL, { method: 'POST', body });
    }

    location.reload();
  });
});
