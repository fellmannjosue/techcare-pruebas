# <--- hecho por claude code (19-oct-2026): aviso diario del MANTENIMIENTO DEL TANQUE (cron de admin2).
# Avisa por la campana al grupo mantenimiento_mecanico_alertas cuando la limpieza está a 15 días o menos, toca hoy o
# está vencida; una sola vez por etapa (Insumo.aviso_limpieza).
from django.core.management.base import BaseCommand
from django.urls import reverse

from mantenimiento_mecanico import services
from mantenimiento_mecanico.models import Insumo


class Command(BaseCommand):
    help = 'Avisa por la campana cuando la limpieza del tanque está próxima o vencida.'

    def handle(self, *args, **opts):
        for ins in Insumo.objects.filter(activo=True, presentacion='tanque'):
            e = services.estado_limpieza(ins)
            n = services.avisar_limpieza(ins, url=reverse('mantenimiento_mecanico:pagina', args=[ins.clave]))
            self.stdout.write(f'{ins.nombre}: próxima limpieza {e["proxima"]:%d/%m/%Y} ({e["texto"]}) · avisos enviados: {n}')
