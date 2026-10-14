# <--- hecho por claude code: módulo Contabilidad (TC-PRY-0002). FASE 1: configuración
# del módulo + permisos custom (capacidades de negocio) para autorización por backend.
# FASE 2: Inventario de uniformes (kardex) por área y tipo, valuación promedio ponderado.
from decimal import Decimal

from django.db import models

from core.models import AuditModel


class ConfiguracionContabilidad(AuditModel):
    """Configuración del módulo de Contabilidad. Además ancla los permisos custom
    del módulo (Meta.permissions) para que existan y sean asignables desde /admin
    desde la FASE 1, aunque los submódulos aún no tengan sus propios modelos.
    Las reglas contables (numeración, impuestos, SAR, saldos) NO se asumen aquí:
    se definirán en requerimientos posteriores."""
    nombre = models.CharField(max_length=80, default='Configuración de Contabilidad')
    moneda = models.CharField(max_length=10, blank=True,
                              help_text='Texto libre; no asume reglas de moneda/redondeo.')
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'contabilidad_configuracion'
        verbose_name = 'Configuración de Contabilidad'
        verbose_name_plural = 'Configuración de Contabilidad'
        # Capacidades de negocio (Django ya crea add/change/delete/view por modelo).
        # Nunca se usa is_staff/is_superuser como rol: la autorización es por permiso.
        default_permissions = ('add', 'change', 'delete', 'view')
        permissions = [
            ('ver_contabilidad', 'Ver Contabilidad'),
            ('ver_inventario', 'Ver Inventario'),
            ('administrar_inventario', 'Administrar Inventario'),
            ('ver_cobros', 'Ver Cobros'),
            ('administrar_cobros', 'Administrar Cobros'),
            ('ver_deudas', 'Ver Deudas'),
            ('administrar_deudas', 'Administrar Deudas'),
            ('ver_declaraciones', 'Ver Declaraciones'),
            ('administrar_declaraciones', 'Administrar Declaraciones'),
            ('ver_conciliaciones', 'Ver Conciliaciones'),
            ('administrar_conciliaciones', 'Administrar Conciliaciones'),
            ('ver_cuentas', 'Ver Cuentas'),
            ('administrar_cuentas', 'Administrar Cuentas'),
            ('ver_partidas', 'Ver Partidas'),
            ('crear_partidas', 'Crear Partidas'),
            ('modificar_partidas', 'Modificar Partidas'),
            ('ver_reportes', 'Ver Reportes'),
            ('administrar_configuracion', 'Administrar configuración contable'),
            # <--- FASE 2.1: proveedores, compras, costos e ingresos
            ('ver_proveedores', 'Ver Proveedores'),
            ('crear_proveedor', 'Crear Proveedor'),
            ('editar_proveedor', 'Editar Proveedor'),
            ('ver_compras', 'Ver Compras'),
            ('registrar_compra', 'Registrar Compra'),
            ('anular_compra', 'Anular Compra'),
            ('ver_costos', 'Ver información de costos'),
            ('ver_ingresos', 'Ver Ingresos'),
            # <--- hecho por claude code: roles separados (Ventas / Supervisión)
            ('registrar_venta', 'Registrar Venta'),
            ('ver_auditoria', 'Ver Auditoría'),
            # <--- hecho por claude code: regalías de proveedores (informe aparte, no se contabiliza)
            ('ver_regalias', 'Ver Regalías'),
            ('registrar_regalia', 'Registrar Regalía'),
        ]

    def __str__(self):
        return self.nombre


# ═══════════════════════ FASE 2 · Inventario de uniformes ═══════════════════════
class AreaUniforme(models.Model):
    """Área a la que pertenece el uniforme (BL, Colegio, CFP…). Catálogo editable."""
    nombre = models.CharField(max_length=60, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'contabilidad_area_uniforme'
        ordering = ['nombre']
        verbose_name = 'Área de uniforme'
        verbose_name_plural = 'Áreas de uniforme'

    def __str__(self):
        return self.nombre


class TipoUniforme(models.Model):
    """Tipo de uniforme (Polo, Física, Suéter…). Catálogo editable."""
    nombre = models.CharField(max_length=60, unique=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'contabilidad_tipo_uniforme'
        ordering = ['nombre']
        verbose_name = 'Tipo de uniforme'
        verbose_name_plural = 'Tipos de uniforme'

    def __str__(self):
        return self.nombre


class ProductoUniforme(AuditModel):
    """Un producto de inventario = uniforme concreto por área/tipo/talla.
    Existencia y costo promedio se CACHEAN pero se reconstruyen desde los movimientos."""
    nombre  = models.CharField(max_length=120, verbose_name='Producto')
    area    = models.ForeignKey(AreaUniforme, on_delete=models.PROTECT, related_name='productos')
    tipo    = models.ForeignKey(TipoUniforme, on_delete=models.PROTECT, related_name='productos')
    talla   = models.CharField(max_length=20, blank=True, verbose_name='Talla')
    color   = models.CharField(max_length=40, blank=True)
    codigo  = models.CharField(max_length=40, blank=True, verbose_name='Código / SKU')
    unidad  = models.CharField(max_length=20, default='Unidad')
    stock_minimo = models.PositiveIntegerField(default=0, verbose_name='Stock mínimo (aviso)')
    activo  = models.BooleanField(default=True)
    # <--- FASE 2.1: precio de venta e impuesto de venta (opcionales; no todo se vende)
    precio_venta = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                       verbose_name='Precio de venta')
    # <--- hecho por claude code: precio de referencia que puso el proveedor (informativo, no cambia el costo promedio)
    precio_proveedor = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                           verbose_name='Precio del proveedor')
    tipo_impuesto_venta = models.ForeignKey('TipoImpuesto', null=True, blank=True,
                                            on_delete=models.SET_NULL, related_name='productos_venta',
                                            verbose_name='Impuesto de venta')
    # Cache (fuente de verdad = movimientos):
    existencia_actual = models.IntegerField(default=0, editable=False)
    costo_promedio    = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'), editable=False)

    class Meta:
        db_table = 'contabilidad_producto_uniforme'
        ordering = ['area__nombre', 'tipo__nombre', 'nombre', 'talla']
        verbose_name = 'Producto (uniforme)'
        verbose_name_plural = 'Productos (uniformes)'
        unique_together = ('nombre', 'area', 'tipo', 'talla')

    def __str__(self):
        base = f'{self.nombre}'
        if self.talla:
            base += f' · Talla {self.talla}'
        return base

    # <--- hecho por claude code: ISV Honduras fijo 15% sobre el precio de venta
    ISV_VENTA = Decimal('0.15')

    @property
    def valor_total(self):
        """Valor del inventario de este producto (existencia × costo promedio)."""
        return (Decimal(self.existencia_actual) * self.costo_promedio).quantize(Decimal('0.01'))

    @property
    def isv_venta(self):
        """ISV 15% CONTENIDO en el precio de venta (impuesto incluido): precio × 0.15/1.15."""
        pv = Decimal(self.precio_venta or 0)
        return (pv * self.ISV_VENTA / (Decimal('1') + self.ISV_VENTA)).quantize(Decimal('0.01'))

    @property
    def precio_venta_final(self):
        """Precio final = el precio de venta (el ISV ya va incluido, no se suma encima)."""
        return (Decimal(self.precio_venta or 0)).quantize(Decimal('0.01'))

    @property
    def bajo_stock(self):
        return self.stock_minimo and self.existencia_actual <= self.stock_minimo


class ClaseMovimiento(models.TextChoices):
    SALDO_INICIAL = 'saldo_inicial', 'Saldo inicial'
    ENTRADA       = 'entrada',       'Entrada'
    SALIDA        = 'salida',        'Salida'
    AJUSTE_POS    = 'ajuste_pos',    'Ajuste (+)'
    AJUSTE_NEG    = 'ajuste_neg',    'Ajuste (−)'


# Clases que suman a la existencia (columna "Entradas" del kardex) y las que restan.
CLASES_ENTRADA = {ClaseMovimiento.SALDO_INICIAL, ClaseMovimiento.ENTRADA, ClaseMovimiento.AJUSTE_POS}
CLASES_SALIDA  = {ClaseMovimiento.SALIDA, ClaseMovimiento.AJUSTE_NEG}


class TipoSalida(models.TextChoices):
    """<--- FASE 2.1: motivo de una SALIDA. Solo VENTA genera ingreso."""
    VENTA       = 'venta',       'Venta'
    AJUSTE      = 'ajuste',      'Ajuste'
    PERDIDA     = 'perdida',     'Pérdida'
    DANO        = 'dano',        'Daño'
    USO_INTERNO = 'uso_interno', 'Uso interno'
    DONACION    = 'donacion',    'Donación'


class MovimientoUniforme(AuditModel):
    """Kardex: cada entrada/salida/ajuste. Append-only (no se borra; se corrige con ajuste).
    El costo del saldo se valora por PROMEDIO PONDERADO (recalculado en services)."""
    producto = models.ForeignKey(ProductoUniforme, on_delete=models.PROTECT, related_name='movimientos')
    fecha    = models.DateField()
    clase    = models.CharField(max_length=20, choices=ClaseMovimiento.choices, db_index=True)
    concepto = models.CharField(max_length=160, blank=True)
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    importe        = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    # Snapshots tras aplicar el movimiento (para el kardex):
    existencia_despues     = models.IntegerField(default=0)
    costo_promedio_despues = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    motivo        = models.CharField(max_length=160, blank=True)
    observaciones = models.TextField(blank=True)
    # <--- FASE 2.1: motivo de salida (solo VENTA genera ingreso) + datos de venta + origen compra
    tipo_salida     = models.CharField(max_length=20, choices=TipoSalida.choices, blank=True)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=4, default=Decimal('0'))
    ingreso         = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    compra = models.ForeignKey('CompraProveedor', null=True, blank=True, on_delete=models.SET_NULL,
                               related_name='movimientos', verbose_name='Compra de origen')

    class Meta:
        db_table = 'contabilidad_movimiento_uniforme'
        ordering = ['fecha', 'id']
        verbose_name = 'Movimiento de inventario'
        verbose_name_plural = 'Movimientos de inventario'
        indexes = [models.Index(fields=['producto', 'fecha'])]

    def __str__(self):
        return f'{self.producto} · {self.get_clase_display()} · {self.cantidad}'

    @property
    def es_entrada(self):
        return self.clase in CLASES_ENTRADA


# ═══════════════════════ FASE 2.1 · Proveedores, impuestos y compras ═══════════════════════
class TipoImpuesto(models.Model):
    """Catálogo configurable de impuestos. SIN porcentajes por defecto (no se asumen reglas SAR)."""
    nombre = models.CharField(max_length=60, unique=True)
    porcentaje = models.DecimalField(max_digits=6, decimal_places=3, default=Decimal('0'),
                                     verbose_name='Porcentaje (%)')
    activo = models.BooleanField(default=True)
    descripcion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'contabilidad_tipo_impuesto'
        ordering = ['nombre']
        verbose_name = 'Tipo de impuesto'
        verbose_name_plural = 'Tipos de impuesto'

    def __str__(self):
        return f'{self.nombre} ({self.porcentaje}%)'


class Proveedor(AuditModel):
    """Proveedor de uniformes/artículos. El color es solo identificación visual (nunca estado)."""
    nombre = models.CharField(max_length=120)
    nombre_comercial = models.CharField(max_length=120, blank=True)
    rtn = models.CharField(max_length=30, blank=True, verbose_name='RTN')
    contacto = models.CharField(max_length=120, blank=True)
    telefono = models.CharField(max_length=40, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    color = models.CharField(max_length=7, default='#3B82F6', verbose_name='Color identificativo')
    activo = models.BooleanField(default=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'contabilidad_proveedor'
        ordering = ['nombre']
        verbose_name = 'Proveedor'
        verbose_name_plural = 'Proveedores'

    def __str__(self):
        return self.nombre


class EstadoCompra(models.TextChoices):
    BORRADOR   = 'borrador',   'Borrador'
    CONFIRMADA = 'confirmada', 'Confirmada'
    ANULADA    = 'anulada',    'Anulada'


class CompraProveedor(AuditModel):
    """Encabezado de una compra a proveedor. Al CONFIRMAR genera las entradas de inventario
    (fuente única). No se borra si ya afectó inventario: se ANULA con movimientos inversos."""
    codigo = models.CharField(max_length=20, unique=True, editable=False, blank=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='compras')
    fecha = models.DateField()
    documento = models.CharField(max_length=60, blank=True, verbose_name='Documento / Factura')
    estado = models.CharField(max_length=12, choices=EstadoCompra.choices,
                              default=EstadoCompra.BORRADOR, db_index=True)
    subtotal      = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    impuesto_total = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    total         = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    observaciones = models.TextField(blank=True)
    confirmada_por = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    confirmada_en  = models.DateTimeField(null=True, blank=True)
    anulada_por = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    anulada_en  = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = 'contabilidad_compra'
        ordering = ['-fecha', '-id']
        verbose_name = 'Compra a proveedor'
        verbose_name_plural = 'Compras a proveedores'

    def __str__(self):
        return self.codigo or f'Compra #{self.pk}'

    def recalcular_totales(self, guardar=True):
        agg = self.detalles.all()
        sub = sum((d.subtotal for d in agg), Decimal('0'))
        imp = sum((d.impuesto for d in agg), Decimal('0'))
        self.subtotal = sub
        self.impuesto_total = imp
        self.total = (sub + imp).quantize(Decimal('0.01'))
        if guardar:
            self.save(update_fields=['subtotal', 'impuesto_total', 'total'])

    @property
    def total_unidades(self):
        return sum((d.cantidad for d in self.detalles.all()), 0)


class DetalleCompra(models.Model):
    """Línea de compra: producto, cantidad y costo. subtotal/impuesto/total se calculan."""
    compra = models.ForeignKey(CompraProveedor, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(ProductoUniforme, on_delete=models.PROTECT, related_name='detalles_compra')
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=4)
    tipo_impuesto = models.ForeignKey(TipoImpuesto, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    subtotal = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    impuesto = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))
    total    = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0'))

    class Meta:
        db_table = 'contabilidad_detalle_compra'
        verbose_name = 'Detalle de compra'
        verbose_name_plural = 'Detalles de compra'

    def __str__(self):
        return f'{self.producto} × {self.cantidad}'

    def calcular(self):
        """Calcula subtotal/impuesto/total en Decimal (no float)."""
        self.subtotal = (Decimal(self.cantidad) * self.costo_unitario).quantize(Decimal('0.01'))
        pct = self.tipo_impuesto.porcentaje if self.tipo_impuesto else Decimal('0')
        self.impuesto = (self.subtotal * pct / Decimal('100')).quantize(Decimal('0.01'))
        self.total = (self.subtotal + self.impuesto).quantize(Decimal('0.01'))


# ═══════════════════════ REGALÍAS DE PROVEEDORES ═══════════════════════
# <--- hecho por claude code: informe APARTE de regalías/obsequios que entrega un proveedor.
# NO afecta inventario, NO afecta contabilidad, NO genera movimientos ni existencias.
class RegaliaProveedor(AuditModel):
    """Regalía/obsequio que un proveedor entrega. Solo informativo (no se contabiliza)."""
    proveedor   = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='regalias')
    fecha       = models.DateField()
    descripcion = models.CharField(max_length=160, verbose_name='Regalía / obsequio')
    cantidad    = models.PositiveIntegerField(default=1)
    valor_estimado = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                         verbose_name='Valor estimado (opcional, NO se contabiliza)')
    documento     = models.CharField(max_length=60, blank=True, verbose_name='Documento / referencia')
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'contabilidad_regalia'
        ordering = ['-fecha', '-id']
        verbose_name = 'Regalía de proveedor'
        verbose_name_plural = 'Regalías de proveedores'

    def __str__(self):
        return f'{self.descripcion} × {self.cantidad} · {self.proveedor.nombre}'


# ═══════════════════════ PRECIO POR PROVEEDOR ═══════════════════════
# <--- hecho por claude code: precio que cada proveedor puso para un producto (referencia de costo).
# NO cambia el costo promedio del kardex (eso viene de las compras reales); es solo referencia.
class PrecioProveedor(AuditModel):
    """Precio de referencia que un proveedor puso para un producto (uno por proveedor)."""
    producto  = models.ForeignKey(ProductoUniforme, on_delete=models.CASCADE, related_name='precios_proveedor')
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='precios_producto')
    precio    = models.DecimalField(max_digits=12, decimal_places=2, verbose_name='Precio del proveedor')

    class Meta:
        db_table = 'contabilidad_precio_proveedor'
        ordering = ['proveedor__nombre']
        unique_together = ('producto', 'proveedor')
        verbose_name = 'Precio por proveedor'
        verbose_name_plural = 'Precios por proveedor'

    def __str__(self):
        return f'{self.producto} · {self.proveedor.nombre}: {self.precio}'


# ═══════════════════════ FASE 3 · Núcleo contable (partida doble) ═══════════════════════
# <--- hecho por claude code (23-sep-2026): catálogo de cuentas, períodos, centros de costo y
# partidas (asientos) de partida doble. Es la base sobre la que los demás módulos (inventario,
# CFP, sponsors) postearán sus asientos automáticamente en fases posteriores.
class TipoCuenta(models.TextChoices):
    ACTIVO     = 'activo',     'Activo'
    PASIVO     = 'pasivo',     'Pasivo'
    PATRIMONIO = 'patrimonio', 'Patrimonio'
    INGRESO    = 'ingreso',    'Ingreso'
    COSTO      = 'costo',      'Costo'
    GASTO      = 'gasto',      'Gasto'


# Naturaleza normal del saldo por tipo: deudora (Activo, Costo, Gasto) o acreedora (Pasivo, Patrimonio, Ingreso)
NATURALEZA_POR_TIPO = {
    TipoCuenta.ACTIVO: 'deudora', TipoCuenta.COSTO: 'deudora', TipoCuenta.GASTO: 'deudora',
    TipoCuenta.PASIVO: 'acreedora', TipoCuenta.PATRIMONIO: 'acreedora', TipoCuenta.INGRESO: 'acreedora',
}


class CuentaContable(AuditModel):
    """Cuenta del catálogo. Árbol por `padre`; solo las cuentas de DETALLE reciben movimientos.
    El código es jerárquico (1 · 1.1 · 1.1.01 · 1.1.01.001) y ordena el catálogo."""
    NATURALEZAS = (('deudora', 'Deudora'), ('acreedora', 'Acreedora'))
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=120)
    tipo = models.CharField(max_length=12, choices=TipoCuenta.choices)
    naturaleza = models.CharField(max_length=10, choices=NATURALEZAS)
    padre = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='hijas')
    nivel = models.PositiveSmallIntegerField(default=1, editable=False)
    es_detalle = models.BooleanField(default=True, verbose_name='Acepta movimientos',
                                     help_text='Solo las cuentas de detalle se usan en las partidas; las de agrupación solo suman.')
    descripcion = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'contabilidad_cuenta'
        ordering = ['codigo']
        verbose_name = 'Cuenta contable'
        verbose_name_plural = 'Catálogo de cuentas'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.naturaleza:
            self.naturaleza = NATURALEZA_POR_TIPO.get(self.tipo, 'deudora')
        self.nivel = (self.padre.nivel + 1) if self.padre_id else 1
        super().save(*args, **kwargs)

    @property
    def es_balance(self):
        """Cuentas de balance (activo/pasivo/patrimonio) vs. de resultados (ingreso/costo/gasto)."""
        return self.tipo in (TipoCuenta.ACTIVO, TipoCuenta.PASIVO, TipoCuenta.PATRIMONIO)


class CentroCosto(AuditModel):
    """Centro de costo / fondo / proyecto (contabilidad por fondos: donante → proyecto → gasto)."""
    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=120)
    descripcion = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'contabilidad_centro_costo'
        ordering = ['codigo']
        verbose_name = 'Centro de costo'
        verbose_name_plural = 'Centros de costo'

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'


class PeriodoContable(AuditModel):
    """Mes contable. Un período CERRADO no admite partidas nuevas ni cambios."""
    ESTADOS = (('abierto', 'Abierto'), ('cerrado', 'Cerrado'))
    anio = models.PositiveIntegerField()
    mes = models.PositiveSmallIntegerField()
    estado = models.CharField(max_length=10, choices=ESTADOS, default='abierto')
    cerrado_por = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    cerrado_en = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'contabilidad_periodo'
        unique_together = ('anio', 'mes')
        ordering = ['-anio', '-mes']
        verbose_name = 'Período contable'
        verbose_name_plural = 'Períodos contables'

    MESES = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto',
             'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']

    def __str__(self):
        return f'{self.MESES[self.mes]} {self.anio}'

    @property
    def abierto(self):
        return self.estado == 'abierto'


class TipoAsiento(models.TextChoices):
    DIARIO   = 'diario',   'Diario'
    INGRESO  = 'ingreso',  'Ingreso'
    EGRESO   = 'egreso',   'Egreso'
    AJUSTE   = 'ajuste',   'Ajuste'
    APERTURA = 'apertura', 'Apertura'
    CIERRE   = 'cierre',   'Cierre'


class EstadoAsiento(models.TextChoices):
    BORRADOR      = 'borrador',      'Borrador'
    CONTABILIZADO = 'contabilizado', 'Contabilizado'
    ANULADO       = 'anulado',       'Anulado'


class Asiento(AuditModel):
    """Partida contable (encabezado). Solo las CONTABILIZADAS afectan saldos y reportes.
    `origen_modulo`/`origen_id` enlazan las partidas generadas automáticamente por otros módulos."""
    numero = models.CharField(max_length=20, unique=True, blank=True, verbose_name='Nº de partida')
    fecha = models.DateField()
    periodo = models.ForeignKey(PeriodoContable, on_delete=models.PROTECT, related_name='asientos')
    tipo = models.CharField(max_length=10, choices=TipoAsiento.choices, default=TipoAsiento.DIARIO)
    descripcion = models.CharField(max_length=250, verbose_name='Concepto')
    referencia = models.CharField(max_length=80, blank=True, verbose_name='Documento / referencia')
    estado = models.CharField(max_length=14, choices=EstadoAsiento.choices, default=EstadoAsiento.BORRADOR)
    total_debe = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    total_haber = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    origen_modulo = models.CharField(max_length=30, blank=True, editable=False)
    origen_id = models.PositiveIntegerField(null=True, blank=True, editable=False)
    contabilizado_por = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    contabilizado_en = models.DateTimeField(null=True, blank=True)
    anulado_por = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    anulado_en = models.DateTimeField(null=True, blank=True)
    motivo_anulacion = models.CharField(max_length=250, blank=True)

    class Meta:
        db_table = 'contabilidad_asiento'
        ordering = ['-fecha', '-id']
        verbose_name = 'Partida contable'
        verbose_name_plural = 'Partidas contables'

    def __str__(self):
        return f'{self.numero or "(borrador)"} · {self.descripcion[:40]}'

    @property
    def cuadrada(self):
        return self.total_debe == self.total_haber and self.total_debe > 0

    @property
    def editable(self):
        return self.estado == EstadoAsiento.BORRADOR


class DetalleAsiento(models.Model):
    """Línea de una partida: una cuenta de detalle con importe en el Debe O en el Haber."""
    asiento = models.ForeignKey(Asiento, on_delete=models.CASCADE, related_name='detalles')
    orden = models.PositiveSmallIntegerField(default=1)
    cuenta = models.ForeignKey(CuentaContable, on_delete=models.PROTECT, related_name='movimientos')
    centro_costo = models.ForeignKey(CentroCosto, null=True, blank=True, on_delete=models.PROTECT, related_name='movimientos')
    descripcion = models.CharField(max_length=200, blank=True)
    debe = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))
    haber = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal('0.00'))

    class Meta:
        db_table = 'contabilidad_asiento_detalle'
        ordering = ['asiento', 'orden']
        verbose_name = 'Línea de partida'
        verbose_name_plural = 'Líneas de partida'

    def __str__(self):
        return f'{self.cuenta.codigo} D {self.debe} H {self.haber}'
