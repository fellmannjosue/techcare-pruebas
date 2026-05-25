document.addEventListener('DOMContentLoaded', function() {

    // ── Ojo contraseña ─────────────────────────────────────────────────────
    const pwdInput = document.getElementById('password');
    const eyeIcon  = document.getElementById('eyeIcon');
    if (pwdInput && eyeIcon) {
        eyeIcon.addEventListener('click', function() {
            if (pwdInput.type === 'password') {
                pwdInput.type = 'text';
                eyeIcon.src = eyeIcon.src.replace('eye_closed.png', 'eye_opened.png');
            } else {
                pwdInput.type = 'password';
                eyeIcon.src = eyeIcon.src.replace('eye_opened.png', 'eye_closed.png');
            }
        });
    }

    // ── Input @ana-hn.org + toggle admin ──────────────────────────────────
    const grupoNormal = document.getElementById('inputGrupoDominio');
    const grupoAdmin  = document.getElementById('inputGrupoAdmin');
    const shortInput  = document.getElementById('usernameShort');
    const adminInput  = document.getElementById('usernameAdmin');
    const hiddenUser  = document.getElementById('username');
    const toggleBtn   = document.getElementById('toggleAdminMode');
    const toggleLabel = document.getElementById('toggleAdminLabel');
    let modoAdmin = false;

    if (toggleBtn) {
        toggleBtn.addEventListener('click', function(e) {
            e.preventDefault();
            modoAdmin = !modoAdmin;
            if (modoAdmin) {
                grupoNormal.style.display = 'none';
                grupoAdmin.style.display  = '';
                toggleLabel.textContent   = 'Modo normal';
                adminInput.focus();
            } else {
                grupoNormal.style.display = '';
                grupoAdmin.style.display  = 'none';
                toggleLabel.textContent   = 'Acceso admin';
                shortInput.focus();
            }
        });
    }

    // ── Submit: armar username real ───────────────────────────────────────
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            // Construir el campo username según el modo
            if (hiddenUser) {
                if (modoAdmin) {
                    hiddenUser.value = (adminInput ? adminInput.value.trim() : '');
                } else {
                    const base = shortInput ? shortInput.value.trim() : '';
                    // Si ya viene con @, no agregar dominio (por si acaso)
                    hiddenUser.value = base.includes('@') ? base : base + '@ana-hn.org';
                }
            }
            const btn = loginForm.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Ingresando…';
            }
        });

        // Enter en shortInput o adminInput activa submit
        [shortInput, adminInput].forEach(inp => {
            if (inp) inp.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') { e.preventDefault(); loginForm.requestSubmit(); }
            });
        });
    }

    // Mostrar hint checkbox si el servidor lo solicita
    const _cfg = document.getElementById('page-config');
    if (_cfg && _cfg.dataset.showCheckboxHint === 'true') {
        mostrarHintCheckbox();
    }
});

function mostrarHintCheckbox() {
    const wrapper  = document.getElementById('checkboxWrapper');
    const hint     = document.getElementById('checkboxHint');
    const checkbox = document.getElementById('is_maestro');
    if (!wrapper || !hint || !checkbox) return;
    wrapper.classList.add('checkbox-highlight');
    wrapper.classList.add('checkbox-shake');
    hint.classList.add('show');
    setTimeout(() => wrapper.classList.remove('checkbox-shake'), 600);
    checkbox.addEventListener('change', function() {
        if (this.checked) {
            hint.classList.remove('show');
            wrapper.classList.remove('checkbox-highlight');
        }
    });
}
