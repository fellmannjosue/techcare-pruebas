# <--- hecho por claude code: crea los grupos de permisos de Salidas Baño
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

from salidas_bano.views import AMBITOS


class Command(BaseCommand):
    help = 'Crea los grupos de acceso de Salidas al Baño (Colegio y CFP)'

    def handle(self, *args, **options):
        # <--- hecho por claude code: antes creaba 'salidas_maestro'/'salidas_coordinador',
        # que NO son los grupos que el módulo consulta. Ahora salen de AMBITOS.
        for ambito, cfg in AMBITOS.items():
            self.stdout.write(f'\n{cfg["label"]}:')
            for nombre in (cfg['grp_maestro'], cfg['grp_coord']):
                _, creado = Group.objects.get_or_create(name=nombre)
                self.stdout.write(f'  Grupo "{nombre}" — {"creado ✓" if creado else "ya existía"}')
        self.stdout.write(self.style.SUCCESS(
            '\nListo. Asigna usuarios desde /admin/auth/user/ o /admin/auth/group/'
        ))
