from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand

from notas_parcial.models import AsignacionMaestro, NotaComentario


class Command(BaseCommand):
    help = 'Crea los grupos coord_notas_parcial y maestros_notas_parcial con sus permisos.'

    def handle(self, *args, **options):
        ct_asig = ContentType.objects.get_for_model(AsignacionMaestro)
        ct_com  = ContentType.objects.get_for_model(NotaComentario)

        # Permisos de AsignacionMaestro
        p_asig_view   = Permission.objects.get(codename='view_asignacionmaestro',   content_type=ct_asig)
        p_asig_add    = Permission.objects.get(codename='add_asignacionmaestro',    content_type=ct_asig)
        p_asig_change = Permission.objects.get(codename='change_asignacionmaestro', content_type=ct_asig)
        p_asig_delete = Permission.objects.get(codename='delete_asignacionmaestro', content_type=ct_asig)

        # Permisos de NotaComentario
        p_com_view   = Permission.objects.get(codename='view_notacomentario',   content_type=ct_com)
        p_com_add    = Permission.objects.get(codename='add_notacomentario',    content_type=ct_com)
        p_com_change = Permission.objects.get(codename='change_notacomentario', content_type=ct_com)
        p_com_delete = Permission.objects.get(codename='delete_notacomentario', content_type=ct_com)

        # ── Grupo Coordinador ──────────────────────────────────────────────
        coord_group, created = Group.objects.get_or_create(name='coord_notas_parcial')
        coord_group.permissions.set([
            p_asig_view, p_asig_add, p_asig_change, p_asig_delete,
            p_com_view,  p_com_add,  p_com_change,  p_com_delete,
        ])
        estado = 'creado' if created else 'actualizado'
        self.stdout.write(self.style.SUCCESS(f'Grupo "coord_notas_parcial" {estado}.'))

        # ── Grupo Maestro ──────────────────────────────────────────────────
        maestro_group, created = Group.objects.get_or_create(name='maestros_notas_parcial')
        maestro_group.permissions.set([
            p_asig_view,
            p_com_view, p_com_add, p_com_change,
        ])
        estado = 'creado' if created else 'actualizado'
        self.stdout.write(self.style.SUCCESS(f'Grupo "maestros_notas_parcial" {estado}.'))

        self.stdout.write(self.style.SUCCESS('Listo. Asigna los grupos a los usuarios desde Settings > Usuarios.'))
