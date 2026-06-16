document.addEventListener('DOMContentLoaded', function(){
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
