/* <--- hecho por claude code (06-nov-2026): Historial del maestro — línea de tiempo (diseño B).
   Filtro por tipo + buscador. Con «Progress» además se muestra el acordeón de Progress del grado (pestañas de antes). */
(function () {
  var chips = document.getElementById('hm-chips'); if (!chips) return;
  var q = document.getElementById('hm-q'), sin = document.getElementById('hm-sin');
  var clasico = document.getElementById('hm-clasico'), nota = document.getElementById('hm-nota-pro');
  var tipo = '';
  function aplicar() {
    var txt = (q.value || '').trim().toLowerCase(), vis = 0;
    document.querySelectorAll('#hm-feed [data-dia]').forEach(function (d) {
      var n = 0;
      d.querySelectorAll('.hm-it').forEach(function (it) {
        var ok = (!tipo || it.dataset.t === tipo) && (!txt || it.dataset.q.indexOf(txt) > -1);
        it.hidden = !ok; if (ok) n++;
      });
      d.hidden = !n; vis += n;
    });
    if (sin) sin.hidden = !!vis || !document.querySelector('#hm-feed [data-dia]');
    var pro = tipo === 'pro';
    if (clasico) {
      clasico.hidden = !pro;
      if (pro) {
        var nav = clasico.querySelector('.card-header'); if (nav) nav.hidden = true;
        var t = document.getElementById('tab-progress');
        if (t && window.bootstrap) bootstrap.Tab.getOrCreateInstance(t).show();
      }
    }
    if (nota) nota.hidden = !pro;
  }
  chips.addEventListener('click', function (e) {
    var b = e.target.closest('.hm-chip'); if (!b) return;
    tipo = b.dataset.t || '';
    chips.querySelectorAll('.hm-chip').forEach(function (x) { x.classList.toggle('on', x === b); });
    aplicar();
  });
  q.addEventListener('input', aplicar);
})();
