# ============================================================
#  views_notifications.py — Sistema Global de Notificaciones
# ============================================================

from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from django.utils.timezone import localtime

from .models import Notificacion
import json


# ============================================================
#  🧩 FORMATEADOR DE FECHAS
# ============================================================
def format_fecha(dt):
    """Convierte fecha datetime a formato legible."""
    if dt is None:
        return ""
    dt_local = localtime(dt)
    return dt_local.strftime("%d/%m/%Y %H:%M")


# ============================================================
#  🔔 OBTENER NOTIFICACIONES NO LEÍDAS
# ============================================================
@require_GET
@login_required
def notificaciones_usuario(request):
    """
    Devuelve las notificaciones NO LEÍDAS del usuario actual.
    Limita a las 20 más recientes.
    Formato solicitado por notifications.js:
    {
        "notificaciones": [
            {
                id, mensaje, modulo, tipo, fecha, extra
            }
        ]
    }
    """

    notis = (
        Notificacion.objects
        .filter(destinatario=request.user, leida=False)
        .order_by('-fecha')[:20]
    )

    data = [
        {
            "id": n.id,
            "mensaje": n.mensaje,
            "modulo": n.modulo,
            "tipo": n.tipo,  # info | alerta | error | exito
            "fecha": format_fecha(n.fecha),
            "extra": n.extra,
        }
        for n in notis
    ]

    return JsonResponse({"ok": True, "notificaciones": data})


# ============================================================
#  🔔 MARCAR NOTIFICACIONES COMO LEÍDAS
# ============================================================
@require_POST
@login_required
def marcar_notificaciones_leidas(request):
    """
    Marca un conjunto de notificaciones como leídas.
    Recibe JSON:
    {
        "ids": [1,2,3]
    }
    """
    try:
        body = request.body.decode('utf-8')
        data = json.loads(body) if body.strip() else {}
        ids = data.get("ids", [])

        qs = Notificacion.objects.filter(destinatario=request.user, leida=False)
        if ids:
            qs = qs.filter(id__in=ids)
        qs.update(leida=True)

        return JsonResponse({"ok": True})

    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
