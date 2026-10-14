document.addEventListener('DOMContentLoaded', function(){
  // <--- hecho por claude code: pausar/reanudar SLA (En espera del usuario) ─────────────
  (function(){
    const path = location.pathname.match(/\/tickets\/ticket\/(\d+)\/comentarios/);
    const ticketId = path ? path[1] : null;
    const csrf = document.querySelector('#form-status-ticket [name=csrfmiddlewaretoken]')?.value || '';
    const statusSelect = document.getElementById('chat-status-select');
    function post(url, data){
      return fetch(url, { method:'POST', headers:{'X-CSRFToken':csrf,'X-Requested-With':'XMLHttpRequest'}, body:new URLSearchParams(data||{}) }).then(r=>r.json());
    }
    // El select "En espera del usuario" abre el modal (motivo obligatorio)
    statusSelect?.addEventListener('change', function(){
      if (this.value === 'En espera del usuario') {
        const m = document.getElementById('modalPonerEspera');
        if (m) new bootstrap.Modal(m).show();
      }
    });
    // Botón directo "Poner en espera del usuario"
    document.getElementById('btn-poner-espera')?.addEventListener('click', function(){
      const m = document.getElementById('modalPonerEspera');
      if (m) new bootstrap.Modal(m).show();
    });
    // Prellenar motivo desde el combo de motivos comunes
    document.getElementById('esp-motivo-pre')?.addEventListener('change', function(){
      if (this.value) document.getElementById('esp-motivo').value = this.value;
    });
    // Confirmar la pausa
    document.getElementById('btn-esp-confirmar')?.addEventListener('click', async function(){
      const motivo = document.getElementById('esp-motivo').value.trim();
      const info = document.getElementById('esp-info').value.trim();
      const err = document.getElementById('esp-error');
      if (!motivo || !info){ err.textContent = 'El motivo y la información requerida son obligatorios.'; err.classList.remove('d-none'); return; }
      err.classList.add('d-none'); this.disabled = true;
      const d = await post(`/tickets/ticket/${ticketId}/poner-espera/`, { motivo, info_requerida: info });
      this.disabled = false;
      if (d.ok){ location.reload(); }
      else { err.textContent = d.error || 'No se pudo poner en espera.'; err.classList.remove('d-none'); }
    });
    // Botón "Reanudar atención"
    document.getElementById('btn-reanudar')?.addEventListener('click', async function(){
      this.disabled = true;
      const d = await post(`/tickets/ticket/${ticketId}/reanudar/`, {});
      if (d.ok){ location.reload(); } else { this.disabled = false; alert(d.error || 'No se pudo reanudar.'); }
    });
    // Refrescar el panel del SLA cada 8s (estado/restante/pausa)
    function refrescarSla(){
      if (!ticketId) return;
      fetch(`/tickets/ticket_status_get_ajax/${ticketId}/`).then(r=>r.json()).then(res=>{
        const badge = document.getElementById('sla-badge');
        const info = document.getElementById('sla-pausa-info');
        if (badge){
          badge.className = 'badge ' + (res.sla_estado==='pausado'?'bg-orange-lt text-orange':res.sla_estado==='vencido'?'bg-red-lt text-red':res.sla_estado==='por_vencer'?'bg-yellow-lt text-yellow':'bg-green-lt text-green');
          badge.innerHTML = (res.sla_estado==='pausado'?'<i class="ti ti-player-pause me-1"></i>':'') + (res.sla_texto||'');
        }
        if (info){
          if (res.sla_pausado){ info.classList.remove('d-none'); info.innerHTML = '<i class="ti ti-info-circle me-1"></i>Desde '+res.pausa_desde+' · '+res.pausa_motivo; }
          else info.classList.add('d-none');
        }
        const fh = document.getElementById('sla-fuera-horario');
        if (fh){
          if (res.fuera_horario){ fh.classList.remove('d-none'); fh.innerHTML = '<i class="ti ti-moon me-1"></i>'+(res.fuera_horario_texto||'Fuera de horario laboral'); }
          else fh.classList.add('d-none');
        }
      }).catch(()=>{});
    }
    setInterval(refrescarSla, 8000);
  })();

  // Búsqueda en sidebar
  document.getElementById('searchTickets')?.addEventListener('input', function(){
    const q = this.value.toLowerCase();
    document.querySelectorAll('#ticketList .ticket-item').forEach(el => {
      el.style.display = el.dataset.search.includes(q) ? '' : 'none';
    });
  });

  // Toast + sonido si viene de crear ticket
  if (localStorage.getItem('ticketCreado')) {
    localStorage.removeItem('ticketCreado');
    const toastEl = document.getElementById('toastNuevoTicket');
    if (toastEl) new bootstrap.Toast(toastEl, { delay: 5000 }).show();
    const audio = document.getElementById('notifSound');
    if (audio) { try { audio.volume = 0.6; audio.play().catch(function(){}); } catch(e){} }
  }
});
