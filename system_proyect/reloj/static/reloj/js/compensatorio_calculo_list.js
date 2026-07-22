/* <--- hecho por claude code: extraído del template. Los valores de Django
   llegan por data-* en #compensatorio_calculo_list-config (un .js no lo procesa Django). */
const CFG = (function(){
  var d = document.getElementById("compensatorio_calculo_list-config").dataset;
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
    v6: d.v6,
    j6: j(d.v6),
    v7: d.v7,
    j7: j(d.v7),
    v8: d.v8,
    j8: j(d.v8),
    v9: d.v9,
    j9: j(d.v9),
    v10: d.v10,
    j10: j(d.v10),
    v11: d.v11,
    j11: j(d.v11),
    v12: d.v12,
    j12: j(d.v12),
  };
})();

// Reactivar el tab de Gilma tras filtrar (?tab=gilma)
  (function () {
    var p = new URLSearchParams(window.location.search);
    var map = { gilma: 'tab-gilma-btn' };
    var id = map[p.get('tab')];
    if (id) {
      var btn = document.getElementById(id);
      if (btn && window.bootstrap) new bootstrap.Tab(btn).show();
    }
  })();
  // Atajos de rango: Mes / Quincena 1 (1–15) / Quincena 2 (16–fin), según el mes de "Hasta"
  (function () {
    function fmt(y, m, d) { return y + '-' + String(m + 1).padStart(2, '0') + '-' + String(d).padStart(2, '0'); }
    document.querySelectorAll('[data-grange]').forEach(function (b) {
      b.addEventListener('click', function () {
        var base = document.getElementById('g_fin').value || document.getElementById('g_ini').value || new Date().toISOString().slice(0, 10);
        var dt = new Date(base + 'T00:00:00'), y = dt.getFullYear(), m = dt.getMonth();
        var last = new Date(y, m + 1, 0).getDate(), r = this.dataset.grange, ini, fin;
        if (r === 'mes') { ini = fmt(y, m, 1); fin = fmt(y, m, last); }
        else if (r === 'q1') { ini = fmt(y, m, 1); fin = fmt(y, m, 15); }
        else { ini = fmt(y, m, 16); fin = fmt(y, m, last); }
        document.getElementById('g_ini').value = ini;
        document.getElementById('g_fin').value = fin;
        document.getElementById('gilmaRangoForm').submit();
      });
    });
  })();

window._PAGE = {
  csrf:         CFG.v0,
  canEdit:      CFG.j8,
  canEditExtra:   CFG.j9,
  canDeleteExtra: CFG.j10,
  isSuperuser:    CFG.j11,
  anio:         CFG.j12,
  urlTeGet:     '/reloj/compensatorio-calculo/{pk}/tiempo-extra/',
  urlTeAdd:     '/reloj/compensatorio-calculo/{pk}/tiempo-extra/add/',
  urlTeDel:     '/reloj/compensatorio-te/{te_pk}/delete/',
  urlEmpBuscar: CFG.v1,
  urlSetHorasAdeudadas: '/reloj/compensatorio-calculo/{pk}/set-horas-adeudadas/',
  urlSetTomado: '/reloj/compensatorio-calculo/{pk}/set-tomado/',
  urlGetTomado: '/reloj/compensatorio-calculo/{pk}/tomado/',
  urlTomManualAdd: '/reloj/compensatorio-calculo/{pk}/tomado-manual/add/',
  urlTomManualDel: '/reloj/compensatorio-tomado-manual/{pk}/delete/',
  urlMensualAdd:    CFG.v2,
  urlMensualCell:   CFG.v3,
  urlMensualComentario: CFG.v4,
  urlDetGet: CFG.v5,
  urlDetAdd: CFG.v6,
  urlDetDel: '/reloj/compensatorio-mensual-detalle/{pk}/delete/',
  urlMensualDel:    '/reloj/compensatorio-mensual/{pk}/delete/',
  urlInstructorAdd: CFG.v7,
  urlInstructorSet: '/reloj/compensatorio-instructor/{pk}/set/',
  urlInstructorDel: '/reloj/compensatorio-instructor/{pk}/delete/',
  urlInstTeGet:  '/reloj/compensatorio-instructor/{pk}/te/',
  urlInstTeAdd:  '/reloj/compensatorio-instructor/{pk}/te/add/',
  urlInstTeDel:  '/reloj/compensatorio-instructor-te/{pk}/delete/',
  urlInstTomGet: '/reloj/compensatorio-instructor/{pk}/tomado/',
  urlInstTomAdd: '/reloj/compensatorio-instructor/{pk}/tomado/add/',
  urlInstTomDel: '/reloj/compensatorio-instructor-tomado/{pk}/delete/',
};
