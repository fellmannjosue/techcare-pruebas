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

/* <--- hecho por claude code (06-nov-2026, pedido del usuario): AUTOGUARDADO de la ficha.
   Cada cambio se manda 1.5 s después de dejar de escribir (mismo POST + ?ajax=1). Un sponsor NUEVO se crea
   en cuanto el formulario es válido (Apellido 1 + Ciudad) y desde ahí la ficha pasa a modo edición sin recargar. */
(function(){
  var form = document.getElementById('form-sponsor');
  if (!form || form.dataset.autoguardar !== '1') return;
  var estado = document.getElementById('spn-auto');
  var timer = null, enCurso = false, pendiente = false, cambiado = false;
  function pintar(clase, icono, txt){ if (!estado) return; estado.className = 'spn-auto ' + clase; estado.innerHTML = '<i class="ti ' + icono + '"></i> '; estado.appendChild(document.createTextNode(txt)); }
  function hora(){ var d = new Date(); return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2); }
  function urlGuardar(){ var a = form.getAttribute('action') || location.pathname; return a + (a.indexOf('?') > -1 ? '&' : '?') + 'ajax=1'; }
  function guardar(final){
    if (!cambiado) return;
    if (enCurso) { pendiente = true; return; }
    enCurso = true; cambiado = false; pintar('guardando', 'ti-loader-2', 'Guardando…');
    fetch(urlGuardar(), { method: 'POST', body: new FormData(form), credentials: 'same-origin', keepalive: !!final,
                          headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function(r){ return r.json().catch(function(){ return { ok: false }; }); })
      .then(function(j){
        if (j.ok) {
          if (j.creado && j.url) {   // pasa a modo edición: las siguientes veces actualiza la misma ficha
            form.setAttribute('action', j.url); form.dataset.modo = 'editar';
            try { history.replaceState(null, '', j.url); } catch (e) {}
            pintar('ok', 'ti-cloud-check', 'Sponsor creado (ID ' + j.id + ') · guardado ' + hora());
          } else pintar('ok', 'ti-cloud-check', 'Guardado ' + hora());
        } else if (j.errores) {
          var faltan = Object.keys(j.errores).map(function(k){ return (j.etiquetas && j.etiquetas[k]) || k; });
          pintar(form.dataset.modo === 'nuevo' ? '' : 'mal', 'ti-alert-circle',
                 (form.dataset.modo === 'nuevo' ? 'Aún no se guarda: falta ' : 'No se guardó: revisa ') + faltan.join(', '));
        } else pintar('mal', 'ti-alert-circle', 'No se pudo guardar. Revisa la conexión.');
      })
      .catch(function(){ pintar('mal', 'ti-wifi-off', 'Sin conexión: no se guardó.'); cambiado = true; })
      .then(function(){ enCurso = false; if (pendiente) { pendiente = false; cambiado = true; guardar(); } });
  }
  function programar(){ cambiado = true; clearTimeout(timer); timer = setTimeout(guardar, 1500); }
  form.addEventListener('input', programar);
  form.addEventListener('change', programar);
  // al salir de la página con cambios sin mandar, se envían igual
  window.addEventListener('pagehide', function(){ if (cambiado) { clearTimeout(timer); guardar(true); } });
})();
