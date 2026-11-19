from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        from django.dispatch import receiver
        from .models import RegistroAcceso

        # <--- hecho por claude code (09-nov-2026): weak=False — al ser una función interna de ready(), con la referencia
        # débil por defecto Python la descartaba y la señal NUNCA registraba nada (solo registraba la vista de login).
        @receiver(user_logged_in, weak=False, dispatch_uid='tc_registro_acceso')
        def registrar_acceso(sender, request, user, **kwargs):
            # <--- hecho por claude code (09-nov-2026): IP = REMOTE_ADDR (sin proxy, X-Forwarded-For lo inventa el cliente).
            # Al "Iniciar sesión como" / "Volver" no se registra un acceso: queda en la bitácora Suplantacion.
            if request is None or getattr(request, '_tc_suplantacion', False):
                return
            from core.seguridad_eventos import ip_cliente
            ip = ip_cliente(request)
            RegistroAcceso.objects.create(
                usuario=user,
                username=user.get_username(),
                ip=ip or None,
                agente=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
