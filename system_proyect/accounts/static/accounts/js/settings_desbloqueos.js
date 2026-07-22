/* <--- hecho por claude code: extraído del template. Las URLs de Django
   llegan por data-* en #settings_desbloqueos-config (un .js no procesa Django). */
const CFG = (function(){
  var d = document.getElementById("settings_desbloqueos-config").dataset;
  return {
    desbloquearUsuario: d.desbloquearUsuario,
    csrf: d.csrf || "",
  };
})();

(function () {
  var CSRF = document.querySelector('[name=csrfmiddlewaretoken]')?.value
             || document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  document.querySelectorAll('.btn-desbloquear').forEach(function (btn) {
    btn.addEventListener('click', function () {
      if (!confirm('¿Desbloquear el acceso de ' + this.dataset.nombre + '?')) return;
      var uid = this.dataset.user, b = this;
      b.disabled = true;
      fetch(CFG.desbloquearUsuario, {
        method: 'POST',
        headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': CSRF},
        body: 'user_id=' + encodeURIComponent(uid),
      }).then(function (r) { return r.json(); }).then(function (d) {
        if (d.ok) { var tr = b.closest('tr'); if (tr) tr.remove(); }
        else { alert(d.error || 'Error'); b.disabled = false; }
      }).catch(function () { alert('Error de red'); b.disabled = false; });
    });
  });
})();
