# mantenimiento/urls.py
from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'mantenimiento'   # declara el namespace

urlpatterns = [
    # <--- hecho por claude code (28-sep-2026): una página por tipo; la raíz manda a Computadoras
    path('', lambda request: redirect('mantenimiento:fichas', tipo='computadoras'), name='maintenance_dashboard'),
    path('download/<int:record_id>/',  views.download_maintenance_pdf, name='download_maintenance_pdf'),
    path('control/reporte.pdf',        views.control_reporte_pdf,      name='control_reporte_pdf'),
    path('control/fichas.pdf',         views.control_fichas_pdf,       name='control_fichas_pdf'),
    # <--- hecho por claude code (17-sep-2026): reportes PDF/Excel de Inspecciones, Entregas y Recogidas
    path('reporte/<str:tipo>.pdf',     views.reporte_tipo_pdf,         name='reporte_tipo_pdf'),
    path('reporte/<str:tipo>.xlsx',    views.reporte_tipo_excel,       name='reporte_tipo_excel'),
    path('<int:pk>/editar/',           views.editar_mantenimiento,      name='editar_mantenimiento'),
    path('<int:pk>/eliminar/',         views.eliminar_mantenimiento,    name='eliminar_mantenimiento'),
    path('tipo-falla/crear/',          views.tipo_falla_crear,          name='tipo_falla_crear'),
    path('<int:pk>/firma-solicitada/', views.marcar_firma_solicitada,   name='marcar_firma_solicitada'),
    path('firmar/<uuid:token>/',       views.firmar_publico,            name='firmar_publico'),
    path(
        'menu/',
        lambda request: redirect('/accounts/menu/'),
        name='maintenance_menu'
    ),
    path('<slug:tipo>/',               views.maintenance_dashboard,     name='fichas'),   # <--- hecho por claude code (28-sep-2026)
]
