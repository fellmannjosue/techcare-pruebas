// <--- hecho por claude code: Sistema Salidas Baño — JS v9 (regreso activo + limpiar form entre maestros)
(function () {
  'use strict';

  const SB = window._SB || {};

  // ── Semáforo config ─────────────────────────────────────────────────────────
  const SEM = {
    verde:    { label: 'Verde',    cls: 'verde',    icon: '🟢' },
    amarillo: { label: 'Amarillo', cls: 'amarillo', icon: '🟡' },
    rojo:     { label: 'Rojo',     cls: 'rojo',     icon: '🔴' },
    negro:    { label: 'Negro',    cls: 'negro',     icon: '⚫' },
  };

  // Orden automático: índice = nº de salidas ya registradas → color asignado
  const SEMAFORO_AUTO = ['verde', 'amarillo', 'rojo', 'negro'];

  // ── Clases por grado (todos los maestros del área) ──────────────────────────
  const clasesPorGrado = SB.clasesPorGrado || {};

  // ── Salidas de hoy: key = str(ingr_egr_id) ─────────────────────────────────
  const salidasHoy = SB.salidasHoy || {};

  // ── Estado filtro de grupo por tabla ───────────────────────────────────────
  const grupoActivo = {};

  // ── ¿El usuario actual es coordinador? ─────────────────────────────────────
  const esCoord = !!SB.esCoord;

  // ══════════════════════════════════════════════════════════════════════════════
  // Builders de UI
  // ══════════════════════════════════════════════════════════════════════════════

  /**
   * Badge de estado actual + indicador del próximo color.
   * count = número de salidas YA registradas hoy.
   */
  function buildSemInfo(count, bloqueado, abierta) {
    // <--- hecho por claude code: el color del semáforo se aplica al REGRESAR.
    // Mientras el alumno está afuera se muestra "Afuera" (neutro), no el color.
    if (abierta) {
      const semPend = SEMAFORO_AUTO[Math.min(Math.max(count, 1) - 1, 3)];
      const pc = SEM[semPend];
      return `<span class="badge-sem" style="background:var(--ps-surface-2,#eef2ff);color:var(--ps-marca,#4f46e5);border:1px solid var(--ps-border,#dbe2ff);font-weight:700;">🚪 Afuera</span>`
           + `<div class="sem-next-lbl ${semPend} mt-1" title="Al regresar quedará ${pc.label}">→ ${pc.icon} ${pc.label} al volver</div>`;
    }
    if (count === 0) {
      return `<span class="sem-next-lbl verde" title="Primera salida será Verde">Primera: 🟢</span>`;
    }

    const semActual = SEMAFORO_AUTO[Math.min(count - 1, 3)];
    const actCfg    = SEM[semActual];
    let html = `<span class="badge-sem ${semActual}">${actCfg.icon} ${count}×</span>`;

    if (bloqueado) {
      html += `<div class="text-danger mt-1" style="font-size:.7rem;font-weight:700;">🔒 Bloqueado</div>`;
    } else if (count < 4) {
      const semSig = SEMAFORO_AUTO[Math.min(count, 3)];
      const sigCfg = SEM[semSig];
      html += `<div class="sem-next-lbl ${semSig} mt-1" title="La próxima salida será ${sigCfg.label}">→ ${sigCfg.icon} ${sigCfg.label}</div>`;
    }
    return html;
  }

  /** Select de clase con "Maestro — Clase" — siempre <select>, todas las clases como fallback */
  function buildClaseSelect(grado, valActual) {
    const gradoExacto = clasesPorGrado[grado] || [];
    const todasClases = Object.values(clasesPorGrado).flat();
    const fuente = gradoExacto.length ? gradoExacto : todasClases;
    // <--- hecho por claude code: quitar maestros/clases duplicados (misma etiqueta)
    const vistos = new Set();
    const clases = [];
    fuente.forEach(c => {
      const k = (c.label || c.value || '').trim();
      if (k && !vistos.has(k)) { vistos.add(k); clases.push(c); }
    });

    let opts = clases.map(c =>
      `<option value="${escHtml(c.value)}" ${c.value === valActual ? 'selected' : ''}>${escHtml(c.label)}</option>`
    ).join('');
    if (valActual && !clases.find(c => c.value === valActual)) {
      opts = `<option value="${escHtml(valActual)}" selected>${escHtml(valActual)}</option>` + opts;
    }
    return `<select class="form-select form-select-sm clase-input" style="min-width:180px;">
              <option value="">— Clase / Maestro —</option>${opts}</select>`;
  }

  /** Botones de sección (grupo) */
  function buildGrupoButtons(grupos, tablaId) {
    if (grupos.length <= 1) return '';
    const all  = `<button class="btn btn-sm btn-outline-secondary active" data-tabla="${tablaId}" data-grupo="">Todas</button>`;
    const btns = grupos.map(g =>
      `<button class="btn btn-sm btn-outline-teal" data-tabla="${tablaId}" data-grupo="${g}">${g.toUpperCase()}</button>`
    ).join('');
    return `<span class="text-muted small fw-semibold me-1">Sección:</span>
            <div class="btn-group btn-group-sm">${all}${btns}</div>`;
  }

  /** Busca la salida de hoy para este alumno */
  function getSalidaExistente(ingr_egr_id) {
    return salidasHoy[String(ingr_egr_id)] || null;
  }

  /** Construye la fila completa de un alumno */
  function buildFila(alumno, grado) {
    const uid = alumno.ingr_egr_id;
    const sal = getSalidaExistente(uid);

    const count       = sal ? sal.count              : 0;
    const lastClase   = sal ? sal.last_clase          : '';
    const hrSalida    = sal ? sal.last_hora_salida    : '';
    const hrRegreso   = sal ? sal.last_hora_regreso   : '';
    const lastMaestro = sal ? sal.last_maestro        : '';
    const salidaId    = sal ? sal.last_id             : '';

    // <--- hecho por claude code: "abierta" = alumno actualmente AFUERA
    // (última salida con hora de salida y SIN regreso). El semáforo se colorea
    // al registrar el regreso, no al salir. Sin botón: todo es autoguardado.
    const abierta = !!(sal && (sal.abierta === true ||
                       (sal.abierta === undefined && hrSalida && !hrRegreso)));

    // ¿Bloqueado para maestros regulares? (count ≥ 3 y no coordinador, y no afuera)
    const bloqueado = count >= 3 && !esCoord && !abierta;
    const rowClass  = bloqueado ? 'fila-alumno fila-bloqueada'
                    : abierta   ? 'fila-alumno fila-afuera'
                    : 'fila-alumno';

    // Botón eliminar (solo coordinadores, solo cuando hay salida registrada hoy)
    const elimBtn = (esCoord && salidaId)
      ? `<button class="btn btn-sm btn-outline-danger btn-eliminar-salida"
               data-pk="${salidaId}"
               data-nombre="${escHtml(alumno.nombre)}"
               title="Eliminar última salida">
           <i class="ti ti-trash"></i>
         </button>`
      : '';

    // ── Campos del formulario, según estado ──────────────────────────────────
    let claseHtml, fechaHtml, hsSalidaHtml, hrRegresoHtml, comentHtml;

    if (bloqueado) {
      // Estático con datos de la última salida
      claseHtml     = `<span class="text-muted small">${escHtml(lastClase) || '—'}</span>`;
      fechaHtml     = `<span class="text-muted small">${SB.fechaHoy}</span>`;
      hsSalidaHtml  = `<span class="text-muted small">${escHtml(hrSalida) || '—'}</span>`;
      hrRegresoHtml = `<span class="text-muted small">${escHtml(hrRegreso) || '—'}</span>`;
      comentHtml    = `<span class="text-muted small">${escHtml(sal ? sal.last_comentario : '') || '—'}</span>`;
    } else if (abierta) {
      // Alumno AFUERA: clase y hora de salida en solo-lectura; regreso habilitado
      claseHtml     = `<span class="small fw-semibold">${escHtml(lastClase) || '—'}</span>`;
      fechaHtml     = `<span class="text-muted small">${SB.fechaHoy}</span>`;
      hsSalidaHtml  = `<span class="small">${escHtml(hrSalida) || '—'}</span>`;
      hrRegresoHtml = `<input type="time" class="form-control form-control-sm hora-regreso text-center"
               value="" style="min-width:80px;border-color:var(--ps-marca,#6366f1);box-shadow:0 0 0 .12rem rgba(99,102,241,.18);"
               title="Registra la hora de regreso">`;
      comentHtml    = `<input type="text" class="form-control form-control-sm comentario-input"
               value="${escHtml(sal ? sal.last_comentario : '')}" placeholder="Observación…">`;
    } else {
      // Estado LISTO: editable, vacío para empezar limpio. La salida se autoguarda
      // en cuanto haya clase + hora. El regreso queda deshabilitado hasta salir.
      claseHtml     = buildClaseSelect(grado, '');
      fechaHtml     = `<input type="date" class="form-control form-control-sm fecha-input text-center"
               value="${SB.fechaHoy}" style="min-width:120px;">`;
      hsSalidaHtml  = `<input type="time" class="form-control form-control-sm hora-salida text-center"
               value="" style="min-width:80px;">`;
      // <--- hecho por claude code: en estado "listo" el regreso NO se puede usar
      // (el alumno aún no ha salido) → guion muted, no un input que parece editable.
      hrRegresoHtml = `<span class="text-muted small" title="Se habilita cuando el alumno registra su salida">—</span>`;
      comentHtml    = `<input type="text" class="form-control form-control-sm comentario-input"
               value="" placeholder="Observación…">`;
    }

    // ── Info de última salida (solo lectura) bajo el nombre ──────────────────
    let infoUltima = '';
    if (lastMaestro && count > 0) {
      infoUltima = `<div class="text-muted maestro-display" style="font-size:.7rem;">
        <i class="ti ti-user me-1"></i>${escHtml(lastMaestro)}`;
      if (hrSalida) {
        infoUltima += ` <span class="ms-1 text-muted">· ${escHtml(hrSalida)}</span>`;
      }
      infoUltima += `</div>`;
    }

    return `
    <tr class="${rowClass}"
        data-iid="${uid}"
        data-nombre="${escHtml(alumno.nombre)}"
        data-grado="${escHtml(alumno.grado)}"
        data-grupo="${escHtml(alumno.grupo)}"
        data-salida-id="${salidaId}"
        data-count="${count}"
        data-abierta="${abierta ? '1' : ''}">
      <td>
        <div class="fw-semibold">${escHtml(alumno.nombre)}</div>
        <div class="text-muted small">Grupo <strong>${alumno.grupo.toUpperCase()}</strong></div>
        ${infoUltima}
      </td>
      <td class="text-center">
        ${buildSemInfo(count, bloqueado, abierta)}
      </td>
      <td>${claseHtml}</td>
      <td class="text-center">${fechaHtml}</td>
      <td class="text-center">${hsSalidaHtml}</td>
      <td class="text-center">${hrRegresoHtml}</td>
      <td>${comentHtml}</td>
      <td class="text-center">
        <div class="btn-group btn-group-sm">
          <button class="btn btn-sm btn-outline-secondary btn-historial"
                  data-iid="${uid}" data-nombre="${escHtml(alumno.nombre)}"
                  title="Historial">
            <i class="ti ti-history"></i>
          </button>
          ${elimBtn}
        </div>
      </td>
    </tr>`;
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Poblar tablas + filtros de grupo
  // ══════════════════════════════════════════════════════════════════════════════

  function poblarTablas() {
    const datos = SB.alumnosPorGrado || {};

    document.querySelectorAll('.tabla-alumnos').forEach(tabla => {
      const grado    = tabla.dataset.grado;
      const tablaId  = tabla.id;
      const gruposId = tabla.dataset.gruposId;
      const alumnos  = datos[grado] || [];
      const tbody    = tabla.querySelector('tbody');

      tbody.innerHTML = alumnos.map(a => buildFila(a, grado)).join('');

      const grupos = [...new Set(alumnos.map(a => a.grupo))].sort();
      grupoActivo[tablaId] = '';
      const gruposEl = document.getElementById(gruposId);
      if (gruposEl) {
        gruposEl.innerHTML = buildGrupoButtons(grupos, tablaId);
        if (grupos.length <= 1) gruposEl.style.display = 'none';
      }
    });
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Filtro por sección
  // ══════════════════════════════════════════════════════════════════════════════

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('[data-tabla][data-grupo]');
    if (!btn) return;
    const tablaId = btn.dataset.tabla;
    const grupo   = btn.dataset.grupo;
    grupoActivo[tablaId] = grupo;

    const container = btn.closest('.btn-group');
    if (container) {
      container.querySelectorAll('button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
    }

    const tabla = document.getElementById(tablaId);
    if (!tabla) return;
    tabla.querySelectorAll('tr.fila-alumno').forEach(fila => {
      fila.style.display = (!grupo || fila.dataset.grupo === grupo) ? '' : 'none';
    });
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // Reconstruir una fila desde el estado local (salidasHoy) conservando el filtro
  // ══════════════════════════════════════════════════════════════════════════════

  function rebuildFila(fila) {
    const iid    = fila.dataset.iid;
    const grado  = fila.dataset.grado;
    const alumno = {
      ingr_egr_id: parseInt(iid),
      nombre:      fila.dataset.nombre,
      grado:       grado,
      grupo:       fila.dataset.grupo,
    };
    const tmp = document.createElement('tbody');
    tmp.innerHTML = buildFila(alumno, grado);
    const filaEl  = tmp.firstElementChild;
    const tabla   = fila.closest('table');
    const tablaId = tabla ? tabla.id : '';
    const grpAct  = grupoActivo[tablaId] || '';
    if (grpAct && filaEl.dataset.grupo !== grpAct) filaEl.style.display = 'none';
    fila.replaceWith(filaEl);
    return filaEl;
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Autoguardado de la SALIDA — <--- hecho por claude code: sin botón.
  // Se guarda automáticamente al tener clase + hora de salida. El semáforo NO se
  // colorea aquí; el alumno queda "Afuera" hasta que se registre su regreso.
  // ══════════════════════════════════════════════════════════════════════════════

  function autoGuardarSalida(fila) {
    if (!fila || fila.dataset.saving === '1') return;
    if (fila.classList.contains('fila-bloqueada') || fila.classList.contains('fila-afuera')) return;
    const sal0 = salidasHoy[fila.dataset.iid];
    if (sal0 && sal0.abierta) return;   // ya está afuera: primero el regreso

    const claseEl = fila.querySelector('.clase-input');
    const hsEl    = fila.querySelector('.hora-salida');
    const cmtEl   = fila.querySelector('.comentario-input');
    if (!claseEl || !hsEl) return;

    const clase       = claseEl.value.trim();
    const hora_salida = hsEl.value.trim();
    const comentario  = cmtEl ? cmtEl.value.trim() : '';
    if (!clase || !hora_salida) return;              // esperar a que estén ambos
    if (!SB.periodoId) { showToast('No hay período activo configurado.', 'danger'); return; }

    fila.dataset.saving = '1';

    fetch(SB.urlGuardar, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': SB.csrfToken },
      body: JSON.stringify({
        periodo_id:   SB.periodoId,
        ingr_egr_id:  fila.dataset.iid,
        alumno:       fila.dataset.nombre,
        grado:        fila.dataset.grado,
        grupo:        fila.dataset.grupo,
        area:         SB.area,
        clase:        clase,
        hora_salida:  hora_salida,
        hora_regreso: '',
        comentario:   comentario,
      }),
    })
    .then(r => r.json())
    .then(d => {
      fila.dataset.saving = '';
      if (!d.ok) { showToast(d.error || 'Error al guardar la salida.', 'danger'); return; }

      // El alumno queda AFUERA; el color se aplicará al registrar el regreso.
      salidasHoy[fila.dataset.iid] = {
        count:             d.count,
        semaforo:          d.semaforo,
        last_id:           d.id,
        last_clase:        clase,
        last_maestro:      d.maestro,
        last_hora_salida:  d.hora_salida,
        last_hora_regreso: '',
        last_comentario:   comentario,
        abierta:           true,
      };
      const filaEl = rebuildFila(fila);
      showToast(`🚪 ${filaEl.dataset.nombre} salió — registrado. Marca el regreso al volver.`, 'info');
      const hrEl = filaEl.querySelector('.hora-regreso');
      if (hrEl) hrEl.focus();
    })
    .catch(() => { fila.dataset.saving = ''; showToast('Error de conexión.', 'danger'); });
  }

  // Disparadores del autoguardado de la salida: elegir clase o poner la hora.
  document.addEventListener('change', function (e) {
    if (e.target.classList.contains('hora-salida') ||
        e.target.classList.contains('clase-input')) {
      autoGuardarSalida(e.target.closest('tr.fila-alumno'));
    }
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // Eliminar salida (coordinador) — con confirmación
  // ══════════════════════════════════════════════════════════════════════════════

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-eliminar-salida');
    if (!btn) return;

    const pk     = btn.dataset.pk;
    const nombre = btn.dataset.nombre;

    if (!confirm(`¿Eliminar la última salida registrada de ${nombre}?\n\nEsto restará un nivel al semáforo.`)) return;

    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';

    const url = SB.urlEliminarBase.replace('{pk}', pk);
    fetch(url, {
      method:  'POST',
      headers: { 'X-CSRFToken': SB.csrfToken },
    })
    .then(r => r.json())
    .then(d => {
      if (!d.ok) {
        btn.disabled = false;
        btn.innerHTML = '<i class="ti ti-trash"></i>';
        showToast(d.error || 'Error al eliminar.', 'danger');
        return;
      }

      const fila     = btn.closest('tr.fila-alumno');
      const iid      = fila.dataset.iid;
      const newCount = d.count;

      // Actualizar estado local
      if (newCount === 0) {
        delete salidasHoy[iid];
      } else {
        salidasHoy[iid] = {
          count:             newCount,
          semaforo:          d.semaforo,
          last_id:           d.last_id,
          last_clase:        d.last_clase,
          last_maestro:      d.last_maestro,
          last_hora_salida:  d.last_hora_salida,
          last_hora_regreso: d.last_hora_regreso || '',
          last_comentario:   d.last_comentario   || '',
        };
      }

      // Reconstruir fila completa
      const grado   = fila.dataset.grado;
      const grupo   = fila.dataset.grupo;
      const alumno  = {
        ingr_egr_id: parseInt(iid),
        nombre:      fila.dataset.nombre,
        grado:       grado,
        grupo:       grupo,
      };
      const nuevaFila = document.createElement('tbody');
      nuevaFila.innerHTML = buildFila(alumno, grado);
      const filaEl = nuevaFila.firstElementChild;

      // Mantener visibilidad del grupo activo
      const tabla   = fila.closest('table');
      const tablaId = tabla ? tabla.id : '';
      const grpAct  = grupoActivo[tablaId] || '';
      if (grpAct && filaEl.dataset.grupo !== grpAct) filaEl.style.display = 'none';

      fila.replaceWith(filaEl);

      const cfg = SEM[d.semaforo] || { icon: '', label: '' };
      const msg = newCount === 0
        ? `🗑️ ${nombre} — salida eliminada. Sin registros hoy.`
        : `🗑️ ${nombre} — eliminada. Ahora: ${cfg.icon} ${cfg.label} (${newCount}×)`;
      showToast(msg, 'info');
    })
    .catch(() => {
      btn.disabled = false;
      btn.innerHTML = '<i class="ti ti-trash"></i>';
      showToast('Error de conexión.', 'danger');
    });
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // Hora de regreso (change) — guarda regreso en salida existente
  // ══════════════════════════════════════════════════════════════════════════════

  document.addEventListener('change', function (e) {
    if (!e.target.classList.contains('hora-regreso')) return;
    const fila = e.target.closest('tr.fila-alumno');
    if (!fila) return;
    const salidaId = fila.dataset.salidaId;
    if (!salidaId) return;
    const hrVal = e.target.value.trim();
    if (!hrVal) return;
    if (fila.dataset.saving === '1') return;
    fila.dataset.saving = '1';
    const url = SB.urlRegresoBase.replace('{pk}', salidaId);
    fetch(url, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': SB.csrfToken },
      body: JSON.stringify({ hora_regreso: hrVal }),
    })
    .then(r => r.json())
    .then(d => {
      fila.dataset.saving = '';
      if (!d.ok) { showToast(d.error || 'Error al registrar el regreso.', 'danger'); return; }

      // <--- hecho por claude code: el alumno regresó → AHORA se colorea el semáforo
      const sal = salidasHoy[fila.dataset.iid];
      if (sal) { sal.last_hora_regreso = hrVal; sal.abierta = false; }

      const filaEl = rebuildFila(fila);   // reconstruye ya coloreado y listo para otra salida
      const dur = (d.duracion !== null && d.duracion !== undefined) ? ` (${d.duracion} min)` : '';
      const cfg = SEM[sal ? sal.semaforo : ''] || { icon: '', label: '' };
      let tipo = 'success';
      if (sal && sal.semaforo === 'negro') { tipo = 'danger'; actualizarBadge(1); }
      else if (sal && sal.semaforo === 'rojo') { tipo = 'warning'; }
      showToast(`⟵ ${filaEl.dataset.nombre} regresó — ${cfg.icon} ${cfg.label}${dur}`, tipo);
    })
    .catch(() => { fila.dataset.saving = ''; showToast('Error de conexión.', 'danger'); });
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // Historial alumno
  // ══════════════════════════════════════════════════════════════════════════════

  document.addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-historial');
    if (!btn) return;
    const iid    = btn.dataset.iid;
    const nombre = btn.dataset.nombre;
    document.getElementById('hist-nombre').textContent = nombre;
    document.getElementById('hist-tbody').innerHTML =
      '<tr><td colspan="7" class="text-center py-3"><span class="spinner-border spinner-border-sm"></span></td></tr>';
    document.getElementById('hist-empty').classList.add('d-none');

    bootstrap.Modal.getOrCreateInstance(document.getElementById('modalHistorial')).show();

    const url = SB.urlHistorialBase.replace('/0/', `/${iid}/`) + `?area=${SB.area}`;
    fetch(url)
      .then(r => r.json())
      .then(d => {
        const tbody = document.getElementById('hist-tbody');
        if (!d.salidas || !d.salidas.length) {
          tbody.innerHTML = '';
          document.getElementById('hist-empty').classList.remove('d-none');
          document.getElementById('hist-total').textContent = '';
          return;
        }
        tbody.innerHTML = d.salidas.map(s => {
          const cfg = SEM[s.semaforo] || { label: s.semaforo, cls: s.semaforo, icon: '' };
          return `
          <tr class="hist-row ${cfg.cls}">
            <td>${s.fecha}</td>
            <td>${escHtml(s.clase)}</td>
            <td class="text-center"><span class="badge-sem ${cfg.cls}">${cfg.icon} ${cfg.label}</span></td>
            <td class="text-center">${s.hora_salida}</td>
            <td class="text-center">${s.hora_regreso || '—'}</td>
            <td class="text-center">${s.duracion !== null ? s.duracion + 'm' : '—'}</td>
            <td>${escHtml(s.comentario) || '<span class="text-muted">—</span>'}</td>
          </tr>`;
        }).join('');
        const n = d.salidas.length;
        document.getElementById('hist-total').textContent =
          `${n} salida${n !== 1 ? 's' : ''} registrada${n !== 1 ? 's' : ''}`;
      })
      .catch(() => {
        document.getElementById('hist-tbody').innerHTML =
          '<tr><td colspan="7" class="text-center text-danger">Error al cargar historial.</td></tr>';
      });
  });

  // ══════════════════════════════════════════════════════════════════════════════
  // Notificaciones
  // ══════════════════════════════════════════════════════════════════════════════

  document.getElementById('btnCampana').addEventListener('click', function () {
    cargarNotificaciones();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('modalNotif')).show();
  });

  function cargarNotificaciones() {
    fetch(SB.urlNotifList)
      .then(r => r.json())
      .then(d => {
        const lista = document.getElementById('notif-lista');
        const empty = document.getElementById('notif-empty');
        if (!d.items || !d.items.length) {
          lista.innerHTML = '';
          empty.classList.remove('d-none');
          return;
        }
        empty.classList.add('d-none');
        lista.innerHTML = d.items.map(n => {
          const cfg       = SEM[n.semaforo] || { label: n.semaforo, cls: n.semaforo, icon: '' };
          const alertType = n.semaforo === 'negro' ? 'danger' : n.semaforo === 'rojo' ? 'warning' : 'success';
          return `
          <div class="alert alert-${alertType} d-flex align-items-start justify-content-between gap-2 py-2 mb-2">
            <div>
              <span class="badge-sem ${cfg.cls} me-2">${cfg.icon} ${cfg.label}</span>
              <strong>${escHtml(n.alumno)}</strong>
              <span class="text-muted ms-1">${n.grado} · Grupo ${n.grupo}</span>
              <br>
              <small class="text-muted">${escHtml(n.clase)} — ${n.hora} — ${escHtml(n.maestro)} — ${n.fecha}</small>
            </div>
            <button class="btn btn-sm btn-ghost-secondary flex-shrink-0 btn-notif-leer" data-id="${n.id}">
              <i class="ti ti-check"></i>
            </button>
          </div>`;
        }).join('');
      })
      .catch(() => {});
  }

  document.getElementById('notif-lista').addEventListener('click', function (e) {
    const btn = e.target.closest('.btn-notif-leer');
    if (!btn) return;
    const url = SB.urlNotifLeerBase.replace('{pk}', btn.dataset.id);
    fetch(url, { method: 'POST', headers: { 'X-CSRFToken': SB.csrfToken } })
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          btn.closest('.alert').remove();
          actualizarBadge(-1);
          if (!document.getElementById('notif-lista').querySelector('.alert')) {
            document.getElementById('notif-empty').classList.remove('d-none');
          }
        }
      });
  });

  document.getElementById('btn-leer-todas').addEventListener('click', function () {
    fetch(SB.urlNotifLeerTodas, { method: 'POST', headers: { 'X-CSRFToken': SB.csrfToken } })
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          document.getElementById('notif-lista').innerHTML = '';
          document.getElementById('notif-empty').classList.remove('d-none');
          setBadge(0);
        }
      });
  });

  // Polling cada 30s
  setInterval(() => {
    fetch(SB.urlNotifCount)
      .then(r => r.json())
      .then(d => setBadge(d.count || 0))
      .catch(() => {});
  }, 30000);

  function setBadge(n) {
    const b = document.getElementById('bell-badge');
    if (!b) return;
    b.textContent = n;
    b.style.display = n > 0 ? '' : 'none';
  }
  function actualizarBadge(delta) {
    const b = document.getElementById('bell-badge');
    if (!b) return;
    setBadge(Math.max(0, parseInt(b.textContent || '0', 10) + delta));
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Toast
  // ══════════════════════════════════════════════════════════════════════════════

  function showToast(msg, tipo) {
    const bgMap = { success: 'bg-success', warning: 'bg-warning text-dark', danger: 'bg-danger', info: 'bg-info' };
    const bg = bgMap[tipo] || 'bg-secondary';
    const el = document.createElement('div');
    el.className = `toast align-items-center text-white border-0 show ${bg}`;
    el.setAttribute('role', 'alert');
    el.innerHTML = `<div class="d-flex"><div class="toast-body">${escHtml(msg)}</div>
      <button type="button" class="btn-close btn-close-white me-2 m-auto" onclick="this.closest('.toast').remove()"></button>
      </div>`;
    document.getElementById('toast-container').appendChild(el);
    setTimeout(() => el.remove(), 5000);
  }

  // ══════════════════════════════════════════════════════════════════════════════
  // Helpers
  // ══════════════════════════════════════════════════════════════════════════════

  function escHtml(s) {
    if (!s) return '';
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // ── Init ─────────────────────────────────────────────────────────────────────
  console.log('[SB v9] grados SQL Server:', Object.keys(SB.alumnosPorGrado));
  console.log('[SB v9] grados MaestroClase:', Object.keys(SB.clasesPorGrado));
  console.log('[SB v9] salidas hoy:', Object.keys(salidasHoy).length, 'alumnos');
  console.log('[SB v9] esCoord:', esCoord);
  poblarTablas();

})();
