/* notas_parcial/maestro.js
   Bridge vars injected via window._PAGE from maestro.html:
     csrf, urlSave, urlFin, gradoSel, seccionSel, urlMaestro
*/
(function () {
  const URL_SAVE = window._PAGE.urlSave;
  const URL_FIN  = window._PAGE.urlFin;
  const CSRF     = window._PAGE.csrf;

  // ── Guardar comentario ── (queda bloqueado tras guardar exitosamente)
  async function guardar(slide) {
    const btn = slide.querySelector('.btn-guardar-uno');
    const msg = slide.querySelector('.estado-msg');
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
          comentario:  slide.querySelector('.comentario-txt').value,
        }),
      });
      const d = await res.json();
      if (d.ok) {
        msg.className   = 'estado-msg saved-ok';
        msg.textContent = '✓ Guardado';
        // Mantener bloqueado y cambiar apariencia
        btn.innerHTML = '<i class="ti ti-circle-check me-1"></i>Guardado';
        btn.classList.replace('btn-success', 'btn-outline-success');
        // btn.disabled permanece true
      } else {
        msg.className   = 'estado-msg saved-err';
        msg.textContent = '✗ Error al guardar';
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
    const txt = `${current + 1} / ${slides.length}`;
    document.getElementById('contadorSlide').textContent  = txt;
    document.getElementById('contadorSlide2').textContent = txt;
    actualizarBotones();
    window.scrollTo({ top: document.getElementById('carrusel-wrap').offsetTop - 80, behavior: 'smooth' });
  }

  document.getElementById('btnAnterior')?.addEventListener('click', () => mostrar(current - 1));
  document.getElementById('btnSiguiente')?.addEventListener('click', () => mostrar(current + 1));
  document.getElementById('btnAnterior2')?.addEventListener('click', () => mostrar(current - 1));
  document.getElementById('btnSiguiente2')?.addEventListener('click', () => mostrar(current + 1));

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
