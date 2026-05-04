from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in
        from django.dispatch import receiver
        from .models import RegistroAcceso

        @receiver(user_logged_in)
        def registrar_acceso(sender, request, user, **kwargs):
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
            )
            RegistroAcceso.objects.create(
                usuario=user,
                username=user.get_username(),
                ip=ip or None,
                agente=request.META.get('HTTP_USER_AGENT', '')[:500],
            )
