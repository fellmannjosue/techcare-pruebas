from django.db import models
from django.contrib.auth import get_user_model

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
