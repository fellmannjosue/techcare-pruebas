from django.db import models
from django.conf import settings

MONEDA_CHOICES = [
    ('USD', 'Dólar (USD)'),
    ('EUR', 'Euro (EUR)'),
    ('CHF', 'Franco Suizo (CHF)'),
]


class TasaCambio(models.Model):
    moneda = models.CharField('Moneda', max_length=10, choices=MONEDA_CHOICES, unique=True)
    tasa = models.DecimalField('Tasa (LPS por 1 unidad)', max_digits=12, decimal_places=4)
    fecha_actualizacion = models.DateField('Fecha de actualización')
    actualizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, verbose_name='Actualizado por'
    )

    class Meta:
        db_table = 'calculadoras_tasa_cambio'
        verbose_name = 'Tasa de cambio'
        verbose_name_plural = 'Tasas de cambio'

    def __str__(self):
        return f'{self.moneda}: L. {self.tasa} ({self.fecha_actualizacion})'
