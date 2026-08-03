/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #maestro-config (un .js no lo procesa Django). */
const CFG_MAESTRO = (function(){
  var d = document.getElementById("maestro-config").dataset;
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
  };
})();

window._PAGE = Object.assign(window._PAGE || {}, {
  csrf:      CFG_MAESTRO.v0,
  urlSave:   CFG_MAESTRO.v1,
  urlFin:    CFG_MAESTRO.v2,
  gradoSel:  CFG_MAESTRO.v3,
  seccionSel:CFG_MAESTRO.v4,
  urlMaestro:CFG_MAESTRO.v5,
});


/* ─────────────────────────────────────────────────────────────────────
   <--- hecho por claude code: esta lógica se había perdido al sacar el JS del
   HTML; el maestro NO podía guardar su comentario ni marcar Finalizado.
   Recuperada de 45698c8.
   ───────────────────────────────────────────────────────────────────── */
/* notas_parcial/maestro.js
   Bridge vars injected via window._PAGE from maestro.html:
     csrf, urlSave, urlFin, gradoSel, seccionSel, urlMaestro
*/
(function () {
  const URL_SAVE = window._PAGE.urlSave;
  const URL_FIN  = window._PAGE.urlFin;
  const CSRF     = window._PAGE.csrf;

  // ── Contador de palabras (máx 40) ──
  function contarPalabras(s) { return (s.trim().match(/\S+/g) || []).length; }
  function actualizarContador(ta) {
    const box = ta.closest('.cmt-box'); if (!box) return;
    const w = contarPalabras(ta.value);
    const lbl = box.querySelector('.cmt-words');
    if (lbl) { lbl.textContent = w + '/40 palabras'; lbl.className = 'cmt-words small ' + (w > 40 ? 'text-danger fw-bold' : 'text-muted'); }
  }
  document.addEventListener('input', function (e) {
    if (e.target && e.target.classList.contains('comentario-txt')) actualizarContador(e.target);
  });
  document.querySelectorAll('.comentario-txt').forEach(actualizarContador);

  // ── Guardar comentario (tu propio comentario; máx 40 palabras) ──
  async function guardar(slide) {
    const box = slide.querySelector('.cmt-box');
    const ta  = slide.querySelector('.comentario-txt');
    const btn = slide.querySelector('.btn-guardar-uno');
    const msg = slide.querySelector('.estado-msg');
    if (contarPalabras(ta.value) > 40) {
      msg.className = 'estado-msg saved-err'; msg.textContent = '✗ Máx. 40 palabras';
      return;
    }
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
      const res = await fetch(URL_SAVE, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ingr_egr_id: slide.dataset.iid,
          parcial:     slide.dataset.parcial,
          anio:        slide.dataset.anio,
          area:        slide.dataset.area,
          maestro_id:  box ? box.dataset.maestro : null,
          comentario:  ta.value,
        }),
      });
      const d = await res.json();
      if (d.ok) {
        msg.className   = 'estado-msg saved-ok';
        msg.textContent = '✓ Guardado';
        btn.innerHTML = '<i class="ti ti-circle-check me-1"></i>Guardado';
        btn.classList.replace('btn-success', 'btn-outline-success');
      } else {
        msg.className   = 'estado-msg saved-err';
        msg.textContent = '✗ ' + (d.error || 'Error al guardar');
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar comentario';
      }
    } catch (e) {
      msg.className = 'estado-msg saved-err'; msg.textContent = '✗ Error';
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar comentario';
    }
  }

  document.querySelectorAll('.btn-guardar-uno').forEach(btn => {
    btn.addEventListener('click', () => guardar(btn.closest('.slide-alumno')));
  });

  // ── Carrusel ──
  const slides  = Array.from(document.querySelectorAll('.slide-alumno'));
  if (!slides.length) return;
  let current = 0;
  const btnFin = document.getElementById('btnFinalizado');

  function actualizarBotones() {
    const esUltimo  = current === slides.length - 1;
    const esPrimero = current === 0;
    // Botón siguiente: deshabilitado en el último
    ['btnSiguiente', 'btnSiguiente2'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.disabled = esUltimo;
    });
    // Botón anterior: deshabilitado en el primero
    ['btnAnterior', 'btnAnterior2'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.disabled = esPrimero;
    });
    // Mostrar Finalizado solo en el último
    if (btnFin) btnFin.style.display = esUltimo ? '' : 'none';
  }

  function mostrar(idx) {
    if (idx < 0 || idx >= slides.length) return;
    slides[current].classList.remove('activo');
    current = idx;
    slides[current].classList.add('activo');
    // <--- hecho por claude code: el contador ahora es un campo escribible
    ['mSalto', 'mSalto2'].forEach(function (id) {
      const el = document.getElementById(id);
      if (el && document.activeElement !== el) el.value = current + 1;
    });
    actualizarBotones();
    window.scrollTo({ top: document.getElementById('carrusel-wrap').offsetTop - 80, behavior: 'smooth' });
  }

  document.getElementById('btnAnterior')?.addEventListener('click', () => mostrar(current - 1));
  document.getElementById('btnSiguiente')?.addEventListener('click', () => mostrar(current + 1));
  document.getElementById('btnAnterior2')?.addEventListener('click', () => mostrar(current - 1));
  document.getElementById('btnSiguiente2')?.addEventListener('click', () => mostrar(current + 1));

  // <--- hecho por claude code: escribir el número y Enter salta a ese alumno
  ['mSalto', 'mSalto2'].forEach(function (id) {
    const el = document.getElementById(id);
    if (!el) return;
    const ir = function () {
      let n = parseInt(el.value, 10);
      if (isNaN(n)) { el.value = current + 1; return; }
      n = Math.max(1, Math.min(n, slides.length));
      el.value = n;
      if (n - 1 !== current) mostrar(n - 1);
    };
    el.addEventListener('change', ir);
    el.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') { e.preventDefault(); ir(); el.blur(); }
    });
  });

  // <--- hecho por claude code: autoguardado del comentario al salir del campo
  document.addEventListener('focusin', function (e) {
    if (e.target.classList && e.target.classList.contains('comentario-txt')) {
      e.target.dataset.antes = e.target.value;
    }
  });
  document.addEventListener('focusout', function (e) {
    var ta = e.target;
    if (!ta.classList || !ta.classList.contains('comentario-txt')) return;
    if (ta.value === (ta.dataset.antes || '')) return;   // no cambió: no se escribe
    ta.dataset.antes = ta.value;
    var slide = ta.closest('.slide-alumno');
    if (slide) guardar(slide);
  });

  // ── Finalizar revisión ──
  const firstSlide = slides[0];
  btnFin?.addEventListener('click', async function () {
    btnFin.disabled = true;
    btnFin.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando…';
    try {
      const res = await fetch(URL_FIN, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area:    firstSlide.dataset.area,
          parcial: firstSlide.dataset.parcial,
          anio:    firstSlide.dataset.anio,
          grado:   window._PAGE.gradoSel,
          seccion: window._PAGE.seccionSel,
        }),
      });
      const d = await res.json();
      if (d.ok) {
        btnFin.classList.replace('btn-danger', 'btn-outline-success');
        btnFin.innerHTML = '<i class="ti ti-circle-check me-1"></i>¡Revisión enviada!';
        Swal.fire({
          icon: 'success',
          title: '¡Gracias!',
          text: 'Gracias por llenar los comentarios. El coordinador ha sido notificado.',
          confirmButtonText: 'Aceptar',
          confirmButtonColor: '#2fb344',
        }).then(() => { window.location.href = window._PAGE.urlMaestro; });
      } else {
        btnFin.innerHTML = '<i class="ti ti-circle-check me-1"></i>Finalizado';
        btnFin.disabled = false;
      }
    } catch (e) {
      btnFin.innerHTML = '<i class="ti ti-circle-check me-1"></i>Finalizado';
      btnFin.disabled = false;
    }
  });

  // Inicializar estado de botones
  actualizarBotones();
})();
