from django.db import models
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


class RegistroAcceso(models.Model):
    usuario    = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='accesos')
    username   = models.CharField(max_length=150)
    ip         = models.GenericIPAddressField(null=True, blank=True)
    agente     = models.TextField(blank=True)
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha_hora']
        verbose_name = 'Registro de acceso'
        verbose_name_plural = 'Registros de acceso'

    def __str__(self):
        return f'{self.username} — {self.fecha_hora:%d/%m/%Y %H:%M}'


class PerfilUsuario(models.Model):
    usuario            = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    avatar             = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Avatar')
    puede_ver_usuarios = models.BooleanField(
        'Puede gestionar usuarios/grupos', default=False,
        help_text='Permite a este usuario Staff ver y editar la sección Usuarios y Grupos en Settings.'
    )
    es_coord_maestro   = models.BooleanField(
        'Es coordinador-maestro', default=False,
        help_text='Activa el checkbox "Soy maestro" en el login para que este usuario pueda alternar entre dashboard de coordinador y maestro.'
    )
    # Bloqueo de acceso por intentos fallidos de login (5+ intentos → bloqueo total).
    login_bloqueado    = models.BooleanField('Acceso bloqueado', default=False)
    login_bloqueado_en = models.DateTimeField('Bloqueado el', null=True, blank=True)
    # <--- hecho por claude code: última versión cuyas novedades vio el usuario
    version_vista      = models.CharField('Última versión vista', max_length=20, blank=True, default='')

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'

    def __str__(self):
        return f'Perfil de {self.usuario.username}'


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.get_or_create(usuario=instance)


class CoordPermiso(models.Model):
    """Permisos de edición/eliminación por módulo para coordinadores BL y Colegio."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='coord_permiso', verbose_name='Usuario',
    )
    # Notas Mitad de Parcial
    notas_editar          = models.BooleanField('Notas – Editar',              default=False)
    notas_eliminar        = models.BooleanField('Notas – Eliminar',            default=False)
    notas_eliminar_hasta  = models.DateTimeField('Notas – Eliminar hasta',     null=True, blank=True)
    # Salidas Baño
    salidas_editar          = models.BooleanField('Salidas – Editar',            default=False)
    salidas_eliminar        = models.BooleanField('Salidas – Eliminar',          default=False)
    salidas_eliminar_hasta  = models.DateTimeField('Salidas – Eliminar hasta',   null=True, blank=True)
    # Agenda
    agenda_editar          = models.BooleanField('Agenda – Editar',             default=False)
    agenda_eliminar        = models.BooleanField('Agenda – Eliminar',           default=False)
    agenda_eliminar_hasta  = models.DateTimeField('Agenda – Eliminar hasta',    null=True, blank=True)
    # Dashboard Coordinador (reportes conducta)
    dashboard_editar          = models.BooleanField('Dashboard – Editar',          default=False)
    dashboard_eliminar        = models.BooleanField('Dashboard – Eliminar',        default=False)
    dashboard_eliminar_hasta  = models.DateTimeField('Dashboard – Eliminar hasta', null=True, blank=True)

    class Meta:
        db_table            = 'accounts_coord_permiso'
        verbose_name        = 'Permiso coordinador'
        verbose_name_plural = 'Permisos coordinadores'

    def __str__(self):
        return f'Permisos coord – {self.user}'


class DestinatarioEmail(models.Model):
    """Configura qué módulos le envían correo directamente a cada usuario."""
    user = models.OneToOneField(
        User, on_delete=models.CASCADE,
        related_name='destinatario_email',
        verbose_name='Usuario',
    )
    conducta_bl        = models.BooleanField('Conducta BL',               default=False)
    conducta_col       = models.BooleanField('Conducta Colegio',           default=False)
    progress_bl        = models.BooleanField('Progress BL',                default=False)
    notas_parcial_bl   = models.BooleanField('Notas Parcial BL',           default=False)
    notas_parcial_col  = models.BooleanField('Notas Parcial Colegio',      default=False)
    salidas_negro_col  = models.BooleanField('Salidas Negro – Colegio',    default=False)
    salidas_negro_bach = models.BooleanField('Salidas Negro – Bachillerato', default=False)
    enfermeria         = models.BooleanField('Enfermería',                  default=False)
    tickets            = models.BooleanField('Tickets Soporte',             default=False)

    class Meta:
        db_table            = 'accounts_destinatario_email'
        verbose_name        = 'Destinatario de correo'
        verbose_name_plural = 'Destinatarios de correos'

    def __str__(self):
        return f'Correos → {self.user.username}'
