# ============================================================
# 🔎 RESÚMENES GLOBALES PARA DASHBOARD PRINCIPAL TECHCARE
# ------------------------------------------------------------
# Este archivo SOLO devuelve datos rápidos (JSON).
# NO modifica nada, NO crea notificaciones.
# ============================================================

from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET

# Importación de modelos
from tickets.models import Ticket
from conducta.models import (
    ReporteInformativo,
    ReporteConductual,
    ProgressReport
)

# 🔔 Estos dos son opcionales (módulo en construcción)
try:
    from reloj.models import TiempoCompensatorio, PermisoEmpleado
except:
    TiempoCompensatorio = None
    PermisoEmpleado = None


# ============================================================
# 🧩 UTILIDAD — Formato de fecha para JSON
# ============================================================
def fmt(dt):
    return dt.strftime("%d/%m/%Y %H:%M")


# <--- hecho por claude code (seguridad 05-nov-2026): resúmenes de coordinación solo para la coordinación de ESA área o el superusuario (antes, cualquier autenticado)
def _prohibido():
    return JsonResponse({"total": 0, "items": [], "error": "Sin permiso"}, status=403)


def _es_coord_de(user, grupos):
    """Mismos grupos que nav_coord_bl/nav_coord_col (core/context_processors.py) y las tarjetas del menú.
    Antes cualquier autenticado recibía "alumno - materia - docente" de las dos áreas; el área sale del USUARIO, nunca del navegador."""
    from accounts.panel_roles import _g
    return user.is_superuser or _g(user, *grupos)


# ============================================================
# 📌 RESUMEN: TICKETS
# ============================================================
@require_GET
@login_required
def summary_tickets(request):
    pendientes = Ticket.objects.exclude(status__iexact="Resuelto").order_by("-id")
    # <--- hecho por claude code (seguridad 05-nov-2026): mismo criterio que la tarjeta del menú: el técnico ve todos; el resto, solo los suyos
    if not (request.user.is_superuser or request.user.has_perm('tickets.view_ticket')):
        pendientes = pendientes.filter(usuario=request.user)

    return JsonResponse({
        "total": pendientes.count(),
        "items": [
            {
                "id": t.id,
                "ticket_id": t.ticket_id,
                "titulo": f"Ticket #{t.ticket_id}",
                "descripcion": f"{t.name}: {t.description[:60]}...",
                "fecha": fmt(t.created_at),
            }
            for t in pendientes[:5]
        ]
    })


# ============================================================
# 📌 RESUMEN: REPORTES — COORDINACIÓN BL
# ============================================================
@require_GET
@login_required
def summary_coordinacion_bl(request):
    """
    ❗ IMPORTANTE:
    Esto NO es el dashboard del coordinador.
    Solo envía un resumen simple para el dashboard principal.
    """
    from accounts.panel_roles import _GRUPOS_COORD_BL
    if not _es_coord_de(request.user, _GRUPOS_COORD_BL):   # <--- hecho por claude code (seguridad 05-nov-2026)
        return _prohibido()

    total = (
        ReporteInformativo.objects.filter(area="bilingue", estado="enviado").count() +
        ReporteConductual.objects.filter(area="bilingue", estado="enviado").count() +
        ProgressReport.objects.filter(estado="enviado").count()
    )

    info     = ReporteInformativo.objects.filter(area="bilingue").order_by("-fecha")[:5]
    conducta = ReporteConductual.objects.filter(area="bilingue").order_by("-fecha")[:5]
    progress = ProgressReport.objects.exclude(estado="borrador").order_by("-fecha")[:5]   # <--- hecho por claude code (seguridad 05-nov-2026): los borradores del maestro no van al coordinador

    recientes = sorted(list(info) + list(conducta) + list(progress),
                       key=lambda x: x.fecha, reverse=True)

    return JsonResponse({
        "total": total,
        "items": [
            {
                "id": r.id,
                "titulo": "Reporte Bilingüe",
                "descripcion": str(r),
                "fecha": fmt(r.fecha),
            }
            for r in recientes[:5]
        ]
    })


# ============================================================
# 📌 RESUMEN: REPORTES — COORDINACIÓN COLEGIO
# ============================================================
@require_GET
@login_required
def summary_coordinacion_col(request):
    from accounts.panel_roles import _GRUPOS_COORD_COL
    if not _es_coord_de(request.user, _GRUPOS_COORD_COL):   # <--- hecho por claude code (seguridad 05-nov-2026)
        return _prohibido()
    total = (
        ReporteInformativo.objects.filter(area="colegio", estado="enviado").count() +
        ReporteConductual.objects.filter(area="colegio", estado="enviado").count()
    )

    info     = ReporteInformativo.objects.filter(area="colegio").order_by("-fecha")[:5]
    conducta = ReporteConductual.objects.filter(area="colegio").order_by("-fecha")[:5]

    recientes = sorted(list(info) + list(conducta),
                       key=lambda x: x.fecha, reverse=True)

    return JsonResponse({
        "total": total,
        "items": [
            {
                "id": r.id,
                "titulo": "Reporte Colegio",
                "descripcion": str(r),
                "fecha": fmt(r.fecha),
            }
            for r in recientes[:5]
        ]
    })


# ============================================================
# 📌 RESUMEN: RELOJ (Permisos / Compensatorio)
# ============================================================
@require_GET
@login_required
def summary_reloj(request):
    if not request.user.is_superuser:   # <--- hecho por claude code (seguridad 05-nov-2026): sin ruta hoy; si se enlaza, que no quede abierta
        return _prohibido()

    if not TiempoCompensatorio or not PermisoEmpleado:
        return JsonResponse({"total": 0, "items": []})

    permisos = PermisoEmpleado.objects.filter(aprobado=False).order_by("-fecha_inicio")[:5]
    compensatorios = TiempoCompensatorio.objects.filter(estado="PEND").order_by("-fecha")[:5]

    recientes = list(permisos) + list(compensatorios)
    recientes.sort(key=lambda x: getattr(x, "fecha", None) or getattr(x, "fecha_inicio", None), reverse=True)

    return JsonResponse({
        "total": len(recientes),
        "items": [
            {
                "id": r.id,
                "titulo": "Solicitud Reloj",
                "descripcion": str(r),
                "fecha": str(getattr(r, "fecha", None) or getattr(r, "fecha_inicio", "")),
            }
            for r in recientes[:5]
        ]
    })
