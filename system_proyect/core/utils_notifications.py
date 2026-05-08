# ============================================
#  utils_notifications.py – Notificaciones + Envío de correo
# ============================================

from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from core.models import Notificacion
from threading import Thread
import datetime

_TIPO_COLOR = {
    'info':   '#1971c2',
    'exito':  '#2f9e44',
    'alerta': '#f08c00',
    'error':  '#e03131',
}
_TIPO_ICON = {
    'info':   '🔔',
    'exito':  '✅',
    'alerta': '⚠️',
    'error':  '❌',
}
_MODULO_LABEL = {
    'tickets':       'Soporte Técnico',
    'conducta':      'Conducta',
    'reloj':         'Control de Horario',
    'inventario':    'Inventario',
    'enfermeria':    'Enfermería',
    'seguridad':     'Seguridad',
}


def crear_notificacion(usuario, mensaje, modulo, tipo='info', extra=None, enviar_correo=True):
    if usuario is None:
        return

    Notificacion.objects.create(
        destinatario=usuario,
        mensaje=mensaje,
        modulo=modulo,
        tipo=tipo,
        extra=extra
    )

    if not enviar_correo:
        return

    try:
        nombre     = usuario.first_name or usuario.username
        color      = _TIPO_COLOR.get(tipo, '#1971c2')
        icono      = _TIPO_ICON.get(tipo, '🔔')
        modulo_lbl = _MODULO_LABEL.get(modulo, modulo.capitalize())
        anio       = datetime.datetime.now().year
        asunto     = f"[TechCare] {modulo_lbl} — nueva notificación"

        texto_plano = f"Hola {nombre},\n\n{mensaje}\n\nEste es un aviso automático del sistema TechCare."

        html = f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 0;">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10);">

      <!-- HEADER -->
      <tr>
        <td style="background:linear-gradient(135deg,#1864ab,#228be6);padding:24px 36px;text-align:center;">
          <p style="margin:0 0 2px;font-size:22px;font-weight:700;color:#fff;letter-spacing:-.5px;">TechCare</p>
          <p style="margin:0;font-size:11px;color:rgba(255,255,255,.75);">Soporte Técnico – Asociación Nuevo Amanecer</p>
        </td>
      </tr>

      <!-- MÓDULO BADGE -->
      <tr>
        <td style="padding:24px 36px 8px;text-align:center;">
          <span style="display:inline-block;background:#e7f5ff;color:#1971c2;font-size:12px;
                       font-weight:700;padding:5px 16px;border-radius:20px;letter-spacing:.4px;">
            {modulo_lbl.upper()}
          </span>
        </td>
      </tr>

      <!-- TÍTULO -->
      <tr>
        <td style="padding:8px 36px 20px;text-align:center;">
          <p style="margin:0;font-size:18px;font-weight:700;color:#1a1a2e;">
            {icono} Hola, {nombre}
          </p>
        </td>
      </tr>

      <!-- SEPARADOR -->
      <tr><td style="padding:0 36px;"><hr style="border:none;border-top:1px solid #e9ecef;margin:0;"></td></tr>

      <!-- MENSAJE -->
      <tr>
        <td style="padding:24px 36px;">
          <table width="100%" cellpadding="0" cellspacing="0"
                 style="background:#f8f9fa;border-radius:8px;padding:16px 20px;border-left:4px solid {color};">
            <tr>
              <td style="font-size:14px;color:#1a1a2e;line-height:1.6;">{mensaje}</td>
            </tr>
          </table>
        </td>
      </tr>

      <!-- FOOTER -->
      <tr>
        <td style="background:#f8f9fa;padding:14px 36px;border-top:1px solid #e9ecef;text-align:center;">
          <p style="margin:0 0 2px;font-size:11px;color:#6c757d;">
            Este es un aviso automático del sistema TechCare.
          </p>
          <p style="margin:0;font-size:11px;color:#adb5bd;">© {anio} Asociación Nuevo Amanecer</p>
        </td>
      </tr>

    </table>
  </td></tr>
</table>
</body>
</html>"""

        def _enviar():
            try:
                msg = EmailMultiAlternatives(
                    asunto, texto_plano,
                    settings.DEFAULT_FROM_EMAIL,
                    [usuario.email]
                )
                msg.attach_alternative(html, "text/html")
                msg.send(fail_silently=True)
            except Exception:
                pass

        Thread(target=_enviar, daemon=True).start()

    except Exception:
        pass
