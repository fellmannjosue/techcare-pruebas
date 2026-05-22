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
    path('usuarios-lista/', views.usuarios_lista_json, name='usuarios_lista_json'),
    path('menu/', views.menu_view, name='menu'),
    path('seleccion-rol/', views.seleccion_rol, name='seleccion_rol'),
    path('aplicar-rol/<str:rol>/', views.aplicar_rol, name='aplicar_rol'),

    # ── Account Settings ──────────────────────────────────────
    path('settings/',                                  views.settings_perfil,           name='settings_perfil'),
    path('settings/notificaciones/',                   views.settings_notificaciones,   name='settings_notificaciones'),
    path('settings/usuarios/',                         views.settings_usuarios,         name='settings_usuarios'),
    path('settings/usuarios/crear/',                   views.settings_usuario_crear,    name='settings_usuario_crear'),
    path('settings/usuarios/<int:pk>/editar/',         views.settings_usuario_editar,   name='settings_usuario_editar'),
    path('settings/usuarios/<int:pk>/eliminar/',       views.settings_usuario_eliminar,    name='settings_usuario_eliminar'),
    path('settings/usuarios/<int:pk>/toggle-perms/',  views.settings_usuario_toggle_perms, name='settings_usuario_toggle_perms'),
    path('settings/grupos/',                           views.settings_grupos,           name='settings_grupos'),
    path('settings/grupos/crear/',                     views.settings_grupo_crear,      name='settings_grupo_crear'),
    path('settings/grupos/<int:pk>/editar/',           views.settings_grupo_editar,     name='settings_grupo_editar'),
    path('settings/grupos/<int:pk>/eliminar/',         views.settings_grupo_eliminar,   name='settings_grupo_eliminar'),
    path('settings/grupos/<int:pk>/usuarios/',         views.settings_grupo_usuarios,        name='settings_grupo_usuarios'),
    path('settings/usuarios/asignar-grupos/',          views.settings_usuarios_asignar_grupos, name='settings_usuarios_asignar_grupos'),
    path('settings/actividad/',                        views.settings_actividad,        name='settings_actividad'),
    path('settings/conducta/coordinadores/',                    views.settings_coordinadores,            name='settings_coordinadores'),
    path('settings/conducta/coordinadores/<int:pk>/eliminar/',  views.settings_coordinador_eliminar,     name='settings_coordinador_eliminar'),
    path('settings/conducta/notificaciones/',                   views.settings_notificaciones_conducta,  name='settings_notificaciones_conducta'),
    path('settings/conducta/notificaciones/<int:pk>/eliminar/', views.settings_notificacion_eliminar,    name='settings_notificacion_eliminar'),
    path('settings/conducta/roles/',                            views.settings_roles,                    name='settings_roles'),
    path('settings/reloj/permisos/',                            views.settings_reloj_permisos,           name='settings_reloj_permisos'),

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
