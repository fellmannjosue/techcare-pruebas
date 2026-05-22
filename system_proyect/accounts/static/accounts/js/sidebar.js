(function () {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  }
  let _prompt = null;
  window.addEventListener('beforeinstallprompt', e => {
    e.preventDefault();
    _prompt = e;
    document.getElementById('pwa-install-item')?.classList.remove('d-none');
  });
  document.getElementById('pwa-install-btn')?.addEventListener('click', async e => {
    e.preventDefault();
    if (!_prompt) return;
    _prompt.prompt();
    const { outcome } = await _prompt.userChoice;
    _prompt = null;
    if (outcome === 'accepted') {
      document.getElementById('pwa-install-item')?.classList.add('d-none');
    }
  });
  window.addEventListener('appinstalled', () => {
    document.getElementById('pwa-install-item')?.classList.add('d-none');
  });
})();
