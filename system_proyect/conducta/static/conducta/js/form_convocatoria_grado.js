/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #form_convocatoria_grado-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("form_convocatoria_grado-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return {
    v0: d.v0,
    j0: j(d.v0),
    v1: d.v1,
    j1: j(d.v1),
    v2: d.v2,
    j2: j(d.v2),
    v3: d.v3,
    j3: j(d.v3),
    v4: d.v4,
    j4: j(d.v4),
    v5: d.v5,
    j5: j(d.v5),
    v6: d.v6,
    j6: j(d.v6),
    v7: d.v7,
    j7: j(d.v7),
    v8: d.v8,
    j8: j(d.v8),
    v9: d.v9,
    j9: j(d.v9),
    v10: d.v10,
    j10: j(d.v10),
  };
})();

(function () {
  var CSRF = (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
  var P = { parcial: CFG.j6, anio: CFG.j7, grado_num: CFG.j8, seccion: CFG.v0 };
  var SUBJECTS = CFG.j9;
  var GRADO_LABEL = CFG.v1;
  var PARCIAL_ROM = CFG.v2;
  var MI_NOMBRE = CFG.v3;
  var ES_COORD = CFG.j10;
  var DIA_AB = ['','L','M','M','J','V'];

  // Guardado al instante + "Solicitó: nombre" + bloqueo tras registrar
  document.querySelectorAll('.conv-chk').forEach(function (chk) {
    chk.addEventListener('change', function () {
      var tr = chk.closest('tr');
      var por = chk.closest('td').querySelector('.conv-por');
      var marcado = chk.checked;
      chk.disabled = true; // evita doble clic mientras guarda
      fetch(CFG.v4, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF },
        body: JSON.stringify({
          parcial: P.parcial, anio: P.anio, grado_num: P.grado_num, seccion: P.seccion,
          alumno_id: tr.dataset.alumno, alumno_nombre: tr.dataset.nombre,
          asignatura: chk.dataset.asig, checked: marcado,
        }),
      }).then(r => r.json()).then(function (d) {
        if (!d.ok) { chk.checked = !marcado; chk.disabled = false; alert(d.error || 'No se pudo guardar'); return; }
        if (marcado) {
          if (por) por.textContent = 'Solicitó: ' + MI_NOMBRE;
        } else {
          if (por) por.textContent = '';
        }
        chk.disabled = false;  // queda habilitado: cualquiera puede corregir
      }).catch(function () { chk.checked = !marcado; chk.disabled = false; alert('Error de red'); });
    });
  });

  // ── Vista previa de cartas (Siguiente página) ──
  var v1 = document.getElementById('conv-ventana1');
  var v2 = document.getElementById('conv-ventana2');
  var cartas = [], idx = 0;

  function recolectarCartas() {
    var diasDe = {}; SUBJECTS.forEach(function (s) { diasDe[s.asignatura] = s.dias || []; });
    var out = [];
    document.querySelectorAll('#conv-ventana1 tbody tr[data-alumno]').forEach(function (tr) {
      var asigs = [];
      tr.querySelectorAll('.conv-chk:checked').forEach(function (c) { asigs.push(c.dataset.asig); });
      if (asigs.length) out.push({ nombre: tr.dataset.nombre, asigs: asigs, diasDe: diasDe });
    });
    return out;
  }
  function fechaTexto() {
    var t = CFG.v5.split('-');
    var M = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre'];
    return (+t[2]) + ' días del mes de ' + M[+t[1]-1] + ' del año ' + t[0];
  }
  function render() {
    var wrap = document.getElementById('prev-wrap');
    var vacio = document.getElementById('prev-vacio');
    if (!cartas.length) { wrap.innerHTML = ''; vacio.style.display = ''; document.getElementById('prev-cont').textContent = '0 / 0'; return; }
    vacio.style.display = 'none';
    if (idx < 0) idx = 0; if (idx >= cartas.length) idx = cartas.length - 1;
    var c = cartas[idx];
    var filas = c.asigs.map(function (a, i) {
      var dl = c.diasDe[a] || [];
      var cels = [1,2,3,4,5].map(function (n) { return '<td>' + (dl.indexOf(n) >= 0 ? '✔' : '') + '</td>'; }).join('');
      return '<tr><td>' + (i+1) + '</td><td class="asig">' + a + '</td>' + cels + '</tr>';
    }).join('');
    wrap.innerHTML =
      '<div class="conv-prev-card"><div class="school">NUEVO AMANECER SCHOOL</div>' +
      '<div style="text-align:center;font-size:.72rem;color:#555;">Aldea La Venta, km. 36 carretera hacia Olancho · Tels. 2758-0300 / 9485-4082</div>' +
      '<div style="text-align:center;font-weight:bold;margin:8px 0;">COMPROMISO DE ASISTENCIA A TUTORÍA</div>' +
      '<p style="text-align:justify;font-size:.82rem;">El C.E.B.N.G.B. Nuevo Amanecer pone a disposición de los padres un sistema de tutorías gratuitas de lunes a viernes de <b>7:00 – 7:45 a.m.</b> Vigencia durante todo el <b>' + PARCIAL_ROM + '</b> parcial.</p>' +
      '<p style="font-size:.82rem;">Su hijo (a) <b>' + c.nombre + '</b> del <b>' + GRADO_LABEL + '</b> ha sido convocado a las siguientes tutorías:</p>' +
      '<table><thead><tr><th>Nº</th><th>Asignatura(s)</th><th>L</th><th>M</th><th>M</th><th>J</th><th>V</th></tr></thead><tbody>' + filas + '</tbody></table>' +
      '<p style="font-size:.75rem;color:#555;">Dado a los ' + fechaTexto() + '.</p>' +
      '<div style="display:flex;justify-content:space-between;margin-top:34px;font-size:.7rem;text-align:center;font-weight:bold;">' +
      '<div style="border-top:1px solid #000;width:30%;padding-top:2px;">PADRE / ENCARGADO</div>' +
      '<div style="border-top:1px solid #000;width:30%;padding-top:2px;">DOCENTE GUÍA</div>' +
      '<div style="border-top:1px solid #000;width:30%;padding-top:2px;">COORDINADOR DE ÁREA</div></div></div>';
    document.getElementById('prev-cont').textContent = (idx+1) + ' / ' + cartas.length;
  }
  var bs = document.getElementById('btn-siguiente');
  if (bs) bs.addEventListener('click', function () { cartas = recolectarCartas(); idx = 0; v1.style.display = 'none'; v2.style.display = ''; render(); });
  var bv = document.getElementById('btn-volver1');
  if (bv) bv.addEventListener('click', function () { v2.style.display = 'none'; v1.style.display = ''; });
  var pa = document.getElementById('prev-ant'); if (pa) pa.addEventListener('click', function () { idx--; render(); });
  var ps = document.getElementById('prev-sig'); if (ps) ps.addEventListener('click', function () { idx++; render(); });
})();
