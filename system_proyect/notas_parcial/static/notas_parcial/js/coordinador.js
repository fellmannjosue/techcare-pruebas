/* notas_parcial/coordinador.js
   Bridge vars injected via window._PAGE from coordinador.html:
     csrf, urlSave, urlAsig, urlLeer, urlEmail,
     area, parcial, anio, curso, grado, seccion,
     soloCarrusel, anioActual
*/
(function () {
  const URL_SAVE  = window._PAGE.urlSave;
  const URL_ASIG  = window._PAGE.urlAsig;
  const URL_LEER  = window._PAGE.urlLeer;
  const URL_EMAIL = window._PAGE.urlEmail;
  const CSRF      = window._PAGE.csrf;

  // ── Marcar notificación como leída ──
  async function leerNotif(pk) {
    try {
      await fetch(URL_LEER, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({ pk }),
      });
    } catch (e) {}
  }

  document.querySelectorAll('.btn-leer-notif').forEach(btn => {
    btn.addEventListener('click', async function () {
      btn.disabled = true;
      await leerNotif(btn.dataset.pk);
      document.getElementById(`notif-${btn.dataset.pk}`)?.remove();
    });
  });

  // ── Ver revisión: marcar como leída y navegar ──
  document.querySelectorAll('.btn-ver-notif').forEach(a => {
    a.addEventListener('click', function () {
      leerNotif(a.dataset.pk); // fire-and-forget, navegación ocurre de inmediato
    });
  });

  // Auto-submit on dropdown change (resets grade/section state)
  document.getElementById('selParcial')?.addEventListener('change', function () {
    const v = parseInt(this.value);
    if (v >= 3 || v === 1) return; // leave it to the modal
    document.getElementById('frmFiltro').submit();
  });
  document.getElementById('selArea')?.addEventListener('change', () =>
    document.getElementById('frmFiltro').submit()
  );
  document.getElementById('inpAnio')?.addEventListener('change', function () {
    if (parseInt(this.value) < window._PAGE.anioActual) return; // modal handles it
    document.getElementById('frmFiltro').submit();
  });

  // ── Guardar comentario ──
  async function guardar(tr) {
    const btn = tr.querySelector('.btn-guardar-uno');
    const msg = tr.querySelector('.estado-msg');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
      const res = await fetch(URL_SAVE, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ingr_egr_id: tr.dataset.iid,
          parcial:     tr.dataset.parcial,
          anio:        tr.dataset.anio,
          area:        tr.dataset.area,
          comentario:  tr.querySelector('.comentario-txt').value,
        }),
      });
      const d = await res.json();
      if (d.ok) {
        btn.classList.replace('btn-outline-success', 'btn-success');
        btn.innerHTML = '<i class="ti ti-circle-check"></i>';
        btn.disabled = true;
        msg.className = 'estado-msg'; msg.textContent = '';
      } else {
        msg.className = 'estado-msg saved-err'; msg.textContent = '✗';
        setTimeout(() => { msg.textContent = ''; }, 3000);
        btn.disabled = false;
      }
    } catch (e) {
      msg.className = 'estado-msg saved-err'; msg.textContent = '✗';
      setTimeout(() => { msg.textContent = ''; }, 3000);
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-check"></i>';
    }
  }

  // ── Asignar maestro ──
  document.querySelectorAll('.btn-asignar').forEach(btn => {
    btn.addEventListener('click', async function () {
      const banner    = btn.closest('.asig-banner');
      const grado     = banner.dataset.grado;
      const seccion   = banner.dataset.seccion;
      const maestroId = banner.querySelector('.sel-maestro').value;
      const msgEl     = banner.querySelector('.asig-msg');
      const nombreEl  = banner.querySelector('.maestro-nombre');
      btn.disabled = true;
      try {
        const res = await fetch(URL_ASIG, {
          method: 'POST',
          headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
          body: JSON.stringify({
            maestro_id: maestroId || null,
            area:    window._PAGE.area,
            parcial: window._PAGE.parcial,
            anio:    window._PAGE.anio,
            grado, seccion,
          }),
        });
        const d = await res.json();
        if (d.ok) {
          nombreEl.textContent = d.nombre || '—';
          msgEl.className = 'asig-msg saved-ok'; msgEl.textContent = '✓ Guardado';
          setTimeout(() => { msgEl.textContent = ''; }, 3000);
        } else {
          msgEl.className = 'asig-msg saved-err'; msgEl.textContent = 'Error';
        }
      } catch (e) {
        msgEl.className = 'asig-msg saved-err'; msgEl.textContent = 'Error';
      }
      btn.disabled = false;
    });
  });

  function activarEnvio() {
    ['btnEnviarCorreo', 'btnEnviarCorreo2'].forEach(id => {
      const el = document.getElementById(id);
      if (el) { el.style.pointerEvents = ''; el.style.opacity = '1'; el.disabled = false; }
    });
    ['txtRevisado', 'txtRevisado2'].forEach(id => {
      const el = document.getElementById(id);
      if (el) el.style.display = '';
    });
    ['btnRevisado', 'btnRevisado2'].forEach(id => {
      const el = document.getElementById(id);
      if (el) {
        el.disabled = true;
        el.classList.remove('btn-outline-success');
        el.classList.add('btn-success');
        el.innerHTML = '<i class="ti ti-circle-check me-1"></i>¡Revisado!';
        el.style.opacity = '1';
      }
    });
  }

  async function revisarTodo() {
    for (const tr of document.querySelectorAll('#lista-alumnos tr[data-iid]'))
      await guardar(tr);
    // Marcar cada fila como revisada visualmente
    document.querySelectorAll('#lista-alumnos .btn-guardar-uno').forEach(btn => {
      btn.classList.replace('btn-outline-success', 'btn-success');
      btn.innerHTML = '<i class="ti ti-circle-check"></i>';
      btn.disabled = true;
    });
    activarEnvio();
  }

  // ── Toggle Lista / Carrusel ──
  if (window._PAGE.soloCarrusel) {
    // coord_revision: solo carrusel, ocultar lista desde el inicio
    document.getElementById('lista-alumnos').style.display = 'none';
    document.getElementById('footerLista').style.display = 'none';
    document.getElementById('seccionCarrusel').style.display = '';
    document.getElementById('footerEnvio').style.display = '';
  }
  document.getElementById('btnVistaLista')?.addEventListener('click', function () {
    document.getElementById('lista-alumnos').style.display = '';
    document.getElementById('footerLista').style.display = '';
    document.getElementById('seccionCarrusel').style.display = 'none';
    document.getElementById('footerEnvio').style.display = 'none';
    this.classList.add('active');
    document.getElementById('btnVistaCarrusel')?.classList.remove('active');
  });
  document.getElementById('btnVistaCarrusel')?.addEventListener('click', function () {
    document.getElementById('lista-alumnos').style.display = 'none';
    document.getElementById('footerLista').style.display = 'none';
    document.getElementById('seccionCarrusel').style.display = '';
    document.getElementById('footerEnvio').style.display = '';
    this.classList.add('active');
    document.getElementById('btnVistaLista')?.classList.remove('active');
  });

  // ── Carrusel coordinador ──
  (function () {
    const slides = Array.from(document.querySelectorAll('.slide-coord'));
    if (!slides.length) return;
    let cur = 0;

    function actualizarCarrusel() {
      ['cBtnAnterior', 'cBtnAnterior2'].forEach(id => {
        const el = document.getElementById(id); if (el) el.disabled = cur === 0;
      });
      ['cBtnSiguiente', 'cBtnSiguiente2'].forEach(id => {
        const el = document.getElementById(id); if (el) el.disabled = cur === slides.length - 1;
      });
    }

    function cMostrar(idx) {
      if (idx < 0 || idx >= slides.length) return;
      slides[cur].classList.remove('activo');
      cur = idx;
      slides[cur].classList.add('activo');
      const txt = `${cur + 1} / ${slides.length}`;
      document.getElementById('cContador').textContent = txt;
      document.getElementById('cContador2').textContent = txt;
      actualizarCarrusel();
      const wrap = document.getElementById('cCarruselWrap');
      if (wrap) window.scrollTo({ top: wrap.offsetTop - 80, behavior: 'smooth' });
    }
    document.getElementById('cBtnAnterior')?.addEventListener('click', () => cMostrar(cur - 1));
    document.getElementById('cBtnSiguiente')?.addEventListener('click', () => cMostrar(cur + 1));
    document.getElementById('cBtnAnterior2')?.addEventListener('click', () => cMostrar(cur - 1));
    document.getElementById('cBtnSiguiente2')?.addEventListener('click', () => cMostrar(cur + 1));
    actualizarCarrusel();
  })();

  // ── Guardar comentario desde carrusel ──
  document.querySelectorAll('.btn-guardar-carrusel').forEach(btn => {
    btn.addEventListener('click', async function () {
      const slide = this.closest('.slide-coord');
      const msg   = slide.querySelector('.estado-msg-carrusel');
      const ta    = slide.querySelector('.comentario-txt-carrusel');
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
            comentario:  ta.value,
          }),
        });
        const d = await res.json();
        if (d.ok) {
          btn.classList.replace('btn-outline-success', 'btn-success');
          btn.innerHTML = '<i class="ti ti-circle-check me-1"></i>Guardado';
          msg.style.color = '#2fb344'; msg.textContent = '';
          setTimeout(() => {
            btn.classList.replace('btn-success', 'btn-outline-success');
            btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
            btn.disabled = false;
          }, 2000);
        } else {
          msg.style.color = '#d63939'; msg.textContent = '✗ Error';
          btn.disabled = false;
          btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
        }
      } catch (e) {
        msg.style.color = '#d63939'; msg.textContent = '✗ Error';
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-device-floppy me-1"></i>Guardar';
      }
    });
  });

  // ── Enviar PDF por correo ──
  document.getElementById('btnConfirmarEnvio')?.addEventListener('click', async function () {
    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando…';
    const msgEl = document.getElementById('envioMensaje');
    const destinatario = document.getElementById('selectDestinatario').value;
    try {
      const res = await fetch(URL_EMAIL, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          parcial:      window._PAGE.parcial,
          anio:         window._PAGE.anio,
          area:         window._PAGE.area,
          curso:        window._PAGE.curso,
          grado:        window._PAGE.grado,
          seccion:      window._PAGE.seccion,
          destinatario: destinatario,
        }),
      });
      const d = await res.json();
      msgEl.style.display = '';
      if (d.ok) {
        msgEl.innerHTML = `<div class="alert alert-success py-2"><i class="ti ti-circle-check me-2"></i>PDF enviado correctamente a <strong>${destinatario}</strong></div>`;
        btn.innerHTML = '<i class="ti ti-circle-check me-1"></i>¡Enviado!';
      } else {
        msgEl.innerHTML = `<div class="alert alert-danger py-2"><i class="ti ti-alert-circle me-2"></i>Error: ${d.error || 'No se pudo enviar'}</div>`;
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-send me-1"></i>Enviar PDF';
      }
    } catch (e) {
      msgEl.style.display = '';
      msgEl.innerHTML = '<div class="alert alert-danger py-2">Error de conexión.</div>';
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-send me-1"></i>Enviar PDF';
    }
  });

  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('.btn-guardar-uno').forEach(btn => {
      btn.addEventListener('click', () => guardar(btn.closest('tr')));
    });
    document.getElementById('btnRevisado')?.addEventListener('click', revisarTodo);
    document.getElementById('btnRevisado2')?.addEventListener('click', revisarTodo);
  });
})();
