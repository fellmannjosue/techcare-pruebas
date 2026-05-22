(function(){
  const CSRF        = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  const URL_SET     = window._PAGE.urlSet;
  const URL_LIST    = window._PAGE.urlList;
  const URL_DELETE  = window._PAGE.urlDelete;
  const URL_SAVE    = window._PAGE.urlSave;
  const URL_BALANCE = window._PAGE.urlBalance;
  const CAN_DELETE  = window._PAGE.canDelete;
  const TIPO_COLORS = window._PAGE.tipoColors;

  const PER_PAGE = 8;
  let allPermisos = [], currentPage = 1;
  let activeCellEmp = null, activeCellMes = null, activeCellNombre = null, activeCellCampo = null;

  // ── DataTable ──
  document.addEventListener('DOMContentLoaded', function(){
    if (typeof $.fn.DataTable !== 'undefined') {
      $('#tabla-permisos').DataTable({
        order: [[0, 'asc']],
        pageLength: 50,
        columnDefs: [{ orderable: false, targets: [1,2,3,4,5,6,7,8,9,10,11] }],
        language: { url: 'https://cdn.datatables.net/plug-ins/1.13.6/i18n/es-ES.json' }
      });
    }
  });

  function tipoColor(tipo){ return TIPO_COLORS[tipo] || '#e9ecef'; }

  // ── Renderizar página del historial ──
  function renderPagina() {
    const tbody  = document.getElementById('mhp-tbody');
    const vacio  = document.getElementById('mhp-vacio');
    const pag    = document.getElementById('mhp-paginacion');
    const info   = document.getElementById('mhp-info');
    const total  = allPermisos.length;
    const totalPag = Math.ceil(total / PER_PAGE);

    tbody.innerHTML = '';

    if (total === 0) {
      vacio.classList.remove('d-none');
      pag.classList.add('d-none');
      return;
    }
    vacio.classList.add('d-none');

    const inicio = (currentPage - 1) * PER_PAGE;
    const slice  = allPermisos.slice(inicio, inicio + PER_PAGE);

    slice.forEach(function(p){
      const fechaDisplay = p.fecha_fin ? p.fecha + ' → ' + p.fecha_fin : p.fecha;
      const diasCell  = p.horas != null
        ? '<span class="text-muted small">' + parseFloat(p.dias).toFixed(2).replace(/\.?0+$/, '') + 'd</span>'
        : '<span class="fw-bold">'          + parseFloat(p.dias).toFixed(2).replace(/\.?0+$/, '') + 'd</span>';
      const horasCell = p.horas != null
        ? '<span class="fw-bold text-primary">' + parseFloat(p.horas).toFixed(2).replace(/\.?0+$/, '') + 'h</span>'
        : '<span class="text-muted">—</span>';
      const tr = document.createElement('tr');
      tr.innerHTML =
        '<td class="small">' + fechaDisplay + '</td>' +
        '<td><span class="badge" style="background:' + tipoColor(p.tipo) + ';color:#333">' + p.label + '</span></td>' +
        '<td class="text-center">' + diasCell  + '</td>' +
        '<td class="text-center">' + horasCell + '</td>' +
        '<td class="text-muted small">' + (p.razon || '—') + '</td>' +
        '<td class="text-center">' +
          (CAN_DELETE
            ? '<button class="btn btn-xs btn-outline-danger p-0 btn-del-hist" data-pk="' + p.pk + '" title="Eliminar" style="width:22px;height:22px;line-height:1.4"><i class="ti ti-trash" style="font-size:.7rem"></i></button>'
            : '') +
        '</td>';
      tbody.appendChild(tr);
    });

    if (totalPag > 1) {
      pag.classList.remove('d-none');
      info.textContent = (inicio+1) + '–' + Math.min(inicio+PER_PAGE, total) + ' de ' + total;
      document.getElementById('mhp-prev').disabled = currentPage <= 1;
      document.getElementById('mhp-next').disabled = currentPage >= totalPag;
    } else {
      pag.classList.add('d-none');
    }
  }

  // ── Helpers vacaciones ──
  async function fetchBalance() {
    const sinCfg = document.getElementById('mhp-vac-sin-cfg');
    const cards  = document.getElementById('mhp-vac-cards');
    try {
      const res  = await fetch(URL_BALANCE + '?emp_code=' + encodeURIComponent(activeCellEmp));
      const data = await res.json();
      if (!data.ok) return;
      if (!data.tiene_config) {
        sinCfg.classList.remove('d-none');
        cards.classList.add('d-none');
      } else {
        sinCfg.classList.add('d-none');
        cards.classList.remove('d-none');
        const dispEl = document.getElementById('mhp-vac-disponibles');
        dispEl.textContent = data.dias_disponibles;
        dispEl.className   = 'fw-bold fs-3 ' + (data.dias_disponibles <= 0 ? 'text-danger' : data.dias_disponibles <= 3 ? 'text-warning' : 'text-success');
      }
    } catch(e) {}
  }

  async function fetchList() {
    document.getElementById('mhp-loading').classList.remove('d-none');
    document.getElementById('mhp-contenido').classList.add('d-none');
    try {
      const res  = await fetch(URL_LIST + '?emp_code=' + encodeURIComponent(activeCellEmp) + '&mes=' + activeCellMes + '&tipo=' + encodeURIComponent(activeCellCampo));
      const data = await res.json();
      allPermisos = data.ok ? data.permisos : [];
      currentPage = 1;
    } catch(e) { allPermisos = []; }
    document.getElementById('mhp-loading').classList.add('d-none');
    document.getElementById('mhp-contenido').classList.remove('d-none');
    renderPagina();
    // actualizar celda en tabla principal
    const totalMes = allPermisos.reduce(function(s, p){ return s + parseFloat(p.dias); }, 0);
    const cellBtn  = document.querySelector('.btn-permiso-cell[data-emp="' + activeCellEmp + '"][data-campo="' + activeCellCampo + '"]');
    if (cellBtn) {
      if (totalMes > 0) {
        const t = parseFloat(totalMes.toFixed(2));
        cellBtn.innerHTML = t + 'd';
        cellBtn.className = 'btn-permiso-cell has-value cell-' + activeCellCampo.replace('_dias','').replace('_','-');
      } else {
        cellBtn.innerHTML = '—';
        cellBtn.className = 'btn-permiso-cell no-value';
      }
    }
  }

  // ── Abrir modal al clic en celda ──
  document.querySelectorAll('.btn-permiso-cell').forEach(function(btn){
    btn.addEventListener('click', async function(){
      activeCellEmp    = this.dataset.emp;
      activeCellMes    = this.dataset.mes;
      activeCellNombre = this.dataset.nombre;
      activeCellCampo  = this.dataset.campo;
      const label      = this.dataset.label;

      document.getElementById('mhp-subtitulo').textContent = activeCellNombre + ' · ' + label + ' · ' + activeCellMes;

      const esVac = activeCellCampo === 'vacaciones_dias';
      document.getElementById('mhp-vac-info').classList.toggle('d-none', !esVac);
      if (esVac) {
        document.getElementById('mhp-vac-sin-cfg').classList.add('d-none');
        document.getElementById('mhp-vac-cards').classList.add('d-none');
        document.getElementById('mhp-add-fecha')?.setAttribute('value', '');
        document.getElementById('mhp-add-fecha-fin')?.setAttribute('value', '');
        document.getElementById('mhp-add-dias')?.setAttribute('value', '');
        document.getElementById('mhp-add-horas')?.setAttribute('value', '');
        document.getElementById('mhp-add-razon')?.setAttribute('value', '');
        fetchBalance();
      }

      new bootstrap.Modal(document.getElementById('modalHistorialPermisos')).show();
      await fetchList();
    });
  });

  // ── Paginacion ──
  document.getElementById('mhp-prev').addEventListener('click', function(){ currentPage--; renderPagina(); });
  document.getElementById('mhp-next').addEventListener('click', function(){ currentPage++; renderPagina(); });

  // ── Eliminar desde historial ──
  document.getElementById('mhp-tbody').addEventListener('click', async function(e){
    const btn = e.target.closest('.btn-del-hist');
    if (!btn) return;
    const pk = btn.dataset.pk;
    if (!confirm('Eliminar este permiso?')) return;
    btn.disabled = true;
    try {
      const res  = await fetch(URL_DELETE.replace('99999', pk), {
        method: 'POST', headers: {'X-CSRFToken': CSRF}
      });
      const data = await res.json();
      if (data.ok) {
        await fetchList();
        if (activeCellCampo === 'vacaciones_dias') await fetchBalance();
      } else {
        alert('Error: ' + (data.error || 'No se pudo eliminar.'));
        btn.disabled = false;
      }
    } catch(e) { btn.disabled = false; }
  });

  // ── Toggle Pierde Bono ──
  document.querySelectorAll('.btn-pierde-bono').forEach(function(btn){
    btn.addEventListener('click', async function(){
      const nuevoValor = this.dataset.valor === '1' ? '0' : '1';
      const body = new URLSearchParams({
        csrfmiddlewaretoken: CSRF,
        emp_code: this.dataset.emp,
        mes:      this.dataset.mes,
        campo:    'pierde_bono',
        valor:    nuevoValor,
      });
      try {
        const res  = await fetch(URL_SET, { method: 'POST', body });
        const data = await res.json();
        if (data.ok) {
          this.dataset.valor = nuevoValor;
          if (nuevoValor === '1') {
            this.className = 'btn btn-sm btn-danger btn-pierde-bono';
            this.innerHTML = '<i class="ti ti-x"></i> Sí';
          } else {
            this.className = 'btn btn-sm btn-ghost-secondary btn-pierde-bono';
            this.innerHTML = '<i class="ti ti-minus"></i> No';
          }
        }
      } catch(e) {}
    });
  });
})();
