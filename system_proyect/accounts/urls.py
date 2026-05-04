from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    # Login principal (unificado)
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('maestro_logout/', views.maestro_logout, name='maestro_logout'),
    path('register/', views.register_maestro, name='register_maestro'),
    path('reenviar-bienvenida/', views.reenviar_bienvenida, name='reenviar_bienvenida'),
    path('menu/', views.menu_view, name='menu'),
    path('seleccion-rol/', views.seleccion_rol, name='seleccion_rol'),
    path('aplicar-rol/<str:rol>/', views.aplicar_rol, name='aplicar_rol'),

    # Notificaciones para dashboard
  

    # Recuperación de contraseña (vistas estándar de Django)
    path('password_reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.txt',
        subject_template_name='accounts/password_reset_subject.txt',
    ), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]
