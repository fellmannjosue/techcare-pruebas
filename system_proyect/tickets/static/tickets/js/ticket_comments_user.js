// Botón Historial: usa history.back() si hay historial, sino url del enlace
(function(){
  var btn = document.getElementById('btn-historial');
  if (btn && window.history.length > 1) {
    btn.addEventListener('click', function(e){
      e.preventDefault();
      history.back();
    });
  }
})();

document.addEventListener('DOMContentLoaded', function(){
  // Búsqueda en sidebar
  document.getElementById('searchTickets')?.addEventListener('input', function(){
    const q = this.value.toLowerCase();
    document.querySelectorAll('#ticketList .ticket-item').forEach(el => {
      el.style.display = el.dataset.search.includes(q) ? '' : 'none';
    });
  });

  // Toast si viene de crear ticket
  if (localStorage.getItem('ticketCreado')) {
    localStorage.removeItem('ticketCreado');
    const toastEl = document.getElementById('toastNuevoTicket');
    if (toastEl) new bootstrap.Toast(toastEl, { delay: 5000 }).show();
  }
});
