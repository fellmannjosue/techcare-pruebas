const CSRF      = window._PAGE.csrf;
const URL_SAVE  = window._PAGE.urlSave;
const URL_EDITAR= window._PAGE.urlEditar;

document.addEventListener('DOMContentLoaded', function(){
  const sinCfg = document.querySelectorAll('tr[data-fecha=""]').length;
  document.getElementById('count-sin-config').textContent = sinCfg;
});

// Buscador (filtra en todas las tablas/tabs)
document.getElementById('buscar').addEventListener('input', function(){
  const q = this.value.toLowerCase();
  document.querySelectorAll('.tabla-vac tbody tr').forEach(tr => {
    if (!tr.dataset.nombre) return;
    tr.style.display = tr.dataset.nombre.toLowerCase().includes(q) ? '' : 'none';
  });
});

// ── Modal editar días usados ──────────────────────────────────
let modalEU = null;

document.querySelectorAll('.btn-editar-usados').forEach(btn => {
  btn.addEventListener('click', function () {
    if (!modalEU) modalEU = new bootstrap.Modal(document.getElementById('modalEditarUsados'));
    document.getElementById('eu-emp-code').value             = this.dataset.emp;
    document.getElementById('eu-nombre').value               = this.dataset.nombre;
    document.getElementById('eu-nombre-display').textContent = this.dataset.nombre;
    document.getElementById('eu-emp-display').textContent    = 'Cód. ' + this.dataset.emp;
    document.getElementById('eu-dias').value                 = this.dataset.usados;
    modalEU.show();
  });
});

document.getElementById('btn-guardar-usados').addEventListener('click', function () {
  const btn      = this;
  const empCode  = document.getElementById('eu-emp-code').value;
  const nombre   = document.getElementById('eu-nombre').value;
  const diasVal  = parseFloat(document.getElementById('eu-dias').value);
  if (isNaN(diasVal) || diasVal < 0) { alert('Ingresa un número válido.'); return; }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

  fetch(URL_EDITAR, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
    body: JSON.stringify({ emp_code: empCode, nombre, dias_usados: diasVal }),
  })
  .then(r => r.json())
  .then(data => {
    if (!data.ok) { alert('Error: ' + data.error); return; }
    const tr  = document.querySelector(`tr[data-emp="${empCode}"]`);
    if (tr) {
      const usados = data.dias_usados;
      const acum   = data.acumulada;

      const tdUsados = tr.querySelector('.td-usados');
      tdUsados.querySelector('.btn-editar-usados').dataset.usados = usados;
      const valEl = tdUsados.querySelector('.td-usados-val');
      if (usados > 0) {
        valEl.className = 'text-orange fw-semibold td-usados-val';
        valEl.textContent = usados;
      } else {
        valEl.className = 'text-muted td-usados-val';
        valEl.textContent = '0';
      }

      // <--- hecho por claude code: la acumulada depende de los usados; la proporcional no cambia
      const tdAcum = tr.querySelector('.td-acumulada');
      if (tdAcum && acum !== undefined) {
        const cls = acum <= 0 ? 'bg-red-lt text-red' : acum <= 5 ? 'bg-orange-lt text-orange' : 'bg-green-lt text-green';
        tdAcum.innerHTML = `<span class="badge ${cls} fw-bold">${acum}</span>`;
      }
    }
    if (modalEU) modalEU.hide();
  })
  .catch(() => alert('Error de conexión'))
  .finally(() => {
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-check me-1"></i>Guardar';
  });
});

// Abrir modal configurar
document.querySelectorAll('.btn-cfg').forEach(btn => {
  btn.addEventListener('click', function(){
    const tr     = this.closest('tr');
    const emp    = this.dataset.emp;
    const nombre = this.dataset.nombre;
    const docente= this.dataset.docente === 'true';
    const fecha  = this.dataset.fecha || '';
    const fijos  = tr.dataset.fijos || '';
    const grupo  = tr.dataset.grupo || '';

    document.getElementById('cfg-emp-code').value             = emp;
    document.getElementById('cfg-nombre').value               = nombre;
    document.getElementById('cfg-nombre-display').textContent = nombre;
    document.getElementById('cfg-emp-display').textContent    = 'Cód. ' + emp;
    document.getElementById('cfg-fecha').value                = fecha;
    document.getElementById('cfg-dias-fijos').value           = fijos;

    // Seleccionar radio según tipo
    if (fijos) {
      document.getElementById('cfg-tipo-fijos').checked    = true;
      document.getElementById('cfg-tipo-docente').checked  = false;
      document.getElementById('cfg-tipo-nodocente').checked= false;
    } else {
      document.getElementById('cfg-tipo-docente').checked  = docente;
      document.getElementById('cfg-tipo-nodocente').checked= !docente;
      document.getElementById('cfg-tipo-fijos').checked    = false;
    }
    document.getElementById('escala-info').style.display = (!fijos && !docente) ? '' : 'none';
    document.getElementById('fijos-info').style.display  = fijos ? '' : 'none';
    // Grupo BL/Colegio (solo docente)
    document.querySelectorAll('input[name="cfg-grupo"]').forEach(g => { g.checked = (g.value === grupo); });
    document.getElementById('grupo-info').style.display = (docente && !fijos) ? '' : 'none';

    new bootstrap.Modal(document.getElementById('modalConfig')).show();
  });
});

document.querySelectorAll('input[name="cfg-tipo"]').forEach(r => {
  r.addEventListener('change', function(){
    document.getElementById('escala-info').style.display = this.value === 'nodocente' ? '' : 'none';
    document.getElementById('fijos-info').style.display  = this.value === 'fijos'     ? '' : 'none';
    document.getElementById('grupo-info').style.display  = this.value === 'docente'   ? '' : 'none';
  });
});

// Guardar configuración
document.getElementById('btn-guardar-cfg').addEventListener('click', function(){
  const btn       = this;
  const empCode   = document.getElementById('cfg-emp-code').value;
  const nombre    = document.getElementById('cfg-nombre').value;
  const tipoVal   = document.querySelector('input[name="cfg-tipo"]:checked').value;
  const esDocente = tipoVal === 'docente';
  const fecha     = document.getElementById('cfg-fecha').value;
  const diasFijos = tipoVal === 'fijos' ? parseInt(document.getElementById('cfg-dias-fijos').value) || null : null;
  const grupoEl   = document.querySelector('input[name="cfg-grupo"]:checked');
  const grupoDoc  = (esDocente && grupoEl) ? grupoEl.value : '';

  if (tipoVal === 'fijos' && !diasFijos) {
    alert('Ingresa los días fijos para el caso especial.');
    return;
  }
  if (esDocente && !grupoDoc) {
    alert('Selecciona si el docente es BL o Colegio.');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

  fetch(URL_SAVE, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
    body: JSON.stringify({ emp_code: empCode, nombre, es_docente: esDocente, grupo_docente: grupoDoc, fecha_inicio: fecha, dias_fijos: diasFijos }),
  })
  .then(r => r.json())
  .then(data => {
    if (!data.ok) { alert('Error: ' + data.error); btn.disabled = false; btn.innerHTML = '<i class="ti ti-check me-1"></i>Guardar'; return; }
    // La fila puede cambiar de tab (no docente ⇄ docente BL/Colegio ⇄ caso especial): recargar.
    location.reload();
  })
  .catch(() => {
    alert('Error de conexión');
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-check me-1"></i>Guardar';
  });
});
