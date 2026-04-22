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
from citas_billingue.models import Appointment_bl
from citas_colegio.models import Appointment_col
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


# ============================================================
# 📌 RESUMEN: TICKETS
# ============================================================
@require_GET
@login_required
def summary_tickets(request):
    pendientes = Ticket.objects.exclude(status__iexact="Resuelto").order_by("-id")

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
# 📌 RESUMEN: CITAS BILINGÜE
# ============================================================
@require_GET
@login_required
def summary_citas_bl(request):
    citas = Appointment_bl.objects.exclude(status__iexact="Resuelto").order_by("-id")

    return JsonResponse({
        "total": citas.count(),
        "items": [
            {
                "id": c.id,
                "titulo": f"Cita BL — {c.parent_name}",
                "descripcion": f"Maestro: {c.teacher.name}",
                "fecha": f"{c.date} {c.time}",
            }
            for c in citas[:5]
        ]
    })


# ============================================================
# 📌 RESUMEN: CITAS COLEGIO/VOC
# ============================================================
@require_GET
@login_required
def summary_citas_col(request):
    citas = Appointment_col.objects.exclude(status__iexact="Resuelto").order_by("-id")

    return JsonResponse({
        "total": citas.count(),
        "items": [
            {
                "id": c.id,
                "titulo": f"Cita Colegio — {c.parent_name}",
                "descripcion": f"Maestro: {c.teacher.name}",
                "fecha": f"{c.date} {c.time}",
            }
            for c in citas[:5]
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

    total = (
        ReporteInformativo.objects.filter(area="bilingue", estado="enviado").count() +
        ReporteConductual.objects.filter(area="bilingue", estado="enviado").count() +
        ProgressReport.objects.filter(estado="enviado").count()
    )

    info     = ReporteInformativo.objects.filter(area="bilingue").order_by("-fecha")[:5]
    conducta = ReporteConductual.objects.filter(area="bilingue").order_by("-fecha")[:5]
    progress = ProgressReport.objects.all().order_by("-fecha")[:5]

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
