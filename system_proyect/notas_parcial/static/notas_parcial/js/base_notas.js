/* notas_parcial/base_notas.js
   Bridge vars injected via window._PAGE from base_notas.html:
     anioActual
*/
(function () {
  const AÑO_ACTUAL = window._PAGE.anioActual;

  function animar(elId, pasos) {
    const el = document.getElementById(elId);
    let i = 0;
    el.textContent = pasos[0];
    el.style.opacity = '1'; el.style.transform = 'scale(1)';
    const tick = setInterval(function () {
      el.style.opacity = '0';
      el.style.transform = 'scale(0.7)';
      setTimeout(function () {
        i = Math.min(i + 1, pasos.length - 1);
        el.textContent = pasos[i];
        el.style.opacity = '1';
        el.style.transform = 'scale(1.15)';
        setTimeout(function () { el.style.transform = 'scale(1)'; }, 180);
        if (i >= pasos.length - 1) clearInterval(tick);
      }, 250);
    }, 750);
  }

  function animarDos(id1, id2) {
    [id1, id2].forEach(function (id, idx) {
      const el = document.getElementById(id);
      if (!el) return;
      el.style.opacity = '1'; el.style.transform = 'scale(1)';
      setTimeout(function () {
        el.style.transform = 'scale(1.4)';
        setTimeout(function () {
          el.style.transform = 'scale(0.85)';
          setTimeout(function () { el.style.transform = 'scale(1)'; }, 150);
        }, 200);
      }, idx * 120);
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    const selParcial = document.querySelector('select[name="parcial"]');
    const inpAnio    = document.querySelector('input[name="anio"]');

    if (selParcial) {
      selParcial.addEventListener('change', function () {
        const v = parseInt(selParcial.value);
        if (v >= 3) {
          animar('emoji-futuro', ['😕', '😟', '😤', '😠']);
          new bootstrap.Modal(document.getElementById('modalParcialFuturo')).show();
          selParcial.value = '';
        } else if (v === 1) {
          animar('emoji-pasado', ['😅', '🤒', '😵', '💀']);
          new bootstrap.Modal(document.getElementById('modalParcialPasado')).show();
          selParcial.value = '';
        }
      });
    }

    if (inpAnio) {
      inpAnio.addEventListener('change', function () {
        if (parseInt(inpAnio.value) < AÑO_ACTUAL) {
          inpAnio.value = AÑO_ACTUAL;
          animarDos('emoji-anio-1', 'emoji-anio-2');
          new bootstrap.Modal(document.getElementById('modalAnioPasado')).show();
        }
      });
    }
  });
})();
