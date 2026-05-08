# mantenimiento/urls.py
from django.urls import path
from django.shortcuts import redirect
from . import views

app_name = 'mantenimiento'   # declara el namespace

urlpatterns = [
    path(
        '',
        views.maintenance_dashboard,
        name='maintenance_dashboard'
    ),
    path('download/<int:record_id>/',  views.download_maintenance_pdf, name='download_maintenance_pdf'),
    path('<int:pk>/editar/',           views.editar_mantenimiento,      name='editar_mantenimiento'),
    path('<int:pk>/eliminar/',         views.eliminar_mantenimiento,    name='eliminar_mantenimiento'),
    path(
        'menu/',
        lambda request: redirect('/accounts/menu/'),
        name='maintenance_menu'
    ),
]
