from datetime import date

from django.db import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    TIPO = [('income', 'Ingreso'), ('expense', 'Gasto')]
    user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_categorias')
    nombre = models.CharField(max_length=100)
    tipo   = models.CharField(max_length=10, choices=TIPO)
    color  = models.CharField(max_length=7, default='#999999')
    icono  = models.CharField(max_length=40, default='ti-tag')
    excluir_totales = models.BooleanField(default=False)  # ej. transferencias entre cuentas

    class Meta:
        ordering = ['tipo', 'nombre']

    def to_dict(self):
        return {'id': str(self.pk), 'name': self.nombre, 'type': self.tipo,
                'color': self.color, 'icon': self.icono, 'exclude': self.excluir_totales}


class Cuenta(models.Model):
    TIPO = [
        ('cash', 'Efectivo'), ('bank', 'Banco'), ('card', 'Tarjeta'),
        ('savings', 'Ahorro'), ('loan', 'Préstamo'), ('other', 'Otro'),
    ]
    MONEDA = [('L', 'Lempira (L)'), ('$', 'Dólar ($)')]
    user          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_cuentas')
    nombre        = models.CharField(max_length=100)
    tipo          = models.CharField(max_length=10, choices=TIPO, default='cash')
    moneda        = models.CharField(max_length=5, choices=MONEDA, default='L')
    saldo_inicial = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    color         = models.CharField(max_length=7, default='#2A7A4F')
    icono         = models.CharField(max_length=40, default='ti-wallet')
    archivada     = models.BooleanField(default=False)
    orden         = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['orden', 'nombre']

    def to_dict(self):
        return {
            'id': str(self.pk), 'name': self.nombre, 'type': self.tipo,
            'currency': self.moneda,
            'initial': float(self.saldo_inicial), 'color': self.color,
            'icon': self.icono, 'archived': self.archivada,
        }


class Transaccion(models.Model):
    TIPO = [('income', 'Ingreso'), ('expense', 'Gasto'), ('transfer', 'Transferencia')]
    user           = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_transacciones')
    tipo           = models.CharField(max_length=10, choices=TIPO)
    monto          = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion    = models.CharField(max_length=255, blank=True)
    categoria      = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    cuenta         = models.ForeignKey(Cuenta, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='transacciones')
    cuenta_destino = models.ForeignKey(Cuenta, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='transferencias_recibidas')
    fecha          = models.DateField()
    creado         = models.DateTimeField(auto_now_add=True)
    origen         = models.CharField(max_length=10, default='manual')  # 'manual' | 'import'
    saldo_ref      = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)

    class Meta:
        ordering = ['-fecha', '-creado']

    def to_dict(self):
        return {
            'id': str(self.pk),
            'type': self.tipo,
            'amount': float(self.monto),
            'description': self.descripcion,
            'categoryId': str(self.categoria_id) if self.categoria_id else '',
            'accountId': str(self.cuenta_id) if self.cuenta_id else '',
            'toAccountId': str(self.cuenta_destino_id) if self.cuenta_destino_id else '',
            'date': str(self.fecha),
        }


class Pendiente(models.Model):
    TIPO = [('income', 'Por cobrar'), ('expense', 'Por pagar')]
    user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_pendientes')
    tipo   = models.CharField(max_length=10, choices=TIPO)
    nombre = models.CharField(max_length=255)
    monto  = models.DecimalField(max_digits=12, decimal_places=2)
    fecha  = models.DateField()

    class Meta:
        ordering = ['fecha']

    def to_dict(self):
        return {
            'id': str(self.pk),
            'type': self.tipo,
            'name': self.nombre,
            'amount': float(self.monto),
            'date': str(self.fecha),
        }


class EntradaRapida(models.Model):
    TIPO = [('income', 'Ingreso'), ('expense', 'Gasto')]
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_entradas_rapidas')
    nombre    = models.CharField(max_length=100)
    monto     = models.DecimalField(max_digits=12, decimal_places=2)
    tipo      = models.CharField(max_length=10, choices=TIPO)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    cuenta    = models.ForeignKey(Cuenta, on_delete=models.SET_NULL, null=True, blank=True)
    color     = models.CharField(max_length=7, default='#2A7A4F')
    icono     = models.CharField(max_length=40, default='ti-bolt')

    def to_dict(self):
        return {
            'id': str(self.pk),
            'name': self.nombre,
            'amount': float(self.monto),
            'type': self.tipo,
            'categoryId': str(self.categoria_id) if self.categoria_id else '',
            'accountId': str(self.cuenta_id) if self.cuenta_id else '',
            'color': self.color,
            'icon': self.icono,
        }


class Recurrente(models.Model):
    TIPO = [('income', 'Ingreso'), ('expense', 'Gasto')]
    FREQ = [
        ('weekly', 'Semanal'), ('biweekly', 'Quincenal'),
        ('monthly', 'Mensual'), ('yearly', 'Anual'),
    ]
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_recurrentes')
    tipo        = models.CharField(max_length=10, choices=TIPO)
    nombre      = models.CharField(max_length=255)
    monto       = models.DecimalField(max_digits=12, decimal_places=2)
    categoria   = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    cuenta      = models.ForeignKey(Cuenta, on_delete=models.SET_NULL, null=True, blank=True)
    frecuencia  = models.CharField(max_length=10, choices=FREQ, default='monthly')
    proxima     = models.DateField()
    activo      = models.BooleanField(default=True)

    class Meta:
        ordering = ['proxima']

    def to_dict(self):
        return {
            'id': str(self.pk),
            'type': self.tipo,
            'name': self.nombre,
            'amount': float(self.monto),
            'categoryId': str(self.categoria_id) if self.categoria_id else '',
            'accountId': str(self.cuenta_id) if self.cuenta_id else '',
            'freq': self.frecuencia,
            'next': str(self.proxima),
            'active': self.activo,
        }

    def avanzar(self):
        """Avanza la fecha próxima según la frecuencia."""
        d = self.proxima
        if self.frecuencia == 'weekly':
            self.proxima = d + _td(days=7)
        elif self.frecuencia == 'biweekly':
            self.proxima = d + _td(days=14)
        elif self.frecuencia == 'yearly':
            self.proxima = d.replace(year=d.year + 1)
        else:  # monthly
            self.proxima = _add_months(d, 1)


class Presupuesto(models.Model):
    user   = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_presupuestos')
    nombre = models.CharField(max_length=100)
    limite = models.DecimalField(max_digits=12, decimal_places=2)

    def to_dict(self):
        return {
            'id': str(self.pk),
            'name': self.nombre,
            'limit': float(self.limite),
            'items': [{'catId': str(i.categoria_id)} for i in self.items.all() if i.categoria_id],
        }


class PresupuestoCategoria(models.Model):
    presupuesto = models.ForeignKey(Presupuesto, on_delete=models.CASCADE, related_name='items')
    categoria   = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True)


class MetaAhorro(models.Model):
    user        = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_metas')
    nombre      = models.CharField(max_length=100)
    objetivo    = models.DecimalField(max_digits=12, decimal_places=2)
    ahorrado    = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_limite = models.DateField(null=True, blank=True)
    emoji       = models.CharField(max_length=10, default='🎯')

    def to_dict(self):
        return {
            'id': str(self.pk),
            'name': self.nombre,
            'target': float(self.objetivo),
            'saved': float(self.ahorrado),
            'deadline': str(self.fecha_limite) if self.fecha_limite else '',
            'emoji': self.emoji,
        }


class ConfiguracionUsuario(models.Model):
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name='fp_configuracion')
    moneda = models.CharField(max_length=5, default='L')
    tema   = models.CharField(max_length=10, default='dark')

    def to_dict(self):
        return {'currency': self.moneda, 'theme': self.tema}


# ── Utilidades de fechas para recurrentes ─────────────────────────────────────
from datetime import timedelta as _td


def _add_months(d, n):
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    import calendar
    last = calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))
