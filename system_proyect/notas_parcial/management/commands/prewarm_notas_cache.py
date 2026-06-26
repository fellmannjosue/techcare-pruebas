"""Pre-carga (calienta) el cache de Notas Mitad de Parcial.

Refresca el cache de los (área, parcial, año) que tienen maestros asignados,
para que los coordinadores/maestros nunca caigan en la consulta lenta del SP.
Pensado para correr por cron cada pocas horas.
"""
from django.core.management.base import BaseCommand
from django.core.cache import cache
from notas_parcial.models import AsignacionMaestro
from notas_parcial import views as nv


class Command(BaseCommand):
    help = "Pre-carga el cache de Notas Mitad de Parcial para las asignaciones activas."

    def handle(self, *args, **opts):
        combos = set(
            AsignacionMaestro.objects.values_list('area', 'parcial', 'anio').distinct()
        )
        if not combos:
            self.stdout.write("Sin asignaciones; nada que pre-cargar.")
            return

        ok = 0
        for area, parcial, anio in sorted(combos):
            cursos = (['1', '2'] if nv.SP_MAP.get(area, ('', False))[1] else [None])
            for curso in cursos:
                try:
                    cache.delete(nv._cache_key(area, parcial, anio, curso))  # forzar refresco
                    rows, _ = nv._llamar_sp(area, parcial, anio, curso)
                    n = len(rows or [])
                    ok += 1
                    self.stdout.write(f"OK {area} P{parcial}/{anio}"
                                      + (f" curso {curso}" if curso else "")
                                      + f" → {n} filas")
                except Exception as e:
                    self.stderr.write(f"ERROR {area} P{parcial}/{anio}: {e}")
        self.stdout.write(self.style.SUCCESS(f"Pre-carga completada: {ok} combinación(es)."))
