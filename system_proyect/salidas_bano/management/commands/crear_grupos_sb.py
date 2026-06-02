# <--- hecho por claude code: crea grupos de permisos para Salidas Baño
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group


class Command(BaseCommand):
    help = 'Crea los grupos salidas_maestro y salidas_coordinador'

    def handle(self, *args, **options):
        for nombre in ['salidas_maestro', 'salidas_coordinador']:
            grupo, created = Group.objects.get_or_create(name=nombre)
            estado = 'creado ✓' if created else 'ya existía'
            self.stdout.write(f'  Grupo "{nombre}" — {estado}')
        self.stdout.write(self.style.SUCCESS(
            '\nListo. Asigna usuarios desde /admin/auth/user/ o /admin/auth/group/'
        ))
