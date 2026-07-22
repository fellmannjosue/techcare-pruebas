/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #form_convocatoria-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("form_convocatoria-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
  };
})();

(function () {
  const HORARIO_URL = CFG.v0;
  const MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
  const PARCIAL_ROM = {1:'I',2:'II',3:'III',4:'IV'};
  const DIAS = [1,2,3,4,5];
  let gradoNum = null, seccion = '';

  try { if (window.jQuery) $('#id_alumno').select2({ placeholder:'-- Selecciona un estudiante --', width:'100%' }); } catch (e) {}

  const ORDINAL = {'1ero':1,'1mo':1,'primero':1,'2do':2,'segundo':2,'3ero':3,'3ro':3,'tercero':3,
    '4to':4,'cuarto':4,'5to':5,'quinto':5,'6to':6,'sexto':6,'7mo':7,'septimo':7,'séptimo':7,
    '8vo':8,'octavo':8,'9no':9,'noveno':9};
  function parseGrado(txt) {
    const m = (txt||'').match(/([0-9A-Za-zªºáéíóú]+)\s*-\s*([0-9A-Za-z_]+)\s*$/);
    if (!m) return { num:null, sec:'' };
    const crso = m[1].toLowerCase();
    const sec = m[2].replace(/^_+/, '');
    let num = ORDINAL[crso];
    if (num == null) { const d = crso.match(/^(\d+)/); num = d ? +d[1] : null; }
    if (num && num >= 1 && num <= 9) return { num, sec };
    return { num:null, sec };
  }
  function parcialParts() {
    const v = (document.getElementById('sel_parcial').value || '').split('|');
    return { parcial: parseInt(v[0]), anio: parseInt(v[1]) };
  }

  async function cargarAsignaturas() {
    const cont = document.getElementById('asig-container');
    const { parcial, anio } = parcialParts();
    document.getElementById('id_parcial').value = parcial || '';
    document.getElementById('id_anio').value = anio || '';
    if (!gradoNum || !parcial) {
      cont.innerHTML = '<div class="text-muted small py-3">Selecciona un estudiante y el parcial para ver las tutorías disponibles.</div>';
      actualizarPreview();
      return;
    }
    cont.innerHTML = '<div class="text-muted small py-3"><span class="spinner-border spinner-border-sm me-2"></span>Cargando tutorías del grado…</div>';
    let d;
    try {
      const r = await fetch(`${HORARIO_URL}?grado_num=${gradoNum}&parcial=${parcial}&anio=${anio}`);
      d = await r.json();
    } catch (err) {
      cont.innerHTML = '<div class="alert alert-danger py-2 mb-0 small">No se pudieron cargar las tutorías. Recarga la página (Ctrl+F5).</div>';
      return;
    }
    if (!d.items || !d.items.length) {
      cont.innerHTML = '<div class="alert alert-warning py-2 mb-0 small">Este grado no tiene tutorías configuradas en este parcial. Pide al coordinador configurar el horario.</div>';
      actualizarPreview();
      return;
    }
    cont.innerHTML = '';
    d.items.forEach(function (it, idx) {
      const row = document.createElement('div');
      row.className = 'asig-row';
      let diasHtml = '<div class="dias">';
      DIAS.forEach(function (n) {
        const on = it.dias.includes(n) ? 'on' : '';
        diasHtml += `<span class="dia-btn locked ${on}" data-dia="${n}">${['','L','M','M','J','V'][n]}</span>`;
      });
      diasHtml += '</div>';
      row.innerHTML =
        `<label class="form-check m-0"><input class="form-check-input chk-asig" type="checkbox"></label>` +
        `<span class="asig-chip" style="background:${it.color}"></span>` +
        `<span class="fw-semibold">${it.asignatura}</span>` +
        diasHtml;
      row.dataset.asignatura = it.asignatura;
      cont.appendChild(row);
    });
    // Los días son fijos (vienen del horario): no se editan.
    cont.querySelectorAll('.chk-asig').forEach(c => c.addEventListener('change', actualizarPreview));
    // Edición: marcar las asignaturas que ya estaban convocadas
    if (window._convPreset && window.CONV_ASIGS && window.CONV_ASIGS.length) {
      cont.querySelectorAll('.asig-row').forEach(function (row) {
        if (window.CONV_ASIGS.indexOf(row.dataset.asignatura) >= 0) {
          const chk = row.querySelector('.chk-asig'); if (chk) chk.checked = true;
        }
      });
      window._convPreset = false;
    }
    actualizarPreview();
  }

  function recolectar() {
    const out = [];
    document.querySelectorAll('#asig-container .asig-row').forEach(function (row) {
      const chk = row.querySelector('.chk-asig');
      if (!chk || !chk.checked) return;
      const dias = [];
      row.querySelectorAll('.dia-btn.on').forEach(b => dias.push(parseInt(b.dataset.dia)));
      if (dias.length) out.push({ asignatura: row.dataset.asignatura, dias });
    });
    return out;
  }

  function actualizarPreview() {
    const sel = document.getElementById('id_alumno');
    const nombre = sel.value ? (sel.options[sel.selectedIndex].dataset.nombre || '') : '';
    document.getElementById('pv-alumno').textContent = nombre || '__________';
    document.getElementById('pv-grado').textContent = gradoNum ? (window.GRADO_LABELS[gradoNum] || gradoNum) : '____';
    document.getElementById('pv-seccion').textContent = seccion || '__';
    const { parcial } = parcialParts();
    document.getElementById('pv-parcial').textContent = PARCIAL_ROM[parcial] || '—';
    const f = document.getElementById('id_fecha').value;
    if (f) { const dd = f.split('-'); document.getElementById('pv-fecha').textContent = `${+dd[2]} días del mes de ${MESES[+dd[1]-1]} del año ${dd[0]}`; }
    const items = recolectar();
    const tb = document.getElementById('pv-tbody');
    if (!items.length) { tb.innerHTML = '<tr><td colspan="7" style="color:#999;">Sin asignaturas seleccionadas</td></tr>'; return; }
    tb.innerHTML = items.map(function (it, i) {
      const cels = DIAS.map(n => `<td>${it.dias.includes(n) ? '✔' : ''}</td>`).join('');
      return `<tr><td>${i+1}</td><td>${it.asignatura}</td>${cels}</tr>`;
    }).join('');
  }

  // Cambio de estudiante. select2 dispara 'change' vía jQuery, así que si jQuery
  // está disponible escuchamos con jQuery; si no, con listener nativo.
  function onAlumnoChange() {
    const selEl = document.getElementById('id_alumno');
    const opt = selEl.options[selEl.selectedIndex];
    const g = parseGrado(opt ? opt.getAttribute('data-grado') : '');
    gradoNum = g.num; seccion = g.sec;
    const gr = opt ? (opt.getAttribute('data-grado') || '') : '';
    document.getElementById('grado-display').value = gr;
    document.getElementById('id_grado').value = gr;
    document.getElementById('id_alumno_nombre').value = opt ? (opt.getAttribute('data-nombre') || '') : '';
    cargarAsignaturas();
  }
  if (window.jQuery) { $('#id_alumno').on('change', onAlumnoChange); }
  else { document.getElementById('id_alumno').addEventListener('change', onAlumnoChange); }
  document.getElementById('sel_parcial').addEventListener('change', cargarAsignaturas);
  document.getElementById('id_fecha').addEventListener('change', actualizarPreview);

  document.getElementById('formConvocatoria').addEventListener('submit', function (e) {
    const items = recolectar();
    if (!items.length) { e.preventDefault(); alert('Marca al menos una asignatura con días.'); return; }
    document.getElementById('id_asignaturas_json').value = JSON.stringify(items);
  });

  // init
  const { parcial, anio } = parcialParts();
  document.getElementById('id_parcial').value = parcial || '';
  document.getElementById('id_anio').value = anio || '';
  // Edición: si ya hay alumno seleccionado, disparar la carga de asignaturas
  if (document.getElementById('id_alumno').value) {
    if (window.jQuery) { $('#id_alumno').trigger('change'); }
    else { document.getElementById('id_alumno').dispatchEvent(new Event('change')); }
  }
})();
window.GRADO_LABELS = {1:'Primero',2:'Segundo',3:'Tercero',4:'Cuarto',5:'Quinto',6:'Sexto',7:'Séptimo',8:'Octavo',9:'Noveno'};
window.CONV_ASIGS = CFG.j1;
window._convPreset = window.CONV_ASIGS.length > 0;
