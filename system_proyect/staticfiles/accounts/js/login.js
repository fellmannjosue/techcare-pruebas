document.addEventListener('DOMContentLoaded', function() {
    const pwdInput = document.getElementById('password');
    const eyeIcon = document.getElementById('eyeIcon');
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

    // Desactiva el botón para evitar doble submit
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', function() {
            const btn = loginForm.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = "Ingresando...";
            }
        });
    }

    // Mostrar hint checkbox si el servidor lo solicita
    if (window._PAGE && window._PAGE.showCheckboxHint) {
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
