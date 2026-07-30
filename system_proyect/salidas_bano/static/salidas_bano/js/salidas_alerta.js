/* salidas_alerta.js — <--- hecho por claude code: aviso de regreso sin registrar.

   Se le pregunta al SERVIDOR quién sigue afuera (no al estado del navegador, así el
   aviso también desaparece si el regreso lo registró otro maestro). Si alguien lleva
   más de N minutos fuera, suena un aviso y se abre un modal para registrar el
   regreso ahí mismo.

   El chequeo es cada 3 s y además al volver a la pestaña, así el aviso aparece solo
   SIN recargar la página. */
(function () {
  var SB = window._SB || {};
  if (!SB.urlPendientes) return;

  var CADA_MS = 3000;           // cada cuánto se pregunta al servidor
  var modalEl = document.getElementById('modalPendientes');
  var tbody   = document.getElementById('pend-tbody');
  var intro   = document.getElementById('pend-intro');
  if (!modalEl || !tbody) return;

  var modal     = null;
  var pospuesto = false;
  var avisados  = {};           // id de salida -> ya sonó, para no repetir el sonido

  function esc(s) {
    return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function dosDig(n) { return String(n).padStart(2, '0'); }
  function horaActual() {
    var d = new Date();
    return dosDig(d.getHours()) + ':' + dosDig(d.getMinutes());
  }
  function duracion(min) {
    return min < 60 ? min + ' min' : Math.floor(min / 60) + ' h ' + (min % 60) + ' min';
  }

  // ── Sonido de aviso ───────────────────────────────────────────────────────
  // <--- hecho por claude code: hey.mp3 EN BUCLE hasta que el maestro atienda.
  // Se corta en cuanto toca el modal (ya lo vio) o cuando ya no queda nadie
  // pendiente. Si aparece OTRO alumno, vuelve a sonar.
  var audio = null;
  var audioListo = false;       // el navegador ya nos dejó reproducir

  function crearAudio() {
    if (audio) return audio;
    audio = new Audio(SB.sonidoAlerta);
    audio.loop = true;
    audio.preload = 'auto';
    return audio;
  }

  // <--- hecho por claude code: Chrome NO deja reproducir audio hasta que el usuario
  // haya interactuado con la página. Al primer clic/tecla se hace un play+pause MUDO
  // para quedar autorizados; si no, la alerta salía sin sonido y sin explicación.
  function desbloquear() {
    if (audioListo || !SB.sonidoAlerta) return;
    try {
      var a = crearAudio();
      var vol = a.volume;
      a.volume = 0;
      var p = a.play();
      if (p && p.then) {
        p.then(function () {
          a.pause(); a.currentTime = 0; a.volume = vol; audioListo = true;
        }).catch(function () { a.volume = vol; });
      } else {
        a.pause(); a.currentTime = 0; a.volume = vol; audioListo = true;
      }
    } catch (e) { }
  }
  ['click', 'keydown', 'touchstart'].forEach(function (ev) {
    document.addEventListener(ev, desbloquear, true);
  });

  function sonar() {
    if (!SB.sonidoAlerta) return;
    try {
      var a = crearAudio();
      a.currentTime = 0;
      var p = a.play();
      if (p && p.catch) {
        p.catch(function () {
          // Sigue bloqueado: se le ofrece al maestro activarlo con un clic.
          botonSonido();
        });
      }
    } catch (e) { botonSonido(); }
  }

  function callar() {
    if (!audio) return;
    try { audio.pause(); audio.currentTime = 0; } catch (e) { }
  }

  // Botón visible cuando el navegador bloquea el sonido (en vez de fallar callado)
  function botonSonido() {
    var el = document.getElementById('pend-msg');
    if (!el || el.querySelector('#pend-activar')) return;
    el.innerHTML = '<div class="alert alert-warning py-2 mb-2 d-flex align-items-center">' +
      '<span class="me-auto"><i class="ti ti-volume-off me-1"></i>' +
      'El navegador bloqueó el sonido de esta pestaña.</span>' +
      '<button type="button" class="btn btn-sm btn-warning" id="pend-activar">' +
      '<i class="ti ti-volume me-1"></i>Activar sonido</button></div>';
    el.querySelector('#pend-activar').addEventListener('click', function () {
      audioListo = false;
      desbloquear();
      setTimeout(function () { el.innerHTML = ''; sonar(); }, 150);
    });
  }

  function aviso(msg, tipo) {
    var el = document.getElementById('pend-msg');
    if (!el) return;
    // No pisar el botón de "Activar sonido" si está puesto
    if (el.querySelector('#pend-activar') && !msg) return;
    if (!msg) { el.innerHTML = ''; return; }
    el.innerHTML = '<div class="alert alert-' + (tipo || 'danger') + ' py-2 mb-2">' + esc(msg) + '</div>';
  }

  function pintar(items) {
    intro.textContent = items.length === 1
      ? 'Este alumno salió y todavía no se registra su regreso:'
      : 'Estos ' + items.length + ' alumnos salieron y todavía no se registra su regreso:';

    tbody.innerHTML = items.map(function (p) {
      return '<tr data-salida="' + p.id + '" data-iid="' + p.ingr_egr_id + '">' +
        '<td><div class="fw-medium">' + esc(p.alumno) + '</div>' +
          '<div class="text-muted small">' + esc(p.grado) + ' ' + esc(p.grupo) +
          (p.clase ? ' · ' + esc(p.clase) : '') + '</div></td>' +
        '<td class="text-center font-monospace">' + esc(p.hora_salida) + '</td>' +
        '<td class="text-center"><span class="badge bg-danger">' + duracion(p.minutos) + '</span></td>' +
        '<td><div class="input-group input-group-sm">' +
          '<input type="time" class="form-control pend-hora" value="' + horaActual() + '">' +
          '<button class="btn btn-success pend-guardar" type="button" title="Registrar regreso">' +
            '<i class="ti ti-check"></i></button>' +
        '</div></td>' +
        '</tr>';
    }).join('');
  }

  function mostrar(items) {
    pintar(items);
    if (!modal) modal = bootstrap.Modal.getOrCreateInstance(modalEl);
    if (!modalEl.classList.contains('show')) modal.show();
    // Suena solo por alumno nuevo, para no repetir el pitido cada 10 s.
    var nuevos = items.filter(function (p) { return !avisados[p.id]; });
    if (nuevos.length) { nuevos.forEach(function (p) { avisados[p.id] = true; }); sonar(); }
  }

  function ocultar() {
    callar();
    if (modal && modalEl.classList.contains('show')) modal.hide();
  }

  // Tocar el modal = el maestro ya lo vio: se calla, pero el aviso sigue en pantalla.
  // Se excluye el botón de "Activar sonido", que justamente sirve para lo contrario.
  function callarSiTocan(e) {
    if (e.target.closest && e.target.closest('#pend-activar')) return;
    callar();
  }
  modalEl.addEventListener('mousedown', callarSiTocan);
  modalEl.addEventListener('keydown', callarSiTocan);
  modalEl.addEventListener('touchstart', callarSiTocan);

  function revisar() {
    fetch(SB.urlPendientes + '?area=' + encodeURIComponent(SB.area || ''),
          { credentials: 'same-origin' })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (!d.ok) return;
        var limite = d.minutos_alerta || 5;
        var abiertos = (d.pendientes || []).filter(function (p) { return p.minutos >= limite; });

        // Los que ya regresaron dejan de contar para el sonido
        var vivos = {};
        abiertos.forEach(function (p) { vivos[p.id] = true; });
        Object.keys(avisados).forEach(function (id) { if (!vivos[id]) delete avisados[id]; });

        if (!abiertos.length) { pospuesto = false; callar(); ocultar(); return; }
        if (modalEl.classList.contains('show')) { pintar(abiertos); return; }
        if (pospuesto) { pospuesto = false; return; }   // se salta UNA vuelta
        mostrar(abiertos);
      })
      .catch(function () { /* sin conexión: se reintenta en la siguiente vuelta */ });
  }

  // ── Registrar el regreso desde el modal ───────────────────────────────────
  // <--- hecho por claude code: delegado en document (no en el tbody) para que siga
  // funcionando pase lo que pase con el repintado de la tabla.
  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.pend-guardar') : null;
    if (!btn) return;
    e.preventDefault();

    var tr = btn.closest('tr');
    if (!tr || !tr.dataset.salida) { aviso('No se pudo identificar la salida.'); return; }
    var campo = tr.querySelector('.pend-hora');
    var hora  = (campo && campo.value.trim()) || horaActual();
    var iid   = tr.dataset.iid;

    aviso('');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    fetch(SB.urlRegresoBase.replace('{pk}', tr.dataset.salida), {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': SB.csrfToken },
      body: JSON.stringify({ hora_regreso: hora }),
    })
      .then(function (r) {
        return r.text().then(function (txt) {
          var d;
          try { d = JSON.parse(txt); }
          catch (err) { throw new Error('El servidor respondió ' + r.status); }
          if (!r.ok || !d.ok) throw new Error(d.error || ('Error ' + r.status));
          return d;
        });
      })
      .then(function (d) {
        delete avisados[tr.dataset.salida];
        tr.remove();

        // Refleja el regreso en la tabla de la pantalla, sin recargar
        var sal = (SB.salidasHoy || {})[String(iid)];
        if (sal) { sal.last_hora_regreso = hora; sal.abierta = false; }
        var filaEl = document.querySelector('tr.fila-alumno[data-iid="' + iid + '"]');
        if (filaEl && typeof window.sbRebuildFila === 'function') window.sbRebuildFila(filaEl);

        if (!tbody.querySelector('tr')) ocultar();
        revisar();
      })
      .catch(function (err) {
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-check"></i>';
        aviso('No se pudo registrar el regreso: ' + err.message);
      });
  });

  var btnDespues = document.getElementById('pend-despues');
  if (btnDespues) btnDespues.addEventListener('click', function () {
    pospuesto = true;
    ocultar();
  });

  // Chequeo periódico + al volver a la pestaña (para que no dependa de recargar)
  revisar();
  setInterval(revisar, CADA_MS);
  document.addEventListener('visibilitychange', function () {
    if (!document.hidden) revisar();
  });
})();
