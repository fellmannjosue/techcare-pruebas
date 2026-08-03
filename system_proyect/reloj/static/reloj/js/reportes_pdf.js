/* <--- hecho por claude code: extraído del template. Las URLs de Django
   llegan por data-* en #reportes_pdf-config (un .js no procesa Django). */
const CFG_REPORTES_PDF = (function(){
  var d = document.getElementById("reportes_pdf-config").dataset;
  return {
    relojExportarPdf: d.relojExportarPdf,
    csrf: d.csrf || "",
  };
})();

// Cargar el PDF de cada tab solo al abrirlo (lazy) para no generar los 5 de golpe.
  (function () {
    function cargar(pane) {
      var f = pane.querySelector('iframe[data-src]');
      if (f && !f.src) f.src = f.dataset.src;
    }
    document.querySelectorAll('[data-bs-toggle="tab"]').forEach(function (t) {
      t.addEventListener('shown.bs.tab', function (e) {
        var sel = e.target.getAttribute('href');
        var pane = document.querySelector(sel);
        if (pane) cargar(pane);
      });
    });
  })();

  // <--- hecho por claude code: filtro por mes/año en cada pestaña. La barra declara
  // en data-* su URL base, los parámetros fijos (sec=…) y el tipo de filtro, así que
  // todas las pestañas usan este mismo código en vez de una función por reporte.
  (function () {
    function ultimoDia(anio, mes) {           // mes 1-12
      return new Date(anio, mes, 0).getDate();
    }

    function consultaDe(bar) {
      var tipo  = bar.dataset.tipo;
      var extra = bar.dataset.extra || '';
      var partes = ['fmt=pdf'];
      if (extra) partes.push(extra);

      if (tipo === 'anio') {
        var inp = bar.querySelector('.rep-anio');
        if (!inp || !inp.value) return null;
        partes.push('anio=' + encodeURIComponent(inp.value));
      } else {
        var m = bar.querySelector('.rep-mes');
        if (!m || !m.value) return null;
        if (tipo === 'mesrango') {
          // Ese reporte trabaja por rango: el mes se convierte en primer y último día
          var p = m.value.split('-'), a = parseInt(p[0], 10), mm = parseInt(p[1], 10);
          partes.push('fecha_inicio=' + m.value + '-01');
          partes.push('fecha_fin=' + m.value + '-' + String(ultimoDia(a, mm)).padStart(2, '0'));
        } else {
          partes.push('mes=' + encodeURIComponent(m.value));
        }
      }
      return partes.join('&');
    }

    document.querySelectorAll('.rep-bar[data-base] .rep-ver').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var bar = btn.closest('.rep-bar');
        var qs  = consultaDe(bar);
        if (!qs) return;                       // sin fecha elegida no se hace nada
        var base = bar.dataset.base;
        var pane = bar.closest('.tab-pane');
        var fr   = pane && pane.querySelector('iframe');
        var dl   = bar.querySelector('.rep-dl');
        if (dl) dl.setAttribute('href', base + '?' + qs);
        if (fr) {
          var url = base + '?' + qs + '&inline=1';
          fr.dataset.src = url;                // para que la carga diferida no lo pise
          fr.src = url;
        }
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Cargando…';
        setTimeout(function () {
          btn.innerHTML = '<i class="ti ti-eye me-1"></i>Ver';
        }, 1500);
      });
    });
  })();

  // Reporte general: aplicar rango Desde/Hasta al iframe y a la descarga
  (function () {
    var btn = document.getElementById('rg_ver');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var ini = document.getElementById('rg_ini').value,
          fin = document.getElementById('rg_fin').value,
          dl  = document.getElementById('rg_dl'),
          fr  = document.getElementById('rg_frame'),
          base = CFG_REPORTES_PDF.relojExportarPdf;
      dl.setAttribute('href', base + '?fecha_inicio=' + ini + '&fecha_fin=' + fin);
      fr.src = base + '?fecha_inicio=' + ini + '&fecha_fin=' + fin + '&inline=1';
    });
  })();

  // Gilma: aplicar rango Desde/Hasta al iframe y a la descarga
  (function () {
    var btn = document.getElementById('gpdf_ver');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var ini = document.getElementById('gpdf_ini').value,
          fin = document.getElementById('gpdf_fin').value,
          dl  = document.getElementById('gpdf_dl'),
          fr  = document.getElementById('gpdf_frame'),
          base = dl.getAttribute('href').split('?')[0];
      dl.setAttribute('href', base + '?fmt=pdf&sec=gilma&gini=' + ini + '&gfin=' + fin);
      fr.src = base + '?fmt=pdf&inline=1&sec=gilma&gini=' + ini + '&gfin=' + fin;
    });
  })();
