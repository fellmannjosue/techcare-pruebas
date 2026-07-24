/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #vacaciones_list-config (un .js no lo procesa Django). */
const CFG_VACACIONES_LIST = (function(){
  var d = document.getElementById("vacaciones_list-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
  };
})();

window._PAGE = {
  csrf:      CFG_VACACIONES_LIST.v0,
  urlSave:   CFG_VACACIONES_LIST.v1,
  urlEditar: CFG_VACACIONES_LIST.v2
};


/* <--- hecho por claude code: lógica recuperada; se había perdido al extraer el JS
   del HTML (solo quedó el puente de configuración de arriba). */

const CSRF      = window._PAGE.csrf;
const URL_SAVE  = window._PAGE.urlSave;
const URL_EDITAR= window._PAGE.urlEditar;

document.addEventListener('DOMContentLoaded', function(){
  const sinCfg = document.querySelectorAll('tr[data-fecha=""]').length;
  document.getElementById('count-sin-config').textContent = sinCfg;
});

// Buscador
document.getElementById('buscar').addEventListener('input', function(){
  const q = this.value.toLowerCase();
  document.querySelectorAll('#tablaVacaciones tbody tr').forEach(tr => {
    tr.style.display = (tr.dataset.nombre || '').toLowerCase().includes(q) ? '' : 'none';
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
      const disp   = data.dias_disponibles;
      const dc     = data.dias_corresponden;

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

      const tdDisp = tr.querySelector('.td-disponibles');
      if (dc > 0) {
        const cls = disp <= 0 ? 'bg-red-lt text-red' : disp <= 5 ? 'bg-orange-lt text-orange' : 'bg-green-lt text-green';
        tdDisp.innerHTML = `<span class="badge ${cls} fw-bold">${disp}</span>`;
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
    const emp    = this.dataset.emp;
    const nombre = this.dataset.nombre;
    const docente= this.dataset.docente === 'true';
    const fecha  = this.dataset.fecha || '';
    const fijos  = this.closest('tr').dataset.fijos || '';

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

    new bootstrap.Modal(document.getElementById('modalConfig')).show();
  });
});

document.querySelectorAll('input[name="cfg-tipo"]').forEach(r => {
  r.addEventListener('change', function(){
    document.getElementById('escala-info').style.display = this.value === 'nodocente' ? '' : 'none';
    document.getElementById('fijos-info').style.display  = this.value === 'fijos'     ? '' : 'none';
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

  if (tipoVal === 'fijos' && !diasFijos) {
    alert('Ingresa los días fijos para el caso especial.');
    return;
  }

  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando...';

  fetch(URL_SAVE, {
    method: 'POST',
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
    body: JSON.stringify({ emp_code: empCode, nombre, es_docente: esDocente, fecha_inicio: fecha, dias_fijos: diasFijos }),
  })
  .then(r => r.json())
  .then(data => {
    if (!data.ok) { alert('Error: ' + data.error); return; }

    const tr = document.querySelector(`tr[data-emp="${empCode}"]`);
    if (tr) {
      tr.dataset.docente = esDocente ? 'true' : 'false';
      tr.dataset.fecha   = fecha;
      tr.dataset.fijos   = diasFijos || '';

      // Actualizar badge tipo
      if (diasFijos) {
        tr.querySelector('.td-tipo').innerHTML =
          `<span class="badge bg-yellow-lt text-yellow"><i class="ti ti-star me-1"></i>Caso especial · ${diasFijos}d</span>`;
      } else if (esDocente) {
        tr.querySelector('.td-tipo').innerHTML =
          '<span class="badge bg-blue-lt text-blue"><i class="ti ti-school me-1"></i>Docente</span>';
      } else {
        tr.querySelector('.td-tipo').innerHTML =
          '<span class="badge bg-green-lt text-green"><i class="ti ti-briefcase me-1"></i>No docente</span>';
      }

      if (fecha) {
        const [y,m,d] = fecha.split('-');
        tr.querySelector('.td-fecha').textContent = `${d}/${m}/${y}`;
      }

      const años = data.años;
      const tdA = tr.querySelector('.td-años');
      if (años === null || años === undefined) tdA.innerHTML = '<span class="text-muted">—</span>';
      else if (años === 0) tdA.innerHTML = '<span class="text-muted small">< 1 año</span>';
      else tdA.textContent = años + (años === 1 ? ' año' : ' años');

      const dc = data.dias_corresponden;
      tr.querySelector('.td-corresponden').innerHTML = dc > 0
        ? `<span class="fw-bold text-primary">${dc}</span>`
        : '<span class="text-muted">0</span>';

      const usadosEl = tr.querySelector('.td-usados-val');
      const usados   = parseFloat(usadosEl ? usadosEl.textContent : 0) || 0;
      const disp     = dc - usados;
      const tdD      = tr.querySelector('.td-disponibles');
      if (dc > 0) {
        const cls = disp <= 0 ? 'bg-red-lt text-red' : disp <= 5 ? 'bg-orange-lt text-orange' : 'bg-green-lt text-green';
        tdD.innerHTML = `<span class="badge ${cls} fw-bold">${disp}</span>`;
      }

      const btnCfg = tr.querySelector('.btn-cfg');
      if (btnCfg) {
        btnCfg.dataset.docente = esDocente ? 'true' : 'false';
        btnCfg.dataset.fecha   = fecha;
      }
    }

    bootstrap.Modal.getInstance(document.getElementById('modalConfig')).hide();
  })
  .catch(() => alert('Error de conexión'))
  .finally(() => {
    btn.disabled = false;
    btn.innerHTML = '<i class="ti ti-check me-1"></i>Guardar';
  });
});
