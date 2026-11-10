(function(){
  const _cfg = document.getElementById('user-dropdown-config');
  if (!_cfg) return;

  const URL_REENVIAR  = _cfg.dataset.urlReenviar;
  const URL_USUARIOS  = _cfg.dataset.urlUsuarios;
  const CSRF          = _cfg.dataset.csrf;
  let usuariosCargados = false;

  function getMensaje(){
    const el = document.getElementById('mensajeExtra');
    return el ? el.value.trim() : '';
  }

  async function enviar(email){
    const body = new URLSearchParams({ modo:'uno', email, mensaje_extra: getMensaje() });
    const res  = await fetch(URL_REENVIAR, {
      method:'POST',
      headers:{'X-CSRFToken':CSRF,'Content-Type':'application/x-www-form-urlencoded'},
      body
    });
    return res.json();
  }

  function toast(msg, ok){
    const el = document.createElement('div');
    el.className = `alert alert-${ok?'success':'danger'} alert-dismissible tc-toast-solido`;
    el.style.zIndex = 9999;
    // <--- hecho por claude code (10-nov-2026): fondo SÓLIDO y por encima del botón del asistente, aunque el navegador tenga el CSS viejo en caché
    Object.assign(el.style, {position: 'fixed', right: '16px', bottom: '88px', margin: '0', opacity: '1',
      maxWidth: 'min(420px, calc(100vw - 32px))', background: ok ? '#ebfbee' : '#fff5f5', color: '#1d2433',
      border: '1px solid ' + (ok ? '#b2f2bb' : '#ffc9c9'), borderLeft: '5px solid ' + (ok ? '#2fb344' : '#d63939'),
      borderRadius: '10px', boxShadow: '0 10px 28px rgba(15,23,42,.25)', fontWeight: '600', backdropFilter: 'none'});
    el.innerHTML = `<i class="ti ti-${ok?'check':'x'} me-1"></i>${msg}<button class="btn-close" data-bs-dismiss="alert"></button>`;
    document.body.appendChild(el);
    setTimeout(()=>el.remove(), 4000);
  }

  function actualizarContador(){
    const n = document.querySelectorAll('#tbodyUsuarios .chk-usuario:checked').length;
    document.getElementById('contadorSel').textContent = n + ' seleccionados';
  }

  function renderFilas(usuarios){
    const tbody = document.getElementById('tbodyUsuarios');
    tbody.innerHTML = usuarios.map(u => `
      <tr class="fila-usuario" data-nombre="${u.nombre.toLowerCase()}" data-email="${u.email.toLowerCase()}">
        <td><input type="checkbox" class="chk-usuario" value="${u.email}"></td>
        <td>${u.nombre}</td>
        <td class="text-muted small">${u.email}</td>
        <td>
          <button type="button" class="btn btn-sm btn-ghost-primary btn-enviar-uno"
                  data-email="${u.email}" data-nombre="${u.nombre}">
            <i class="ti ti-send me-1"></i>Enviar
          </button>
        </td>
      </tr>`).join('');

    tbody.querySelectorAll('.chk-usuario').forEach(c => c.addEventListener('change', actualizarContador));
    tbody.querySelectorAll('.btn-enviar-uno').forEach(btn => {
      btn.addEventListener('click', async function(){
        const email  = this.dataset.email;
        const nombre = this.dataset.nombre;
        this.disabled = true;
        this.innerHTML = '<span class="spinner-border spinner-border-sm"></span>';
        const data = await enviar(email);
        this.disabled = false;
        this.innerHTML = '<i class="ti ti-send me-1"></i>Enviar';
        toast(data.ok ? `Correo enviado a ${nombre}` : `Error: ${data.error||'desconocido'}`, data.ok);
      });
    });
  }

  async function cargarUsuarios(){
    if (usuariosCargados) return;
    try {
      const res  = await fetch(URL_USUARIOS);
      const data = await res.json();
      if (data.ok) { renderFilas(data.usuarios); usuariosCargados = true; }
    } catch(e) {
      document.getElementById('tbodyUsuarios').innerHTML =
        '<tr><td colspan="4" class="text-center text-danger py-3">Error al cargar usuarios.</td></tr>';
    }
  }

  document.addEventListener('DOMContentLoaded', function(){
    const btnAbrir = document.getElementById('btnAbrirReenviar');
    if (!btnAbrir) return;

    // Mover el modal al body para que no quede atrapado dentro del sidebar
    const modalEl = document.getElementById('modalReenviarBienvenida');
    document.body.appendChild(modalEl);
    const modal = new bootstrap.Modal(modalEl);

    btnAbrir.addEventListener('click', function(e){
      e.preventDefault();
      modal.show();
      cargarUsuarios();
    });

    document.getElementById('buscadorUsuarios').addEventListener('input', function(){
      const q = this.value.toLowerCase();
      document.querySelectorAll('#tbodyUsuarios .fila-usuario').forEach(tr => {
        tr.style.display = (tr.dataset.nombre.includes(q)||tr.dataset.email.includes(q)) ? '' : 'none';
      });
    });

    document.getElementById('btnSelTodos').addEventListener('click', ()=>{
      document.querySelectorAll('#tbodyUsuarios .fila-usuario:not([style*="none"]) .chk-usuario')
              .forEach(c=>c.checked=true);
      document.getElementById('chkTodosHeader').checked = true;
      actualizarContador();
    });

    document.getElementById('btnDeselTodos').addEventListener('click', ()=>{
      document.querySelectorAll('#tbodyUsuarios .chk-usuario').forEach(c=>c.checked=false);
      document.getElementById('chkTodosHeader').checked = false;
      actualizarContador();
    });

    document.getElementById('chkTodosHeader').addEventListener('change', function(){
      document.querySelectorAll('#tbodyUsuarios .fila-usuario:not([style*="none"]) .chk-usuario')
              .forEach(c=>c.checked=this.checked);
      actualizarContador();
    });

    document.getElementById('btnEnviarSeleccionados').addEventListener('click', async function(){
      const seleccionados = [...document.querySelectorAll('#tbodyUsuarios .chk-usuario:checked')].map(c=>c.value);
      if (!seleccionados.length){ toast('Selecciona al menos un usuario.', false); return; }
      this.disabled = true;
      this.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Enviando...';
      let ok=0, err=0;
      for (const email of seleccionados){
        const data = await enviar(email);
        data.ok ? ok++ : err++;
      }
      this.disabled = false;
      this.innerHTML = '<i class="ti ti-mail me-1"></i>Enviar a seleccionados';
      toast(`Enviados: ${ok}${err?` | Errores: ${err}`:''}`, err===0);
    });
  });
})();
