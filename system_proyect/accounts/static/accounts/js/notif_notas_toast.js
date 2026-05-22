(function(){
  if (typeof window._NOTIF_NOTAS === 'undefined') return;

  const URL_NOTIF = window._NOTIF_NOTAS.urlNotif;
  const URL_LEER  = window._NOTIF_NOTAS.urlLeer;
  const URL_COORD = window._NOTIF_NOTAS.urlCoord;
  const CSRF      = window._NOTIF_NOTAS.csrf;
  const seen      = new Set();

  async function checkNotifs(){
    try {
      const res = await fetch(URL_NOTIF);
      if(!res.ok) return;
      const json = await res.json();
      for(const n of json.notificaciones){
        if(seen.has(n.pk)) continue;
        seen.add(n.pk);
        mostrarToast(n);
      }
    } catch(e){}
  }

  function mostrarToast(n){
    const container = document.getElementById('tc-notif-global');
    if(!container) return;

    let coordUrl = `${URL_COORD}?parcial=${n.parcial}&anio=${n.anio}&area=${encodeURIComponent(n.area)}`;
    if(n.grado)   coordUrl += `&grado=${encodeURIComponent(n.grado)}`;
    if(n.seccion) coordUrl += `&seccion=${encodeURIComponent(n.seccion)}`;

    const el = document.createElement('div');
    el.className = 'toast show';
    el.setAttribute('role', 'alert');
    el.setAttribute('aria-live', 'assertive');
    el.style.minWidth = '320px';
    el.innerHTML = `
      <div class="toast-header">
        <span class="avatar avatar-xs me-2 rounded bg-blue-lt text-blue"
              style="font-size:.85rem;width:24px;height:24px;display:inline-flex;align-items:center;justify-content:center;">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12 3L2 9l10 6 10-6-10-6z"/>
            <path d="M2 17l10 6 10-6"/>
            <path d="M2 13l10 6 10-6"/>
          </svg>
        </span>
        <strong class="me-auto">${n.maestro}</strong>
        <small class="text-muted ms-2">${n.fecha}</small>
        <button type="button" class="btn-close ms-2" aria-label="Cerrar"></button>
      </div>
      <div class="toast-body">
        <i class="ti ti-clipboard-check text-success me-1"></i>
        Ha finalizado de ingresar comentarios a los reportes de
        <strong>${n.area_label} — Parcial ${n.parcial}/${n.anio}</strong>
        — Grado <strong>${n.grado}${n.seccion ? ' ' + n.seccion : ''}</strong>.
        <div class="mt-2 pt-2 border-top">
          <button type="button" class="btn btn-primary btn-sm btn-entendido">
            Entendido
          </button>
        </div>
      </div>`;

    el.querySelector('.btn-close').addEventListener('click', () => el.remove());

    el.querySelector('.btn-entendido').addEventListener('click', async function(){
      this.disabled = true;
      this.textContent = '…';
      try {
        await fetch(URL_LEER, {
          method: 'POST',
          headers: {'X-CSRFToken': CSRF, 'Content-Type': 'application/json'},
          body: JSON.stringify({pk: n.pk}),
        });
      } catch(e){}
      el.remove();
      window.location.href = coordUrl;
    });

    container.appendChild(el);
  }

  checkNotifs();
  setInterval(checkNotifs, 25000);
})();
