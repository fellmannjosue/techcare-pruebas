/* <--- hecho por claude code: bloqueo de scroll para TODOS los modales de Bootstrap.
   Problema: al abrir un modal la página "saltaba" hacia arriba (el fondo se movía).
   Solución: al abrir cualquier modal congelamos el body en su posición actual con
   position:fixed + top negativo; al cerrar el último modal restauramos el scroll.
   Soporta modales apilados con un contador. Es global: aplica a red, reloj, etc. */
(function () {
  var lockY = 0;   // posición del scroll congelada
  var locks = 0;   // cuántos modales hay abiertos (para no romper con apilados)

  function scrollActual() {
    return window.scrollY || window.pageYOffset ||
           document.documentElement.scrollTop || document.body.scrollTop || 0;
  }

  function bloquear() {
    if (locks++ > 0) return;              // ya bloqueado por otro modal
    lockY = scrollActual();
    document.body.style.top = (-lockY) + 'px';
    document.body.classList.add('tc-modal-lock');
  }

  function desbloquear() {
    if (locks > 0) locks--;
    if (locks > 0) return;                // aún queda algún modal abierto
    document.body.classList.remove('tc-modal-lock');
    document.body.style.top = '';
    window.scrollTo(0, lockY);            // volver EXACTAMENTE a donde estaba
  }

  // Se dispara para cualquier modal (los eventos burbujean hasta document)
  document.addEventListener('show.bs.modal', bloquear);
  document.addEventListener('hidden.bs.modal', desbloquear);
})();
