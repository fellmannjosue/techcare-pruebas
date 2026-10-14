# <--- hecho por claude code (01-oct-2026): Mantenimiento Mecánico — control de combustibles y aceites.
# Seis insumos (gasolina, diésel, aceite 40, aceite 50, aceite hidráulico, coolant). El saldo NUNCA se guarda:
# es entradas − entregas (ver services.resumen), como el kardex de Contabilidad.
from decimal import Decimal

from django.conf import settings
from django.db import models
from simple_history.models import HistoricalRecords

GRUPO_ACCESO  = 'mantenimiento_mecanico'
GRUPO_ALERTAS = 'mantenimiento_mecanico_alertas'
GRUPO_LECTURA = 'mantenimiento_mecanico_lectura'   # <--- hecho por claude code (02-oct-2026): auditoría = ver + comentar
FIRMA_AUDITORA = ('Yeny Lagos', 'Auditora')


class Insumo(models.Model):
    CATEGORIAS = [('combustible', 'Combustible'), ('aceite', 'Aceite')]
    PRESENTACIONES = [('galones', 'Galones (compra suelta)'), ('tanque', 'Tanque'), ('barril', 'Barril')]

    clave        = models.SlugField('Clave', max_length=30, unique=True)
    prefijo      = models.CharField('Prefijo de ficha', max_length=6)
    nombre       = models.CharField('Nombre', max_length=60)
    categoria    = models.CharField('Categoría', max_length=12, choices=CATEGORIAS)
    presentacion = models.CharField('Presentación', max_length=10, choices=PRESENTACIONES)
    # Tanque: capacidad total (diésel 715 gal). Barril: galones por barril (55). Galones sueltos: vacío.
    capacidad_envase = models.DecimalField('Capacidad del envase (gal)', max_digits=8, decimal_places=2, null=True, blank=True)
    minimo_alerta    = models.DecimalField('Mínimo para alertar (gal)', max_digits=8, decimal_places=2, default=Decimal('10'))
    requiere_kilometraje = models.BooleanField('Pide kilometraje', default=False)
    color  = models.CharField('Color', max_length=7, default='#206bc4')
    icono  = models.CharField('Ícono Tabler', max_length=40, default='ti-gas-station')
    orden  = models.PositiveSmallIntegerField('Orden', default=0)
    activo = models.BooleanField('Activo', default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['orden', 'nombre']
        verbose_name = 'Insumo'
        verbose_name_plural = 'Insumos'

    def __str__(self):
        return self.nombre

    @property
    def etiqueta_entrada(self):
        return {'galones': 'Compra de galones', 'tanque': 'Llenado de tanque', 'barril': 'Barril nuevo'}[self.presentacion]


class Maquinaria(models.Model):
    TIPOS = [('vehiculo', 'Vehículo'), ('maquina', 'Máquina'), ('otro', 'Otro')]
    nombre = models.CharField('Nombre', max_length=120, unique=True)
    tipo   = models.CharField('Tipo', max_length=10, choices=TIPOS, default='maquina')
    usa_kilometraje = models.BooleanField('Lleva kilometraje', default=False)
    # <--- hecho por claude code (12-oct-2026): datos de vehículo (para Mantenimiento de vehículos)
    placa  = models.CharField('Placa', max_length=20, blank=True)
    marca  = models.CharField('Marca', max_length=60, blank=True)
    modelo = models.CharField('Modelo', max_length=60, blank=True)
    anio   = models.PositiveSmallIntegerField('Año', null=True, blank=True)
    activo = models.BooleanField('Activo', default=True)
    creado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Maquinaria'
        verbose_name_plural = 'Maquinaria'

    def __str__(self):
        return self.nombre


class Entrada(models.Model):
    """Lo que ENTRA al inventario: compra de galones, llenado del tanque, barril nuevo, saldo inicial o ajuste."""
    TIPOS = [('compra', 'Compra de galones'), ('llenado', 'Llenado de tanque'), ('barril', 'Barril nuevo'),
             ('inicial', 'Saldo inicial'), ('ajuste', 'Ajuste')]
    insumo   = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='entradas')
    fecha    = models.DateField('Fecha')
    cantidad = models.DecimalField('Galones', max_digits=9, decimal_places=2)
    tipo     = models.CharField('Tipo', max_length=10, choices=TIPOS, default='compra')
    observaciones = models.TextField('Observaciones', blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Entrada'
        verbose_name_plural = 'Entradas'

    def __str__(self):
        return f'{self.insumo} +{self.cantidad} gal ({self.fecha})'


class Entrega(models.Model):
    """Lo que SALE: cada formulario de control (entrega de combustible/aceite a una maquinaria)."""
    insumo   = models.ForeignKey(Insumo, on_delete=models.PROTECT, related_name='entregas')
    numero   = models.PositiveIntegerField('Número', default=0)   # correlativo por insumo (services.siguiente_numero)
    fecha    = models.DateField('Fecha')
    hora     = models.TimeField('Hora', null=True, blank=True)
    maquinaria = models.ForeignKey(Maquinaria, null=True, blank=True, on_delete=models.SET_NULL, related_name='entregas')
    # <--- hecho por claude code (12-oct-2026): el DIÉSEL se carga a un vehículo de Mantenimiento de vehículos (su km alimenta el conteo)
    vehiculo   = models.ForeignKey('VehiculoMant', null=True, blank=True, on_delete=models.SET_NULL, related_name='cargas_combustible')
    kilometraje = models.PositiveIntegerField('Kilometraje', null=True, blank=True)
    galones  = models.DecimalField('Galones', max_digits=9, decimal_places=2)
    persona  = models.CharField('Persona que recibe', max_length=120, blank=True)
    observaciones = models.TextField('Observaciones', blank=True)
    firma_responsable = models.CharField('Responsable', max_length=120, blank=True)
    firma_auditora    = models.CharField('Auditora', max_length=120, default=FIRMA_AUDITORA[0])
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    creado = models.DateTimeField(auto_now_add=True)
    modificado = models.DateTimeField(auto_now=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-fecha', '-hora', '-id']
        unique_together = [('insumo', 'numero')]
        verbose_name = 'Entrega'
        verbose_name_plural = 'Entregas'

    @property
    def codigo(self):
        return f'{self.insumo.prefijo}-{self.numero:04d}'

    @property
    def equipo_nombre(self):   # <--- vehículo (diésel) o maquinaria (resto)
        if self.vehiculo_id:
            return self.vehiculo.nombre
        return self.maquinaria.nombre if self.maquinaria_id else ''

    def __str__(self):
        return f'{self.codigo} · {self.galones} gal'


class Comentario(models.Model):
    """<--- hecho por claude code (02-oct-2026): comentario de auditoría sobre una entrega o un servicio (bitácora, no se edita)."""
    entrega = models.ForeignKey(Entrega, null=True, blank=True, on_delete=models.CASCADE, related_name='comentarios')
    # <--- hecho por claude code (12-oct-2026): o un mantenimiento de vehículo (MantenimientoVehiculo.pk, en sponsors2)
    mant_vehic_id = models.IntegerField('Mantenimiento de vehículo', null=True, blank=True, db_index=True)
    autor   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name='+')
    texto   = models.TextField('Comentario')
    creado  = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['creado', 'id']
        verbose_name = 'Comentario de auditoría'
        verbose_name_plural = 'Comentarios de auditoría'

    def __str__(self):
        return f'{self.entrega.codigo if self.entrega_id else ("MV-" + str(self.mant_vehic_id))} · {self.texto[:40]}'


# ═══════════════════════════════════════════════════════════════════════════════════════════════
# MANTENIMIENTO DE VEHÍCULOS (hecho por claude code, 12-oct-2026). Copia de las tablas de Access de AdmonANASQL
# (tblGenVehiculo, tblGenDefTareaMantVehic, tblGenKmActual, tblGenMantVehic, tblGenDefMantVehic) a sponsors2.
# `legacy_id` = el ID de Access, para que la importación sea repetible sin duplicar (manage.py importar_mant_vehiculos).
# Desde el cambio se registra SOLO aquí; Access deja de usarse para esto.
# ═══════════════════════════════════════════════════════════════════════════════════════════════
GRUPO_VEH_REGISTRO = 'vehiculos_registro'          # registra mantenimientos y km (usuario mantenimiento)
GRUPO_VEH_KM       = 'vehiculos_kilometraje'       # registra solo km (jvivas)
GRUPO_VEH_AUDITORIA = 'vehiculos_auditoria'        # solo ve y comenta (Yeny Lagos)
GRUPO_VEH_ALERTAS  = 'vehiculos_alertas'           # recibe el aviso cuando a un vehículo le toca mantenimiento


class VehiculoMant(models.Model):
    legacy_id  = models.IntegerField('ID en Access', unique=True, null=True, blank=True)
    marca      = models.CharField('Marca', max_length=50, blank=True)
    tipo       = models.CharField('Tipo', max_length=50, blank=True)
    color      = models.CharField('Color', max_length=50, blank=True)
    anio       = models.IntegerField('Año', null=True, blank=True)
    placa      = models.CharField('Placa', max_length=20, blank=True)
    chasis     = models.CharField('Chasis', max_length=50, blank=True)
    motor      = models.CharField('Motor', max_length=50, blank=True)
    intervalo  = models.IntegerField('Mantenimiento cada (km u horas)', null=True, blank=True)
    cuenta_diesel = models.CharField('Cuenta diésel', max_length=50, blank=True)   # <--- hecho por claude code (12-oct-2026)
    por_horas  = models.BooleanField('Se mide en horas', default=False)
    millas     = models.BooleanField('Se mide en millas', default=False)
    agricultura = models.BooleanField('Tractor / agrícola', default=False)
    sin_tacometro = models.BooleanField('Sin tacómetro', default=False)
    no_en_uso  = models.BooleanField('Fuera de uso', default=False)
    history = HistoricalRecords()

    class Meta:
        ordering = ['marca', 'tipo']
        verbose_name = 'Vehículo (mantenimiento)'
        verbose_name_plural = 'Vehículos (mantenimiento)'

    @property
    def nombre(self):
        tipo = (self.tipo or '').strip()
        partes = [self.marca, '' if tipo.lower() in ('x', '') else tipo, self.color]
        return ' '.join(p.strip() for p in partes if p and p.strip() and p.strip().lower() != 'x')

    def __str__(self):
        return self.nombre


class TareaMantVehiculo(models.Model):
    legacy_id = models.IntegerField('ID en Access', unique=True, null=True, blank=True)
    numero    = models.IntegerField('Número')
    tarea     = models.CharField('Tarea', max_length=200)
    aplica    = models.CharField('Aplica', max_length=50)           # Todo / Vehic / Tract / Tract/Vehic
    intervalo = models.IntegerField('Intervalo', default=1)          # 1 = cada mantenimiento, 4 = cada cuarto, 8 …
    activo    = models.BooleanField('Activa', default=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['numero', 'id']
        verbose_name = 'Tarea de mantenimiento'
        verbose_name_plural = 'Tareas de mantenimiento'

    def __str__(self):
        return f'{self.numero}. {self.tarea}'


class TecnicoVehiculo(models.Model):
    legacy_id = models.IntegerField('PersonaID en Access', unique=True, null=True, blank=True)
    nombre    = models.CharField('Nombre', max_length=120)
    activo    = models.BooleanField('Activo', default=True)

    class Meta:
        ordering = ['nombre']
        verbose_name = 'Técnico (mantenimiento de vehículos)'
        verbose_name_plural = 'Técnicos (mantenimiento de vehículos)'

    def __str__(self):
        return self.nombre


class LecturaVehiculo(models.Model):
    legacy_id = models.IntegerField('ID en Access', unique=True, null=True, blank=True)
    vehiculo  = models.ForeignKey(VehiculoMant, on_delete=models.PROTECT, related_name='lecturas')
    valor     = models.BigIntegerField('Km u horas')
    fecha     = models.DateField('Fecha')
    usuario   = models.CharField('Usuario (Access)', max_length=50, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    creado    = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Lectura de km / horas'
        verbose_name_plural = 'Lecturas de km / horas'


class MantenimientoVehiculo(models.Model):
    legacy_id = models.IntegerField('ID en Access', unique=True, null=True, blank=True)
    vehiculo  = models.ForeignKey(VehiculoMant, on_delete=models.PROTECT, related_name='mantenimientos')
    tecnico   = models.ForeignKey(TecnicoVehiculo, null=True, blank=True, on_delete=models.PROTECT, related_name='mantenimientos')
    valor     = models.BigIntegerField('Km u horas')
    fecha     = models.DateField('Fecha')
    usuario   = models.CharField('Usuario (Access)', max_length=50, blank=True)
    registrado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    creado    = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-fecha', '-id']
        verbose_name = 'Mantenimiento de vehículo'
        verbose_name_plural = 'Mantenimientos de vehículos'


class MantenimientoVehiculoTarea(models.Model):
    legacy_id = models.IntegerField('ID en Access', unique=True, null=True, blank=True)
    mantenimiento = models.ForeignKey(MantenimientoVehiculo, on_delete=models.CASCADE, related_name='tareas')
    tarea     = models.ForeignKey(TareaMantVehiculo, on_delete=models.PROTECT, related_name='+')
    hecho     = models.BooleanField('Hecho', default=False)

    class Meta:
        ordering = ['tarea__numero', 'id']
        verbose_name = 'Tarea de un mantenimiento'
        verbose_name_plural = 'Tareas de un mantenimiento'
