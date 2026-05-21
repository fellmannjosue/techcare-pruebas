from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()

USUARIOS = ['jzelaya@ana-hn.org', 'llopez@ana-hn.org']


class Command(BaseCommand):
    help = 'Crea el grupo solo_progress y asigna a jzelaya y llopez'

    def handle(self, *args, **options):
        grupo, created = Group.objects.get_or_create(name='solo_progress')
        if created:
            self.stdout.write(self.style.SUCCESS('Grupo "solo_progress" creado.'))
        else:
            self.stdout.write('Grupo "solo_progress" ya existía.')

        for email in USUARIOS:
            try:
                user = User.objects.get(username=email)
                grupos_anteriores = list(user.groups.values_list('name', flat=True))
                user.groups.clear()
                user.groups.add(grupo)
                user.is_staff = False
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f'{email}: grupos {grupos_anteriores} → [solo_progress]'
                    )
                )
            except User.DoesNotExist:
                self.stdout.write(self.style.WARNING(f'{email}: usuario no encontrado.'))
