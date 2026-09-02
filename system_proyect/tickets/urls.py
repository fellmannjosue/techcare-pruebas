from django.urls import path
from . import views
from django.shortcuts import redirect
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),

    path('submit_ticket/', views.submit_ticket, name='submit_ticket'),
    path('dashboard/administracion/', views.dashboard_administracion, name='dashboard_administracion'),
    path('mis-tickets/', views.mis_tickets, name='mis_tickets'),
    path('technician_dashboard/', views.technician_dashboard, name='technician_dashboard'),
    path('ticket/<int:ticket_id>/comentarios/', views.ticket_comments, name='ticket_comments'),
    path('ticket_comments/ajax/<int:ticket_id>/', views.ticket_comments_ajax, name='ticket_comments_ajax'),
    path('menu/', lambda request: redirect('/accounts/menu/'), name='tickets_menu'),

    path('ticket_status_update_ajax/<int:ticket_id>/', views.ticket_status_update_ajax, name='ticket_status_update_ajax'),
    path('ticket_eliminar/<int:ticket_id>/', views.ticket_eliminar_ajax, name='ticket_eliminar_ajax'),
    path('ticket_status_get_ajax/<int:ticket_id>/', views.ticket_status_get_ajax, name='ticket_status_get_ajax'),
    path('ticket_send_comment_ajax/<int:ticket_id>/', views.ticket_send_comment_ajax, name='ticket_send_comment_ajax'),
    path('ticket/<int:ticket_id>/reporte/', views.ticket_reporte_ajax, name='ticket_reporte_ajax'),

    # 🚀 IA — <--- hecho por claude code: chat IA + sandbox ACTIVOS en pruebas
    path('ticket/<int:ticket_id>/chat_ai/', views.ticket_chat_ai_ajax, name='ticket_chat_ai_ajax'),
    path('ia/', views.ia_sandbox, name='ia_sandbox'),
    path('ia/preguntar/', views.ia_sandbox_ajax, name='ia_sandbox_ajax'),
]
