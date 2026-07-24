/* <--- hecho por claude code: los valores de Django llegan por data-* en
   #coordinador-config (un .js no lo procesa Django). */
const CFG_COORDINADOR = (function(){
  var d = document.getElementById("coordinador-config").dataset;
  function j(x){ try { return JSON.parse(x); } catch(e){ return x; } }
  return { v0:d.v0, v1:d.v1, v2:d.v2, v3:d.v3, v4:d.v4, v5:d.v5,
           v6:d.v6, v7:d.v7, v8:d.v8, v9:d.v9, v10:d.v10, j11:j(d.v11), v12:d.v12 };
})();

window._PAGE = Object.assign(window._PAGE || {}, {
  csrf:         CFG_COORDINADOR.v0,
  urlSave:      CFG_COORDINADOR.v1,
  urlAsig:      CFG_COORDINADOR.v2,
  urlLeer:      CFG_COORDINADOR.v3,
  urlEmail:     CFG_COORDINADOR.v4,
  area:         CFG_COORDINADOR.v5,
  parcial:      CFG_COORDINADOR.v6,
  anio:         CFG_COORDINADOR.v7,
  curso:        CFG_COORDINADOR.v8,
  grado:        CFG_COORDINADOR.v9,
  seccion:      CFG_COORDINADOR.v10,
  soloCarrusel: CFG_COORDINADOR.j11 === true,
  urlRevisado:  CFG_COORDINADOR.v12,   // <--- hecho por claude code
  anioActual:   window._PAGE && window._PAGE.anioActual
                  ? window._PAGE.anioActual : new Date().getFullYear(),
});

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
    // <--- hecho por claude code: el rango lo define base_notas.js
    const max = (typeof PARCIAL_MAX !== 'undefined') ? PARCIAL_MAX : 3;
    const min = (typeof PARCIAL_MIN !== 'undefined') ? PARCIAL_MIN : 2;
    if (isNaN(v) || v > max || v < min) return; // lo atrapa el modal
    document.getElementById('frmFiltro').submit();
  });
  document.getElementById('selArea')?.addEventListener('change', () =>
    document.getElementById('frmFiltro').submit()
  );
  document.getElementById('inpAnio')?.addEventListener('change', function () {
    if (parseInt(this.value) < window._PAGE.anioActual) return; // modal handles it
    document.getElementById('frmFiltro').submit();
  });

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

  // ── Guardar comentario (por maestro/caja) ──
  async function guardar(box) {
    const tr  = box.closest('.alumno-card') || box.closest('[data-iid]');
    const ta  = box.querySelector('.comentario-txt');
    const btn = box.querySelector('.btn-guardar-uno');
    const msg = box.querySelector('.estado-msg');
    if (contarPalabras(ta.value) > 40) {
      msg.className = 'estado-msg small saved-err'; msg.textContent = 'Máx. 40 palabras';
      return;
    }
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
    try {
      const res = await fetch(URL_SAVE, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ingr_egr_id: tr.dataset.iid, parcial: tr.dataset.parcial,
          anio: tr.dataset.anio, area: tr.dataset.area,
          maestro_id: box.dataset.maestro,
          comentario: ta.value,
        }),
      });
      const d = await res.json();
      if (d.ok) {
        btn.classList.replace('btn-outline-success', 'btn-success');
        btn.innerHTML = '<i class="ti ti-circle-check"></i>';
        // <--- hecho por claude code: el check se queda marcado; antes volvía a gris
        btn.innerHTML = '<i class="ti ti-circle-check"></i>';
        msg.className = 'estado-msg small saved-ok'; msg.textContent = '✓';
        setTimeout(() => { msg.textContent = ''; btn.disabled = false; }, 2000);
      } else {
        msg.className = 'estado-msg small saved-err'; msg.textContent = d.error || '✗';
        btn.disabled = false; btn.innerHTML = '<i class="ti ti-check"></i>';
      }
    } catch (e) {
      msg.className = 'estado-msg small saved-err'; msg.textContent = '✗';
      btn.disabled = false; btn.innerHTML = '<i class="ti ti-check"></i>';
    }
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('.btn-guardar-uno');
    if (b) { const box = b.closest('.cmt-box'); if (box) guardar(box); }
  });

  // ── Asignar / quitar maestro (recarga para refrescar chips + cajas) ──
  // <--- hecho por claude code: `items` permite asignar el mismo maestro a varios
  // grado-sección de una sola vez (la vista ya lo soportaba, faltaba la UI).
  async function asignarAccion(banner, maestroId, accion, items) {
    const res = await fetch(URL_ASIG, {
      method: 'POST',
      headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        accion: accion, maestro_id: maestroId,
        area: window._PAGE.area, parcial: window._PAGE.parcial, anio: window._PAGE.anio,
        grado: banner.dataset.grado, seccion: banner.dataset.seccion,
        items: items || null,
      }),
    });
    const d = await res.json();
    return d.ok ? true : (d.error || 'Error');
  }

  // <--- hecho por claude code: grados marcados en el desplegable (el propio si no hay)
  function gradosElegidos(banner) {
    const chks = banner.querySelectorAll('.chk-grado:checked');
    if (!chks.length) return [{ grado: banner.dataset.grado, seccion: banner.dataset.seccion }];
    return Array.from(chks).map(c => ({ grado: c.dataset.grado, seccion: c.dataset.seccion }));
  }

  function refrescarContador(banner) {
    const n = banner.querySelectorAll('.chk-grado:checked').length;
    const lbl = banner.querySelector('.grados-n');
    if (lbl) lbl.textContent = n || 1;
  }

  document.querySelectorAll('.asig-banner').forEach(banner => {
    banner.querySelectorAll('.chk-grado').forEach(c =>
      c.addEventListener('change', () => refrescarContador(banner)));
    banner.querySelector('.btn-grados-todos')?.addEventListener('click', () => {
      banner.querySelectorAll('.chk-grado').forEach(c => { c.checked = true; });
      refrescarContador(banner);
    });
    banner.querySelector('.btn-grados-ninguno')?.addEventListener('click', () => {
      banner.querySelectorAll('.chk-grado').forEach(c => {
        c.checked = (c.dataset.grado === banner.dataset.grado &&
                     c.dataset.seccion === banner.dataset.seccion);
      });
      refrescarContador(banner);
    });
    refrescarContador(banner);
  });

  document.querySelectorAll('.btn-asignar').forEach(btn => {
    btn.addEventListener('click', async function () {
      const banner = btn.closest('.asig-banner');
      const sel = banner.querySelector('.sel-maestro');
      const msg = banner.querySelector('.asig-msg');
      const maestroId = sel.value;
      if (!maestroId) {
        msg.className = 'asig-msg ms-1 small text-danger';
        msg.textContent = 'Elige un maestro';
        setTimeout(() => { msg.textContent = ''; }, 3000);
        return;
      }
      btn.disabled = true;
      const r = await asignarAccion(banner, maestroId, 'add', gradosElegidos(banner));
      if (r === true) location.reload();
      else {
        btn.disabled = false;
        msg.className = 'asig-msg ms-1 small text-danger';
        msg.textContent = r;
      }
    });
  });
  document.addEventListener('click', async function (e) {
    var rm = e.target.closest && e.target.closest('.chip-remove');
    if (!rm) return;
    e.preventDefault();
    const chip = rm.closest('.chip-maestro');
    const banner = rm.closest('.asig-banner');
    // Quitar afecta SOLO a este grado-sección, no a los marcados en el desplegable
    if (await asignarAccion(banner, chip.dataset.maestro, 'remove') === true) location.reload();
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
    for (const box of document.querySelectorAll('#lista-alumnos .cmt-box'))
      await guardar(box);
    // <--- hecho por claude code: persistir el "Revisado" para que siga marcado al volver
    try {
      await fetch(window._PAGE.urlRevisado, {
        method: 'POST',
        headers: { 'X-CSRFToken': CSRF, 'Content-Type': 'application/json' },
        body: JSON.stringify({
          area: window._PAGE.area, parcial: window._PAGE.parcial, anio: window._PAGE.anio,
          grado: window._PAGE.grado, seccion: window._PAGE.seccion,
        }),
      });
    } catch (e) {}
    // Marcar cada caja como revisada visualmente
    document.querySelectorAll('#lista-alumnos .btn-guardar-uno').forEach(btn => {
      btn.classList.replace('btn-outline-success', 'btn-success');
      btn.innerHTML = '<i class="ti ti-circle-check"></i>';
      btn.disabled = true;
    });
    activarEnvio();
  }

  // <--- hecho por claude code: la página ya venía marcada como revisada
  if (document.getElementById('btnRevisado')?.disabled) activarEnvio();

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

  // (El guardado del carrusel ahora usa las cajas .cmt-box con guardado delegado.)

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
    // El guardado por caja se maneja con delegación de eventos (ver arriba).
    document.getElementById('btnRevisado')?.addEventListener('click', revisarTodo);
    document.getElementById('btnRevisado2')?.addEventListener('click', revisarTodo);
  });
})();
