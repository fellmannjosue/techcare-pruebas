/* <--- hecho por claude code: lógica del overlay de bienvenida (extraído de _welcome_overlay.html) */
(function () {
  // Leer cookie tc_welcome
  function getCookie(name) {
    const m = document.cookie.match('(?:^|; )' + name + '=([^;]*)');
    return m ? decodeURIComponent(m[1]) : null;
  }
  function delCookie(name) {
    document.cookie = name + '=;max-age=0;path=/;samesite=lax';
  }

  let nombre = getCookie('tc_welcome');
  if (!nombre) return;
  delCookie('tc_welcome');
  // Django puede envolver valores con espacios entre comillas — eliminarlas
  nombre = nombre.replace(/^"|"$/g, '');

  const ov    = document.getElementById('tcWelcomeOverlay');
  const logo  = document.getElementById('tcWLogo');
  const bien  = document.getElementById('tcWBienvenido');
  const usu   = document.getElementById('tcWUsuario');
  const sub   = document.getElementById('tcWSubtitulo');
  const bar   = document.getElementById('tcWBar');
  const lbl   = document.getElementById('tcWLabel');
  const parts = document.getElementById('tcWParticles');

  if (!ov) return;

  usu.textContent = '@' + nombre;

  // Mostrar overlay
  ov.style.display = 'flex';

  // Partículas
  const colors = ['#60a5fa', '#a78bfa', '#c4b5fd', '#f0abfc', '#bfdbfe', '#fff'];   // <--- paleta Horizon (14-oct-2026)
  for (let i = 0; i < 22; i++) {
    const p = document.createElement('div');
    p.className = 'tc-p';
    const s = Math.random() * 12 + 4;
    p.style.cssText = `width:${s}px;height:${s}px;left:${Math.random() * 100}%;top:${Math.random() * 100}%;background:${colors[i % colors.length]};animation-delay:${Math.random() * 2}s;animation-duration:${2 + Math.random() * 1.5}s`;
    parts.appendChild(p);
  }

  var cerrado = false;
  function cerrar() {
    if (cerrado) return; cerrado = true;
    ov.style.transition = 'opacity .45s ease';
    ov.style.opacity = '0';
    setTimeout(function () { ov.remove(); }, 480);
    document.removeEventListener('keydown', alTeclear);
  }
  function alTeclear(e) { if (e.key === 'Escape') cerrar(); }
  ov.addEventListener('click', cerrar);
  document.addEventListener('keydown', alTeclear);

  // Secuencia de animación
  requestAnimationFrame(function () {
    logo.style.opacity = '1';
    logo.style.transform = 'scale(1)';
    setTimeout(function () {
      bien.style.opacity = '1';
      bien.style.transform = 'translateY(0)';
      usu.style.opacity = '1';
      usu.style.transform = 'translateY(0)';
      sub.style.opacity = '1';

      setTimeout(function () {
        bar.style.width = '100%';
        const steps = ['Cargando módulos…', 'Verificando permisos…', 'Preparando dashboard…', '¡Listo! ✓'];
        let idx = 0;
        lbl.textContent = steps[0];
        const iv = setInterval(function () {
          idx = Math.min(idx + 1, steps.length - 1);
          lbl.textContent = steps[idx];
          if (idx === steps.length - 1) clearInterval(iv);
        }, 1000);

        // <--- hecho por claude code (14-oct-2026): 75 % más rápida (antes ~20 s, ahora ~5 s) y se cierra con clic o Esc
        setTimeout(cerrar, 4300);

      }, 300);
    }, 100);
  });
})();
