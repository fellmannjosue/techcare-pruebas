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

    class Meta:
        verbose_name = 'Perfil de usuario'
        verbose_name_plural = 'Perfiles de usuario'

    def __str__(self):
        return f'Perfil de {self.usuario.username}'


@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        PerfilUsuario.objects.get_or_create(usuario=instance)
