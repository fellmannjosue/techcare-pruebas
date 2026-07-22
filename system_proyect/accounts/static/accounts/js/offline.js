/* <--- hecho por claude code: extraído del template (JS fuera del HTML) */
// Reintenta automáticamente cuando vuelve la conexión
    function actualizar(){
      var e=document.getElementById('estado');
      if(navigator.onLine){ e.textContent='Conexión restablecida, recargando…'; setTimeout(function(){location.reload();},700); }
      else { e.textContent='Esperando conexión…'; }
    }
    window.addEventListener('online', actualizar);
    actualizar();
