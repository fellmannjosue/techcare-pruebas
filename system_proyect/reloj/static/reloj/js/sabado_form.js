document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('form input, form textarea, form select').forEach(function(el){
    if (el.type === 'checkbox') el.classList.add('form-check-input');
    else if (el.tagName === 'SELECT') el.classList.add('form-select');
    else if (!el.classList.contains('form-control')) el.classList.add('form-control');
  });
});

// ── Asignación de empleados (only in edit mode when obj exists) ──
if (window._PAGE && window._PAGE.hasBulkUrl) {
  const BULK_URL = window._PAGE.bulkUrl;
  const CSRF     = window._PAGE.csrf;

  document.getElementById('buscarEmpleado').addEventListener('input', function(){
    const q = this.value.toLowerCase();
    document.querySelectorAll('.emp-row').forEach(function(row){
      row.style.display = row.dataset.label.includes(q) ? '' : 'none';
    });
  });

  document.getElementById('btnSelAll').addEventListener('click', function(){
    document.querySelectorAll('.emp-row:not([style*="none"]) .emp-chk').forEach(function(chk){
      chk.checked = true;
      actualizarEstilo(chk);
    });
  });
  document.getElementById('btnDeselAll').addEventListener('click', function(){
    document.querySelectorAll('.emp-row:not([style*="none"]) .emp-chk').forEach(function(chk){
      chk.checked = false;
      actualizarEstilo(chk);
    });
  });

  document.querySelectorAll('.emp-chk').forEach(function(chk){
    chk.addEventListener('change', function(){ actualizarEstilo(this); });
  });

  function actualizarEstilo(chk){
    const lbl = document.getElementById('lbl-' + chk.value);
    if (!lbl) return;
    if (chk.checked) lbl.classList.add('bg-blue-lt');
    else             lbl.classList.remove('bg-blue-lt');
  }

  document.getElementById('btnGuardarAsig').addEventListener('click', function(){
    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Guardando…';

    const checked = Array.from(document.querySelectorAll('.emp-chk:checked')).map(c => c.value);
    const fd = new FormData();
    fd.append('csrfmiddlewaretoken', CSRF);
    checked.forEach(c => fd.append('emp_codes', c));

    fetch(BULK_URL, { method: 'POST', body: fd })
      .then(r => r.json())
      .then(function(res){
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i> Guardar selección';
        const $alert = document.getElementById('asig-alert');
        if (res.ok){
          document.getElementById('badge-total').textContent = res.total;
          $alert.className = 'alert alert-success';
          $alert.textContent = `Guardado: ${res.added} agregados, ${res.removed} removidos.`;
          $alert.classList.remove('d-none');
          setTimeout(() => $alert.classList.add('d-none'), 3000);
        } else {
          $alert.className = 'alert alert-danger';
          $alert.textContent = res.error || 'Error al guardar.';
          $alert.classList.remove('d-none');
        }
      })
      .catch(function(){
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i> Guardar selección';
        const $alert = document.getElementById('asig-alert');
        $alert.className = 'alert alert-danger';
        $alert.textContent = 'Error de red.';
        $alert.classList.remove('d-none');
      });
  });
}
