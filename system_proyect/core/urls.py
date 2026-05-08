from django.urls import path
from .views_maintenance import toggle_mantenimiento, estado_mantenimiento

# Notificaciones
from .views_notifications import (
    notificaciones_usuario,
    marcar_notificaciones_leidas
)

# Resúmenes para el dashboard
from .views_summary import (
    summary_tickets,
    summary_coordinacion_bl,
    summary_coordinacion_col,
)

urlpatterns = [

    # ============================
    # 🔔 NOTIFICACIONES
    # ============================
    path("api/notificaciones/", notificaciones_usuario, name="api_notificaciones"),
    path("api/notificaciones/marcar/", marcar_notificaciones_leidas, name="api_notificaciones_marcar"),

    # ============================
    # 📊 SUMMARY PARA EL DASHBOARD
    # ============================
    path("api/summary/tickets/", summary_tickets, name="summary_tickets"),
    path("api/summary/coordinacion_bl/", summary_coordinacion_bl, name="summary_coordinacion_bl"),
    path("api/summary/coordinacion_col/", summary_coordinacion_col, name="summary_coordinacion_col"),

    # ============================
    # 🔧 MODO MANTENIMIENTO
    # ============================
    path("api/mantenimiento/toggle/", toggle_mantenimiento, name="toggle_mantenimiento"),
    path("api/mantenimiento/estado/", estado_mantenimiento, name="estado_mantenimiento"),
]
