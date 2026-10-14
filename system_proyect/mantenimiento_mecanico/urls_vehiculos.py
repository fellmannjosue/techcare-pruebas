# <--- hecho por claude code (12-oct-2026): Mantenimiento de vehículos — ventana aparte en /mantenimiento-vehiculos/
from django.urls import path

from . import views_vehiculos as v

app_name = 'vehiculos'

urlpatterns = [
    path('', v.flota, name='flota'),
    path('hojas.pdf', v.hojas_pdf, name='hojas'),
    path('nuevo/', v.vehiculo_nuevo, name='nuevo'),   # <--- hecho por claude code (12-oct-2026)
    path('<int:vid>/editar/', v.vehiculo_editar, name='editar'),
    path('<int:vid>/', v.detalle, name='detalle'),
    path('<int:vid>/hoja.pdf', v.hoja_pdf, name='hoja'),
    path('<int:vid>/lectura/', v.lectura_crear, name='lectura'),
    path('<int:vid>/mantenimiento/', v.mant_crear, name='mant_crear'),
    path('<int:vid>/historial.xlsx', v.historial_xlsx, name='historial_xlsx'),
    path('mant/<int:mid>/pdf/', v.mant_pdf, name='mant_pdf'),
    path('mant/<int:mid>/comentario/', v.mant_comentario, name='mant_comentario'),
]
