# <--- hecho por claude code: Sistema Salidas Baño — URLs
from django.urls import path
from . import views

app_name = 'salidas_bano'

urlpatterns = [
    # ── Vista principal ──────────────────────────────────────────────────────
    path('',                             views.index,              name='index'),
    # <--- hecho por claude code: misma vista, ámbito CFP (participantes por curso)
    path('cfp/',                         views.index, {'ambito': 'cfp'}, name='index_cfp'),

    # ── APIs de registro ─────────────────────────────────────────────────────
    path('guardar/',                     views.guardar_salida,     name='guardar'),
    path('<int:pk>/regreso/',            views.marcar_regreso,     name='regreso'),
    path('<int:pk>/eliminar/',           views.eliminar_salida,    name='eliminar_salida'),

    # ── Notificaciones ───────────────────────────────────────────────────────
    path('notif/count/',                 views.notif_count,        name='notif_count'),
    path('notif/list/',                  views.notif_list,         name='notif_list'),
    path('notif/<int:pk>/leer/',         views.notif_leer,         name='notif_leer'),
    path('notif/leer-todas/',            views.notif_leer_todas,   name='notif_leer_todas'),

    # ── Historial ────────────────────────────────────────────────────────────
    path('historial/<int:ingr_egr_id>/', views.historial_alumno,   name='historial'),

    # ── Coordinador: Períodos Escolares ──────────────────────────────────────
    path('periodos/',                    views.periodos_view,       name='periodos'),

    # ── Coordinador: Maestros – Clases ───────────────────────────────────────
    path('maestros-clases/',             views.maestros_clases_view, name='maestros_clases'),
]
