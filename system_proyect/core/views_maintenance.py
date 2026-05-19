import json
import datetime as dt
from threading import Thread

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.core.mail import EmailMultiAlternatives
from django.conf import settings

User = get_user_model()

_AREA_GROUPS = {
    'bilingue': ('maestros_bilingue',),
    'colegio':  ('maestros_colegio',),
}
_AREA_LABELS = {
    'bilingue': 'Bilingüe',
    'colegio':  'Colegio',
    'all':      'Todas las áreas',
    'staff':    'Staff',
}


def _usuarios_area(area):
    qs = User.objects.filter(is_active=True).exclude(email='').exclude(is_superuser=True)
    if area == 'staff':
        return qs.filter(is_staff=True)
    elif area == 'all':
        return qs.filter(is_staff=False)
    else:
        grupos = _AREA_GROUPS.get(area, ())
        if grupos:
            return qs.filter(groups__name__in=grupos).distinct()
    return qs


def _html_correo(icono, titulo, color, parrafos_html):
    year = dt.datetime.now().year
    cuerpo = ''.join(
        f'<p style="font-size:14px;color:#495057;margin:0 0 10px;">{p}</p>'
        for p in parrafos_html
    )
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f0f4f8;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#f0f4f8;padding:32px 0;">
  <tr><td align="center">
    <table width="520" cellpadding="0" cellspacing="0"
           style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.10);">
      <tr>
        <td style="background:linear-gradient(135deg,{color},{color}bb);padding:24px 36px;text-align:center;">
          <p style="margin:0 0 2px;font-size:22px;font-weight:700;color:#fff;letter-spacing:-.5px;">TechCare</p>
          <p style="margin:0;font-size:11px;color:rgba(255,255,255,.75);">Soporte Técnico – Asociación Nuevo Amanecer</p>
        </td>
      </tr>
      <tr>
        <td style="padding:28px 36px 8px;text-align:center;">
          <p style="margin:0;font-size:36px;">{icono}</p>
          <p style="margin:8px 0 0;font-size:20px;font-weight:700;color:#1a1a2e;">{titulo}</p>
        </td>
      </tr>
      <tr><td style="padding:20px 36px;">{cuerpo}</td></tr>
      <tr>
        <td style="background:#f8f9fa;padding:14px 36px;border-top:1px solid #e9ecef;text-align:center;">
          <p style="margin:0;font-size:11px;color:#adb5bd;">© {year} Asociación Nuevo Amanecer</p>
        </td>
      </tr>
    </table>
  </td></tr>
</table>
</body>
</html>"""


def _enviar_async(usuarios_qs, asunto, html, texto):
    lista = list(usuarios_qs.values_list('email', flat=True))

    def _send():
        for email in lista:
            try:
                msg = EmailMultiAlternatives(asunto, texto, settings.DEFAULT_FROM_EMAIL, [email])
                msg.attach_alternative(html, 'text/html')
                msg.send(fail_silently=True)
            except Exception:
                pass

    Thread(target=_send, daemon=True).start()


def enviar_correo_inicio(area, mensaje, end_time_str):
    area_label = _AREA_LABELS.get(area, area)
    fin_info = ''
    fin_texto = ''
    if end_time_str:
        try:
            end_dt = dt.datetime.fromisoformat(end_time_str)
            fin_info = f'<strong>Duración estimada:</strong> hasta las {end_dt.strftime("%H:%M")} del {end_dt.strftime("%d/%m/%Y")}.'
            fin_texto = f'\nDuración estimada: hasta las {end_dt.strftime("%H:%M")} del {end_dt.strftime("%d/%m/%Y")}.'
        except ValueError:
            pass

    parrafos = [
        f'El sistema TechCare (<strong>{area_label}</strong>) estará temporalmente en mantenimiento.',
        mensaje,
    ]
    if fin_info:
        parrafos.append(fin_info)
    parrafos.append('Recibirás otro correo cuando el sistema esté disponible nuevamente.')

    html  = _html_correo('🔧', 'Sistema en Mantenimiento', '#f59f00', parrafos)
    texto = (
        f'El sistema TechCare ({area_label}) estará en mantenimiento.\n\n'
        f'{mensaje}{fin_texto}\n\n'
        'Recibirás otro correo cuando el sistema esté disponible nuevamente.'
    )
    _enviar_async(_usuarios_area(area), '[TechCare] Sistema en mantenimiento', html, texto)


def enviar_correo_fin(area):
    area_label = _AREA_LABELS.get(area, area)
    parrafos = [
        f'El sistema TechCare (<strong>{area_label}</strong>) ya está disponible nuevamente.',
        'Ya puedes ingresar con normalidad. Gracias por tu paciencia.',
    ]
    html  = _html_correo('✅', 'Sistema Restaurado', '#2f9e44', parrafos)
    texto = (
        f'El sistema TechCare ({area_label}) ha vuelto a estar disponible.\n\n'
        'Ya puedes ingresar con normalidad. Gracias por tu paciencia.'
    )
    _enviar_async(_usuarios_area(area), '[TechCare] Sistema disponible nuevamente', html, texto)


# ── VISTAS ─────────────────────────────────────────────────────────────────────

@login_required
@require_POST
def toggle_mantenimiento(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)

    from constance import config

    body = {}
    try:
        body = json.loads(request.body or b'{}')
    except Exception:
        pass

    if config.MAINTENANCE_MODE:
        area_actual = getattr(config, 'MAINTENANCE_AREA', 'all')
        config.MAINTENANCE_MODE          = False
        config.MAINTENANCE_END_TIME      = ''
        config.MAINTENANCE_BLOCKED_USERS = ''
        enviar_correo_fin(area_actual)
    else:
        area         = body.get('area', 'all').strip() or 'all'
        mensaje      = body.get('message', '').strip() or config.MAINTENANCE_MESSAGE
        end_time     = body.get('end_time', '').strip()
        blocked_list = body.get('blocked_users', [])
        blocked_str  = ','.join(e.strip().lower() for e in blocked_list if e.strip())

        config.MAINTENANCE_AREA          = area
        config.MAINTENANCE_MESSAGE       = mensaje
        config.MAINTENANCE_END_TIME      = end_time
        config.MAINTENANCE_BLOCKED_USERS = blocked_str
        config.MAINTENANCE_MODE          = True
        enviar_correo_inicio(area, mensaje, end_time)

    blocked_raw = getattr(config, 'MAINTENANCE_BLOCKED_USERS', '')
    blocked_out = [e for e in blocked_raw.split(',') if e.strip()]

    return JsonResponse({
        'ok':            True,
        'activo':        config.MAINTENANCE_MODE,
        'area':          getattr(config, 'MAINTENANCE_AREA', 'all'),
        'end_time':      getattr(config, 'MAINTENANCE_END_TIME', ''),
        'message':       getattr(config, 'MAINTENANCE_MESSAGE', ''),
        'blocked_users': blocked_out,
    })


@login_required
@require_GET
def estado_mantenimiento(request):
    if not request.user.is_superuser:
        return JsonResponse({'ok': False, 'error': 'Sin permisos'}, status=403)
    from constance import config
    blocked_raw = getattr(config, 'MAINTENANCE_BLOCKED_USERS', '')
    blocked_out = [e for e in blocked_raw.split(',') if e.strip()]
    return JsonResponse({
        'ok':            True,
        'activo':        config.MAINTENANCE_MODE,
        'area':          getattr(config, 'MAINTENANCE_AREA', 'all'),
        'end_time':      getattr(config, 'MAINTENANCE_END_TIME', ''),
        'message':       getattr(config, 'MAINTENANCE_MESSAGE', ''),
        'blocked_users': blocked_out,
    })
