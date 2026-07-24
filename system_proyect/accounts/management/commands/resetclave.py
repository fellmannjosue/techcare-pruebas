# accounts/management/commands/resetclave.py
# <--- hecho por claude code: cambiar la clave de un usuario y quitarle el bloqueo de login
# desde la terminal, sin necesidad de entrar al sistema.
import getpass

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.management.base import BaseCommand, CommandError

User = get_user_model()


class Command(BaseCommand):
    help = ('Cambia la contraseña de un usuario y le limpia el bloqueo por intentos '
            'fallidos de login. Sin --clave, la pide por teclado (no se ve al escribir).')

    def add_arguments(self, parser):
        parser.add_argument('usuario', help='Username o correo del usuario')
        parser.add_argument('--clave', default=None,
                            help='Nueva contraseña. Si se omite, se pide por teclado.')
        parser.add_argument('--solo-desbloquear', action='store_true',
                            help='No cambia la contraseña, solo quita el bloqueo.')

    def handle(self, *args, **opts):
        ident = (opts['usuario'] or '').strip()
        u = (User.objects.filter(username__iexact=ident).first()
             or User.objects.filter(email__iexact=ident).first())
        if not u:
            raise CommandError(f'No existe ningún usuario con username o correo "{ident}".')

        # ── Quitar el bloqueo (perfil + contadores en cache) ──
        try:
            p = u.perfil
            if p.login_bloqueado:
                p.login_bloqueado = False
                p.login_bloqueado_en = None
                p.save(update_fields=['login_bloqueado', 'login_bloqueado_en'])
                self.stdout.write(self.style.SUCCESS('  · bloqueo de acceso retirado'))
        except Exception:
            pass
        for k in (u.username, u.email, ident):
            clave = (k or '').strip().lower()
            if clave:
                cache.delete('login_fails:' + clave)
                cache.delete('login_lock:' + clave)
        self.stdout.write(self.style.SUCCESS('  · intentos fallidos reiniciados'))

        if not u.is_active:
            u.is_active = True
            u.save(update_fields=['is_active'])
            self.stdout.write(self.style.SUCCESS('  · cuenta reactivada'))

        if opts['solo_desbloquear']:
            self.stdout.write(self.style.SUCCESS(f'\nListo: {u.username} desbloqueado.'))
            return

        # ── Contraseña nueva ──
        nueva = opts['clave']
        if not nueva:
            nueva = getpass.getpass(f'Nueva contraseña para {u.username}: ')
            if nueva != getpass.getpass('Repetir contraseña: '):
                raise CommandError('Las contraseñas no coinciden.')
        if not nueva:
            raise CommandError('La contraseña no puede estar vacía.')

        u.set_password(nueva)
        u.save()
        self.stdout.write(self.style.SUCCESS(
            f'\nListo: contraseña de {u.username} cambiada y cuenta desbloqueada.'))
