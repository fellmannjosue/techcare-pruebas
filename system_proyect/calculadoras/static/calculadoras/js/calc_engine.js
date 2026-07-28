/* hecho por claude code: motor cliente de las calculadoras de tiempo (una tarjeta por pagina). */
(function () {
  'use strict';

  function show(el) { if (el) el.classList.remove('d-none'); }
  function hide(el) { if (el) el.classList.add('d-none'); }

  function setField(card, name, val) {
    var el = card.querySelector('[data-field="' + name + '"]');
    if (el) el.textContent = val;
  }

  function numVal(card, sel) {
    var el = card.querySelector(sel);
    if (!el) return NaN;
    return parseFloat(String(el.value).replace(',', '.'));
  }

  function strVal(card, sel) {
    var el = card.querySelector(sel);
    return el ? String(el.value).trim() : '';
  }

  // ── entre_horas ──
  function computeEntreHoras(card) {
    var ini = strVal(card, '#inp-hora-inicio');
    var fin = strVal(card, '#inp-hora-fin');
    if (!ini || !fin) return { ok: false, error: 'Ingresa ambas horas.' };
    var a = ini.split(':'), b = fin.split(':');
    var h1 = parseInt(a[0], 10), m1 = parseInt(a[1], 10);
    var h2 = parseInt(b[0], 10), m2 = parseInt(b[1], 10);
    if (isNaN(h1) || isNaN(m1) || isNaN(h2) || isNaN(m2)) {
      return { ok: false, error: 'Ingresa ambas horas.' };
    }
    var diffMin = (h2 * 60 + m2) - (h1 * 60 + m1);
    if (diffMin <= 0) return { ok: false, error: 'La hora fin debe ser posterior a la hora inicio.' };
    var hh = Math.floor(diffMin / 60), mm = diffMin % 60;
    var principal;
    if (hh > 0 && mm > 0) principal = hh + ' hora(s) ' + mm + ' minuto(s)';
    else if (hh > 0) principal = hh + ' hora(s)';
    else principal = mm + ' minuto(s)';
    return {
      ok: true,
      fields: {
        principal: principal,
        horas_dec: (diffMin / 60).toFixed(2) + ' h',
        minutos: diffMin + ' min',
        nota: 'De ' + ini + ' a ' + fin
      }
    };
  }

  // ── horas_dias ──
  function computeHorasDias(card) {
    var h = numVal(card, '#inp-horas');
    if (isNaN(h)) return { ok: false, error: 'Ingresa un número de horas.' };
    var dias = Math.floor(h / 24), resto = h % 24;
    return {
      ok: true,
      fields: {
        dias: dias + ' día(s)',
        resto: resto > 0 ? '+ ' + resto.toFixed(1) + ' horas restantes' : ''
      }
    };
  }

  // ── minutos_horas ──
  function computeMinutosHoras(card) {
    var m = numVal(card, '#inp-minutos');
    if (isNaN(m)) return { ok: false, error: 'Ingresa un número de minutos.' };
    var h = Math.floor(m / 60), resto = m % 60;
    return {
      ok: true,
      fields: {
        horas: h + ' hora(s)',
        resto: resto > 0 ? '+ ' + resto + ' minutos restantes' : ''
      }
    };
  }

  // ── fecha_fecha ──
  function computeFechaFecha(card) {
    var si = strVal(card, '#inp-fecha-inicio');
    var sf = strVal(card, '#inp-fecha-fin');
    if (!si || !sf) return { ok: false, error: 'Selecciona ambas fechas.' };
    var fi = new Date(si), ff = new Date(sf);
    if (isNaN(fi.getTime()) || isNaN(ff.getTime())) {
      return { ok: false, error: 'Selecciona ambas fechas.' };
    }
    var diff = Math.round((ff - fi) / 86400000);
    var absDiff = Math.abs(diff);
    return {
      ok: true,
      fields: {
        dias_total: String(absDiff),
        semanas: (absDiff / 7).toFixed(1),
        meses: (absDiff / 30.44).toFixed(1)
      }
    };
  }

  function calcFor(card) {
    switch (card.getAttribute('data-calc')) {
      case 'entre_horas': return computeEntreHoras(card);
      case 'horas_dias': return computeHorasDias(card);
      case 'minutos_horas': return computeMinutosHoras(card);
      case 'fecha_fecha': return computeFechaFecha(card);
      default: return null;
    }
  }

  function runCard(card) {
    var result = card.querySelector('[data-result]');
    var error = card.querySelector('[data-error]');
    var loading = card.querySelector('.calc-loading');
    hide(result);
    hide(error);
    if (loading) loading.classList.add('show');
    setTimeout(function () {
      if (loading) loading.classList.remove('show');
      var res = calcFor(card);
      if (!res) return;
      if (res.ok) {
        for (var name in res.fields) {
          if (Object.prototype.hasOwnProperty.call(res.fields, name)) {
            setField(card, name, res.fields[name]);
          }
        }
        show(result);
      } else if (error) {
        error.textContent = res.error;
        show(error);
      }
    }, 700);
  }

  document.addEventListener('click', function (e) {
    var btn = e.target.closest ? e.target.closest('.calc-btn') : null;
    if (!btn) return;
    var card = btn.closest('.calc-card');
    if (card) runCard(card);
  });
})();
