document.addEventListener('DOMContentLoaded', function() {

    // ── Ojo contraseña ─────────────────────────────────────────────────────
    const pwdInput = document.getElementById('password');
    const eyeBtn   = document.getElementById('eyeBtn');
    const eyeIcon  = document.getElementById('eyeIcon');
    if (pwdInput && eyeBtn) {
        eyeBtn.addEventListener('click', function () {
            if (pwdInput.type === 'password') {
                pwdInput.type = 'text';
                eyeIcon.classList.replace('ti-eye-off', 'ti-eye');
            } else {
                pwdInput.type = 'password';
                eyeIcon.classList.replace('ti-eye', 'ti-eye-off');
            }
        });
    }

    // ── Input @ana-hn.org + toggle admin ──────────────────────────────────
    const grupoNormal = document.getElementById('inputGrupoDominio');
    const grupoAdmin  = document.getElementById('inputGrupoAdmin');
    const shortInput  = document.getElementById('usernameShort');   // name="username"
    const adminInput  = document.getElementById('usernameAdmin');
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
    // shortInput tiene name="username" → Django lo recibe directamente.
    // Solo necesitamos ajustar el valor antes de enviar.
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function(e) {
            if (modoAdmin) {
                // En modo admin se usa el campo libre; copia su valor a shortInput
                if (shortInput && adminInput) {
                    shortInput.value = adminInput.value.trim();
                }
            } else {
                // Modo normal: agregar @ana-hn.org si el gestor de contraseñas
                // llenó solo la parte corta (Dashlane puede llenar ambas formas)
                if (shortInput) {
                    const base = shortInput.value.trim();
                    shortInput.value = base.includes('@') ? base : base + '@ana-hn.org';
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
