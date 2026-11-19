# accounts/recuperacion.py
# <--- hecho por claude code (09-nov-2026, revisión ISO 27001 · autenticación segura): recuperación de contraseña con límite.
"""Vistas de recuperación de contraseña de Django con dos agregados:

1. Límite de solicitudes: 3 por correo por hora y, desde IPs públicas, 10 por IP por hora.
   Antes se podía inundar el buzón de una persona y gastar la cuota del SMTP. Al pasarse del límite
   la pantalla responde IGUAL que siempre ("revisa tu correo"), así no revela si el correo existe.
2. Bitácora: solicitud, solicitud limitada y contraseña restablecida (sin el correo completo ni el token).
"""
import ipaddress

from django.contrib.auth import views as auth_views
from django.core.cache import cache
from django.shortcuts import redirect

from core.seguridad_eventos import evento, ip_cliente

LIMITE_POR_CORREO = 3
LIMITE_POR_IP = 10
VENTANA = 60 * 60


def _contar(clave, limite):
    n = (cache.get(clave, 0) or 0) + 1
    cache.set(clave, n, VENTANA)
    return n > limite


def _ip_publica(request):
    try:
        ip = ipaddress.ip_address(ip_cliente(request) or '')
        return not (ip.is_private or ip.is_loopback)
    except ValueError:
        return False


def _correo_oculto(correo):
    usuario, _, dominio = (correo or '').partition('@')
    return (usuario[:2] + '***@' + dominio) if dominio else '***'


class PasswordResetLimitadoView(auth_views.PasswordResetView):
    def form_valid(self, form):
        correo = (form.cleaned_data.get('email') or '').strip().lower()
        excedido = _contar('pwreset_mail:' + correo, LIMITE_POR_CORREO)
        if _ip_publica(self.request):
            excedido = _contar('pwreset_ip:' + (ip_cliente(self.request) or ''), LIMITE_POR_IP) or excedido
        if excedido:
            evento('recuperacion_limitada', self.request, objetivo=_correo_oculto(correo))
            return redirect(self.get_success_url())   # misma respuesta: no revela nada
        evento('recuperacion_solicitada', self.request, objetivo=_correo_oculto(correo))
        return super().form_valid(form)


class PasswordResetConfirmRegistradoView(auth_views.PasswordResetConfirmView):
    def form_valid(self, form):
        resp = super().form_valid(form)
        evento('recuperacion_completada', self.request, objetivo=getattr(self, 'user', None))
        return resp
