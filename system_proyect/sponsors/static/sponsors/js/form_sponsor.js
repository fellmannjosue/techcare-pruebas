/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
(function(){
  var btn = document.getElementById('btn-eliminar');
  if(!btn) return;
  btn.addEventListener('click', function(){
    Swal.fire({
      icon: 'warning',
      title: '¿Eliminar este sponsor?',
      html: 'Se borrará también su <strong>historial de ingresos, padrinazgos y correspondencia</strong>.<br>Esta acción no se puede deshacer.',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#d63939'
    }).then(function(r){
      if(r.isConfirmed) document.getElementById('form-eliminar').submit();
    });
  });
})();

/* <--- hecho por claude code (06-nov-2026): imprimir (antes onclick en el HTML) + buscador de la ficha como Access */
(function(){
  var imp = document.getElementById('btn-imprimir');
  if (imp) imp.addEventListener('click', function(){ window.print(); });

  var box = document.getElementById('spn-buscar'); if (!box) return;
  var res = document.getElementById('spn-res'), URL_B = box.dataset.url, FICHA = box.dataset.ficha;
  var t = null, ultimo = 0, items = [], sel = -1;
  function esc(x){ return String(x).replace(/[&<>"]/g, function(c){ return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]; }); }
  function fichaUrl(id){ return FICHA.replace(/\/0\/$/, '/' + id + '/'); }
  function pintar(datos){
    items = datos; sel = datos.length ? 0 : -1;
    res.innerHTML = datos.length ? datos.map(function(d, i){
      return '<a href="' + fichaUrl(d.id) + '"' + (i === 0 ? ' class="is-sel"' : '') + '><span class="id">' + d.id + '</span><span class="n">' + esc(d.nombre) + '</span>' +
        (d.off ? '<span class="off">Inactivo</span>' : '') + '<span class="l">' + esc(d.lugar) + '</span></a>';
    }).join('') : '<div class="vacio">Sin resultados.</div>';
    res.hidden = false;
  }
  function buscar(inp){
    var q = inp.value.trim(); clearTimeout(t);
    if (!q) { res.hidden = true; return; }
    t = setTimeout(function(){
      var n = ++ultimo;
      fetch(URL_B + '?campo=' + encodeURIComponent(inp.dataset.campo) + '&q=' + encodeURIComponent(q), { credentials: 'same-origin' })
        .then(function(r){ return r.json(); }).then(function(d){ if (n === ultimo) pintar(d); }).catch(function(){});
    }, 250);
  }
  box.querySelectorAll('input[data-campo]').forEach(function(inp){
    inp.addEventListener('input', function(){
      box.querySelectorAll('input[data-campo]').forEach(function(o){ if (o !== inp) o.value = ''; });
      buscar(inp);
    });
    inp.addEventListener('focus', function(){ if (inp.value.trim()) buscar(inp); });
    inp.addEventListener('keydown', function(e){
      var as = res.querySelectorAll('a');
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        if (!as.length) return; e.preventDefault();
        sel = (sel + (e.key === 'ArrowDown' ? 1 : -1) + as.length) % as.length;
        as.forEach(function(a, i){ a.classList.toggle('is-sel', i === sel); });
      } else if (e.key === 'Enter') {
        e.preventDefault();   // no enviar el formulario del sponsor
        if (sel >= 0 && items[sel]) location.href = fichaUrl(items[sel].id);
      } else if (e.key === 'Escape') { res.hidden = true; }
    });
  });
  document.addEventListener('click', function(e){ if (!box.contains(e.target)) res.hidden = true; });
  if (box.dataset.auto === '1') { var f = box.querySelector('input[data-campo="last_name_1"]'); if (f) f.focus(); }
})();
