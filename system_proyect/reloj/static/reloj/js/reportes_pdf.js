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
