from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# <!-- <--- hecho por claude code: modelo abstracto de auditoría reutilizable.
#      Agrega creado_por, modificado_por, fecha_creado y fecha_modificado
#      a cualquier modelo que herede de él. related_name='+' desactiva
#      la relación inversa para evitar conflictos entre modelos. -->
class AuditModel(models.Model):
    creado_por = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name="Creado por"
    )
    modificado_por = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL,
        related_name='+', verbose_name="Modificado por"
    )
    fecha_creado = models.DateTimeField(default=timezone.now, editable=False, verbose_name="Fecha de creación")
    fecha_modificado = models.DateTimeField(auto_now=True, verbose_name="Fecha de modificación")

    class Meta:
        abstract = True


class AuditLog(models.Model):
    """Registro de bajo nivel: capturado por triggers MySQL.
    Complementa a django-simple-history (que registra cambios vía ORM con usuario).
    Los triggers lo alimentan incluso ante SQL directo / migraciones / imports."""
    table_name = models.CharField("Tabla", max_length=100, db_index=True)
    operation  = models.CharField("Operación", max_length=10)  # INSERT UPDATE DELETE
    record_pk  = models.CharField("PK del registro", max_length=100, db_index=True)
    changed_at = models.DateTimeField("Fecha/hora", db_index=True)

    class Meta:
        db_table = 'core_audit_log'
        verbose_name = 'Audit log (trigger)'
        verbose_name_plural = 'Audit logs (trigger)'
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.operation} on {self.table_name} pk={self.record_pk}'


class Notificacion(models.Model):
    destinatario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notificaciones')
    mensaje = models.CharField(max_length=300)
    modulo = models.CharField(max_length=50)
    tipo = models.CharField(max_length=30, default='info')
    leida = models.BooleanField(default=False)
    fecha = models.DateTimeField(auto_now_add=True)
    extra = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f'{self.destinatario} - {self.mensaje[:40]}'
