# <--- hecho por claude code: monitoreo continuo de conectividad (Fase 4).
# Pensado para cron: hace ping a todos los dispositivos/switches con IP, guarda estado/latencia
# y NOTIFICA (campana + correo) a los superusuarios y al grupo red_admin cuando un equipo
# pasa de "en línea" a "caído" (solo en la transición, para no spamear). También avisa cuando vuelve.
#   ../venv/bin/python manage.py ping_red            # corre una pasada
#   ../venv/bin/python manage.py ping_red --silencioso   # sin notificaciones (solo actualiza)
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from red.models import Device, Switch
from red import services


class Command(BaseCommand):
    help = 'Ping a todos los equipos de red con IP; guarda estado y notifica caídas/recuperaciones.'

    def add_arguments(self, parser):
        parser.add_argument('--silencioso', action='store_true', help='No enviar notificaciones.')
        parser.add_argument('--timeout', type=int, default=1, help='Timeout del ping en segundos.')

    def _destinatarios(self):
        qs = User.objects.filter(is_active=True).filter(
            models_q_super_o_admin()).distinct()
        return list(qs)

    def _probar(self, obj, ip, manager, etiqueta, timeout, avisos):
        antes = obj.conectividad
        ok, lat = services.ping_host(ip, timeout=timeout)
        estado = 'ok' if ok else 'caido'
        manager.filter(pk=obj.pk).update(conectividad=estado, latencia_ms=lat, probado_en=timezone.now())
        # Solo avisar en TRANSICIÓN (ok→caido o caido→ok); "desconocido" inicial no avisa caída falsa
        if antes == 'ok' and estado == 'caido':
            avisos.append(('caida', f'{etiqueta} {obj.nombre} ({ip}) NO responde al ping.'))
        elif antes == 'caido' and estado == 'ok':
            avisos.append(('recuperado', f'{etiqueta} {obj.nombre} ({ip}) volvió a responder ({lat} ms).'))
        return estado

    def handle(self, *args, **opts):
        timeout = opts['timeout']
        avisos, resumen = [], {'ok': 0, 'caido': 0}
        for d in Device.objects.exclude(ip__isnull=True):
            resumen[self._probar(d, d.ip, Device.objects, 'Dispositivo', timeout, avisos)] += 1
        for s in Switch.objects.exclude(ip_admin__isnull=True):
            resumen[self._probar(s, s.ip_admin, Switch.objects, 'Switch', timeout, avisos)] += 1

        self.stdout.write(f"ping_red: en línea={resumen['ok']} caídos={resumen['caido']} avisos={len(avisos)}")
        if avisos and not opts['silencioso']:
            from core.utils_notifications import crear_notificacion
            for u in self._destinatarios():
                for tipo, msg in avisos:
                    crear_notificacion(u, msg, modulo='red',
                                       tipo=('error' if tipo == 'caida' else 'success'))
        for tipo, msg in avisos:
            self.stdout.write(f'  [{tipo}] {msg}')


def models_q_super_o_admin():
    from django.db.models import Q
    return Q(is_superuser=True) | Q(groups__name='red_admin')
