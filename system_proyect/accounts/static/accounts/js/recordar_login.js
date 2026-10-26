// <--- hecho por claude code (26-oct-2026): "Recordar mis datos" en el login (para la app de escritorio)
// Guarda correo + contraseña en localStorage por 1 mes; luego pide volver a ingresarlos.
// IIFE con nombres propios para no chocar con login.js (ámbito global compartido).
(function () {
  'use strict';

  var CLAVE   = 'tc_recordar';
  var MS_MES  = 30 * 24 * 60 * 60 * 1000;   // 1 mes
  var DOMINIO = '@ana-hn.org';

  // Ofuscación simple (NO es cifrado): evita que se lea a simple vista.
  function cifrar(txt) {
    try { return btoa(encodeURIComponent(txt)); } catch (e) { return ''; }
  }
  function descifrar(b64) {
    try { return decodeURIComponent(atob(b64)); } catch (e) { return ''; }
  }
  function leer() {
    try {
      var raw = localStorage.getItem(CLAVE);
      if (!raw) return null;
      var d = JSON.parse(raw);
      if (!d || !d.t || (Date.now() - d.t) > MS_MES) { borrar(); return null; }
      return d;
    } catch (e) { return null; }
  }
  function borrar() {
    try { localStorage.removeItem(CLAVE); } catch (e) {}
  }

  document.addEventListener('DOMContentLoaded', function () {
    var form        = document.getElementById('loginForm');
    var chkRecordar = document.getElementById('rec_recordar');
    var shortInput  = document.getElementById('usernameShort');   // name="username"
    var adminInput  = document.getElementById('usernameAdmin');
    var pwd         = document.getElementById('password');
    var isMaestro   = document.getElementById('is_maestro');
    var toggleBtn   = document.getElementById('toggleAdminMode');
    if (!form || !chkRecordar) return;   // pantalla de bloqueo: no hay formulario

    // ── Restaurar datos guardados ──────────────────────────────────────────
    var d = leer();
    if (d) {
      chkRecordar.checked = true;
      if (isMaestro && typeof d.m === 'boolean') isMaestro.checked = d.m;
      if (pwd) pwd.value = descifrar(d.p || '');

      var usuario = d.u || '';
      if (d.a) {
        // Modo admin: cambiar al campo libre (dispara el handler de login.js)
        if (toggleBtn) toggleBtn.click();
        if (adminInput) adminInput.value = usuario;
      } else if (shortInput) {
        // Modo normal: el campo visible muestra solo la parte corta
        var pos = usuario.indexOf(DOMINIO);
        shortInput.value = pos >= 0 ? usuario.slice(0, pos) : usuario;
      }
    }

    // ── Guardar / borrar al enviar ─────────────────────────────────────────
    // Este listener corre DESPUÉS del de login.js (el script carga después),
    // así que shortInput.value ya trae el correo completo / el usuario admin.
    form.addEventListener('submit', function () {
      if (!chkRecordar.checked) { borrar(); return; }
      var enAdmin = !!(adminInput && adminInput.offsetParent !== null);  // campo admin visible
      try {
        localStorage.setItem(CLAVE, JSON.stringify({
          u: shortInput ? shortInput.value.trim() : '',
          p: cifrar(pwd ? pwd.value : ''),
          m: isMaestro ? isMaestro.checked : false,
          a: enAdmin,
          t: Date.now()
        }));
      } catch (e) {}
    });

    // Si desmarca la casilla, olvidar de inmediato.
    chkRecordar.addEventListener('change', function () {
      if (!chkRecordar.checked) borrar();
    });
  });
})();
