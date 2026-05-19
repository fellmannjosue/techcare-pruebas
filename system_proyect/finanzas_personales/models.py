from django.db import models
from django.contrib.auth.models import User


class Categoria(models.Model):
    TIPO = [('income', 'Ingreso'), ('expense', 'Gasto')]
    user  = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_categorias')
    nombre = models.CharField(max_length=100)
    tipo   = models.CharField(max_length=10, choices=TIPO)
    color  = models.CharField(max_length=7, default='#999999')

    class Meta:
        ordering = ['tipo', 'nombre']

    def to_dict(self):
        return {'id': str(self.pk), 'name': self.nombre, 'type': self.tipo, 'color': self.color}


class Transaccion(models.Model):
    TIPO = [('income', 'Ingreso'), ('expense', 'Gasto')]
    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='fp_transacciones')
    tipo       = models.CharField(max_length=10, choices=TIPO)
    monto      = models.DecimalField(max_digits=12, decimal_places=2)
    descripcion = models.CharField(max_length=255, blank=True)
    categoria  = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, blank=True)
    fecha      = models.DateField()
    creado     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-fecha', '-creado']

    def to_dict(self):
        return {
            'id': str(self.pk),
            'type': self.tipo,
            'amount': float(self.monto),
            'description': self.descripcion,
            'categoryId': str(self.categoria_id) if self.categoria_id else '',
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

    def to_dict(self):
        return {
            'id': str(self.pk),
            'name': self.nombre,
            'amount': float(self.monto),
            'type': self.tipo,
            'categoryId': str(self.categoria_id) if self.categoria_id else '',
        }


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
    tema   = models.CharField(max_length=10, default='light')

    def to_dict(self):
        return {'currency': self.moneda, 'theme': self.tema}
