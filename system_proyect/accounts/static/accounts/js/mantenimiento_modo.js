/* <--- hecho por claude code: extraído del template. Las URLs de Django
   llegan por data-* en #mantenimiento_modo-config (un .js no procesa Django). */
const CFG_MANTENIMIENTO_MODO = (function(){
  var d = document.getElementById("mantenimiento_modo-config").dataset;
  return {
    modulosGuardar: d.modulosGuardar,
    csrf: d.csrf || "",
  };
})();

(function(){
  var sels = document.querySelectorAll('.mant-mod-sel');
  var st   = document.getElementById('mant-mod-status');
  var csrf = (document.cookie.match(/csrftoken=([^;]+)/)||[])[1] || '';
  // <--- hecho por claude code: la audiencia (área + docentes) se guarda junto con los estados
  function usuariosSeleccionados(){
    return [].slice.call(document.querySelectorAll('.mant-chk:checked')).map(function(c){ return c.value; });
  }
  function areaActual(){
    var b = document.querySelector('.mant-area-btn.btn-primary');
    return b ? b.dataset.area : 'all';
  }
  var AREA_LABEL = {all:'todas las áreas', staff:'staff', bilingue:'Bilingüe', colegio:'Colegio'};

  function pintar(s){
    var box = s.closest('.border');
    if(!box) return;
    box.classList.remove('border-danger','border-warning');
    if(s.value==='bloqueado') box.classList.add('border-danger');
    else if(s.value==='lectura') box.classList.add('border-warning');
  }

  function guardar(){
    var payload = {};
    sels.forEach(function(s){ payload[s.dataset.key] = s.value; });
    st.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Guardando…';
    fetch(CFG_MANTENIMIENTO_MODO.modulosGuardar, {
      method:'POST', headers:{'X-CSRFToken':csrf,'Content-Type':'application/json'},
      body: JSON.stringify({modulos: payload, blocked_users: usuariosSeleccionados(), area: areaActual()})
    }).then(function(r){return r.json();}).then(function(d){
      st.innerHTML = d.ok ? '<i class="ti ti-check me-1 text-green"></i>Guardado'
                          : '<i class="ti ti-alert-triangle me-1 text-danger"></i>Error';
      sels.forEach(pintar);
    }).catch(function(){ st.innerHTML='<i class="ti ti-alert-triangle me-1 text-danger"></i>Error'; });
  }
  // <--- hecho por claude code: restaurar todo a "Normal" con confirmación
  var btnReset = document.getElementById('mant-mod-reset');
  if (btnReset) btnReset.addEventListener('click', function(){
    var activos = [].slice.call(sels).filter(function(s){ return s.value !== 'normal'; });
    if (activos.length === 0) {
      Swal.fire({icon:'info', title:'Ya está en el predeterminado',
                 text:'Todos los formularios están en Normal.', timer:1600, showConfirmButton:false});
      return;
    }
    Swal.fire({
      icon: 'question',
      title: '¿Restaurar al predeterminado?',
      html: 'Se quitarán las restricciones de <strong>' + activos.length + ' formulario(s)</strong> ' +
            'y todos volverán a <strong>Normal</strong>.<br><br>' +
            'Los usuarios afectados recuperarán el acceso de inmediato.',
      showCancelButton: true,
      confirmButtonText: 'Sí, restaurar',
      cancelButtonText: 'Cancelar',
      confirmButtonColor: '#2fb344'
    }).then(function(r){
      if (!r.isConfirmed) return;
      sels.forEach(function(s){ s.value = 'normal'; pintar(s); });
      guardar();
      Swal.fire({icon:'success', title:'Restaurado', text:'Todos los formularios están en Normal.',
                 timer:1600, showConfirmButton:false});
    });
  });

  sels.forEach(function(s){
    s.addEventListener('change', function(){
      // Si restringe un formulario y NO hay docentes seleccionados, avisar:
      // sin selección el bloqueo alcanza a TODA el área.
      if (s.value !== 'normal' && usuariosSeleccionados().length === 0) {
        var area = areaActual();
        var n = document.querySelectorAll('.mant-chk').length;
        Swal.fire({
          icon: 'warning',
          title: 'No has seleccionado ningún docente',
          html: 'Arriba, en <strong>Usuarios específicos</strong>, no hay nadie marcado.<br><br>' +
                'Si continúas, <strong>la restricción se aplicará a ' +
                '<u>todos</u> los usuarios de ' + (AREA_LABEL[area] || area) + '</strong> (hasta ' + n + ' en la lista), ' +
                'no solo a una persona.',
          showCancelButton: true,
          confirmButtonText: 'Aplicar a toda el área',
          cancelButtonText: 'Voy a seleccionar un docente',
          confirmButtonColor: '#f76707'
        }).then(function(r){
          if (r.isConfirmed) { guardar(); }
          else { s.value = 'normal'; pintar(s); }   // revierte el cambio
        });
        return;
      }
      guardar();
    });
    pintar(s);
  });
})();
