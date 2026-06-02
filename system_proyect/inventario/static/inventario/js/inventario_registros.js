/* inventario_registros.js — uses window._REG_PAGE bridge set in template */

function iniciarTabla(idTabla) {
  $('#' + idTabla).DataTable({
    pageLength: 25,
    autoWidth: false,
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.4/i18n/es-ES.json' }
  });
}

$(function(){
  iniciarTabla('tablaComputadoras');
  iniciarTabla('tablaImpresoras');
  iniciarTabla('tablaTelevisores');
  iniciarTabla('tablaRouters');
  iniciarTabla('tablaDataShows');
  iniciarTabla('tablaMonitores');

  // ── Sub-tabs: filtrar tablaComputadoras por prefijo de Asset ID ───────────
  let _prefijo_activo = '';

  // Filtro personalizado: extrae el texto plano de la celda Asset ID (col 1)
  $.fn.dataTable.ext.search.push(function (settings, data) {
    if (settings.nTable.id !== 'tablaComputadoras') return true;
    if (!_prefijo_activo) return true;
    const texto = $('<div>').html(data[1]).text().trim();
    return texto.startsWith(_prefijo_activo);
  });

  $('#subtabs-prefijo').on('click', 'button', function () {
    $('#subtabs-prefijo button').removeClass('active');
    $(this).addClass('active');
    _prefijo_activo = $(this).data('prefijo') || '';
    $('#tablaComputadoras').DataTable().draw();
  });
});

(function(){
  const CSRF = window._REG_PAGE.csrf;
  let catModo = 'single'; // 'single' | 'bulk'
  let catCompId = null, catTipo = null, catBulkIds = [];

  // ── Helpers ───────────────────────────────────────────
  function getChecked(tipo) {
    return [...document.querySelectorAll(`.chk-cat-item[data-tipo="${tipo}"]:checked`)].map(c => c.value);
  }

  function updateBulkBar(tipo) {
    const ids = getChecked(tipo);
    const bar = document.getElementById(`bulk-bar-${tipo}`);
    if (!bar) return;
    if (ids.length > 0) {
      bar.classList.remove('d-none'); bar.classList.add('d-flex');
      bar.querySelector('.bulk-count').textContent = ids.length;
    } else {
      bar.classList.add('d-none'); bar.classList.remove('d-flex');
    }
  }

  function updateCatBadge(id, tipo, categoria) {
    const suffix = `-${id}-${tipo}`;
    const badge  = document.querySelector(`.cat-badge${suffix}`);
    if (!badge) return;
    if (categoria) {
      badge.className = `badge bg-purple-lt text-purple cat-badge${suffix}`;
      badge.textContent = categoria;
    } else {
      badge.className = `text-muted cat-badge${suffix}`;
      badge.textContent = '—';
    }
    $(`.btn-cat[data-id="${id}"][data-tipo="${tipo}"]`).data('cat', categoria || '');
  }

  // ── Checkboxes select-all ─────────────────────────────
  $(document).on('change', '.chk-all-cat', function(){
    const tipo = $(this).data('tipo');
    document.querySelectorAll(`.chk-cat-item[data-tipo="${tipo}"]`).forEach(c => c.checked = this.checked);
    updateBulkBar(tipo);
  });

  $(document).on('change', '.chk-cat-item', function(){
    const tipo = $(this).data('tipo');
    const total   = document.querySelectorAll(`.chk-cat-item[data-tipo="${tipo}"]`).length;
    const checked = getChecked(tipo).length;
    const allChk  = document.querySelector(`.chk-all-cat[data-tipo="${tipo}"]`);
    if (allChk) allChk.checked = (total === checked);
    updateBulkBar(tipo);
  });

  // ── Quitar selección (lote) ───────────────────────────
  $(document).on('click', '.btn-bulk-desel', function(){
    const tipo = $(this).data('tipo');
    document.querySelectorAll(`.chk-cat-item[data-tipo="${tipo}"]`).forEach(c => c.checked = false);
    const allChk = document.querySelector(`.chk-all-cat[data-tipo="${tipo}"]`);
    if (allChk) allChk.checked = false;
    updateBulkBar(tipo);
  });

  // ── Abrir modal categoría (individual) ───────────────
  $(document).on('click', '.btn-cat', function(){
    catModo   = 'single';
    catCompId = $(this).data('id');
    catTipo   = $(this).data('tipo');
    document.getElementById('cat-modal-asset').textContent = $(this).data('asset');
    document.getElementById('cat-select').value = $(this).data('cat') || '';
    new bootstrap.Modal(document.getElementById('modalAsignarCategoria')).show();
  });

  // ── Abrir modal categoría (lote) ─────────────────────
  $(document).on('click', '.btn-bulk-cat', function(){
    const tipo = $(this).data('tipo');
    const ids  = getChecked(tipo);
    if (!ids.length) return;
    catModo    = 'bulk';
    catTipo    = tipo;
    catBulkIds = ids;
    document.getElementById('cat-modal-asset').textContent = `${ids.length} equipos seleccionados`;
    document.getElementById('cat-select').value = '';
    new bootstrap.Modal(document.getElementById('modalAsignarCategoria')).show();
  });

  // ── Guardar categoría ─────────────────────────────────
  document.getElementById('btn-guardar-cat').addEventListener('click', async function(){
    const valor = document.getElementById('cat-select').value;
    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

    if (catModo === 'single') {
      const url  = `/inventario/${catTipo}/categoria/${catCompId}/`;
      const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, categoria: valor });
      const res  = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
      const data = await res.json();
      if (data.ok) updateCatBadge(catCompId, catTipo, data.categoria);
    } else {
      const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, tipo: catTipo, categoria: valor });
      catBulkIds.forEach(id => body.append('ids', id));
      const res  = await fetch('/inventario/categoria-bulk/', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
      const data = await res.json();
      if (data.ok) {
        catBulkIds.forEach(id => updateCatBadge(id, catTipo, data.categoria));
        document.querySelectorAll(`.chk-cat-item[data-tipo="${catTipo}"]`).forEach(c => c.checked = false);
        const allChk = document.querySelector(`.chk-all-cat[data-tipo="${catTipo}"]`);
        if (allChk) allChk.checked = false;
        updateBulkBar(catTipo);
      }
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
    bootstrap.Modal.getInstance(document.getElementById('modalAsignarCategoria')).hide();
  });
})();

(function(){
  const CSRF = window._REG_PAGE.csrf;
  let modoGrupo = 'single'; // 'single' | 'bulk'
  let grupoCompId = null;

  // ── Helpers ──────────────────────────────────────────
  function seleccionados() {
    return [...document.querySelectorAll('.chk-comp:checked')].map(c => c.value);
  }

  function actualizarBulkBar() {
    const ids = seleccionados();
    const bar = document.getElementById('bulk-bar');
    if (ids.length > 0) {
      bar.classList.remove('d-none');
      bar.classList.add('d-flex');
      document.getElementById('bulk-count').textContent = ids.length;
    } else {
      bar.classList.add('d-none');
      bar.classList.remove('d-flex');
    }
  }

  function updateBadge(id, grupo) {
    const badge = document.getElementById(`grupo-badge-${id}`);
    if (!badge) return;
    if (grupo) {
      badge.className = 'badge bg-azure-lt';
      badge.textContent = `Grupo ${grupo}`;
    } else {
      badge.className = 'text-muted';
      badge.textContent = '—';
    }
    $(`.btn-asignar-grupo[data-id="${id}"]`).data('grupo', grupo || '');
  }

  // ── Checkboxes ────────────────────────────────────────
  document.getElementById('chk-all-comp').addEventListener('change', function(){
    document.querySelectorAll('.chk-comp').forEach(c => c.checked = this.checked);
    actualizarBulkBar();
  });

  $(document).on('change', '.chk-comp', function(){
    const total = document.querySelectorAll('.chk-comp').length;
    const checked = seleccionados().length;
    document.getElementById('chk-all-comp').checked = (total === checked);
    actualizarBulkBar();
  });

  // ── Abrir modal individual ────────────────────────────
  $(document).on('click', '.btn-asignar-grupo', function(){
    modoGrupo = 'single';
    grupoCompId = $(this).data('id');
    document.getElementById('grupo-modal-desc').innerHTML =
      'Equipo: <strong>' + $(this).data('asset') + '</strong>';
    document.getElementById('grupo-input').value = $(this).data('grupo') || '';
    new bootstrap.Modal(document.getElementById('modalAsignarGrupo')).show();
  });

  // ── Abrir modal en lote ───────────────────────────────
  document.getElementById('btn-bulk-grupo').addEventListener('click', function(){
    const ids = seleccionados();
    if (!ids.length) return;
    modoGrupo = 'bulk';
    document.getElementById('grupo-modal-desc').innerHTML =
      '<strong>' + ids.length + ' equipos</strong> seleccionados';
    document.getElementById('grupo-input').value = '';
    new bootstrap.Modal(document.getElementById('modalAsignarGrupo')).show();
  });

  // ── Quitar selección ──────────────────────────────────
  document.getElementById('btn-bulk-desel').addEventListener('click', function(){
    document.querySelectorAll('.chk-comp').forEach(c => c.checked = false);
    document.getElementById('chk-all-comp').checked = false;
    actualizarBulkBar();
  });

  // ── Guardar ───────────────────────────────────────────
  document.getElementById('btn-guardar-grupo').addEventListener('click', async function(){
    const valor = document.getElementById('grupo-input').value.trim();
    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

    if (modoGrupo === 'single') {
      const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, grupo: valor });
      const res  = await fetch(`/inventario/computadora/grupo/${grupoCompId}/`, {
        method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body
      });
      const data = await res.json();
      if (data.ok) updateBadge(grupoCompId, data.grupo);

    } else {
      const ids  = seleccionados();
      const body = new URLSearchParams({ csrfmiddlewaretoken: CSRF, grupo: valor });
      ids.forEach(id => body.append('ids', id));
      const res  = await fetch('/inventario/computadora/grupo-bulk/', {
        method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body
      });
      const data = await res.json();
      if (data.ok) {
        ids.forEach(id => updateBadge(id, data.grupo));
        // Deseleccionar tras aplicar
        document.querySelectorAll('.chk-comp').forEach(c => c.checked = false);
        document.getElementById('chk-all-comp').checked = false;
        actualizarBulkBar();
      }
    }

    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
    bootstrap.Modal.getInstance(document.getElementById('modalAsignarGrupo')).hide();
  });
})();
