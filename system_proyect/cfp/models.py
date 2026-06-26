from django.db import models

# ── Talleres (subdashboards) ──────────────────────────────────────────────────
TALLER_CHOICES = [
    ('belleza',     'Belleza'),
    ('computacion', 'Computación'),
    ('panaderia',   'Panadería / Repostería'),
    ('mecanica',    'Mecánica Automotriz'),
]
TALLER_LABEL = dict(TALLER_CHOICES)

# Distribución fija
PCT_SEGURO = 0.60   # Seguro, Materiales, Mantenimiento
PCT_INSTR  = 0.20   # Instructores y director
PCT_ADMIN  = 0.20   # Administración

# ── Estructura fija de egresos del informe (Tab 3) ───────────────────────────
EGRESO_GRUPOS = [
    ('personal', 'Gastos de Personal', [
        ('instructor', 'Instructor'), ('encargado', 'Encargado del centro'),
        ('apoyo', 'Personal de apoyo')]),
    ('materia', 'Materia Prima y Material Didáctico', [
        ('materiales', 'Materiales'), ('manual', 'Manual'), ('disketes', 'Disketes'),
        ('papel', 'Papel'), ('marcadores', 'Marcadores'), ('otros', 'Otros')]),
    ('amortizacion', 'Amortización y Depreciación', [
        ('equipos', 'Equipos'), ('maquinaria', 'Maquinarias'), ('instalaciones', 'Instalaciones')]),
    ('mantenimiento', 'Mantenimiento', [
        ('equipos', 'Equipos'), ('maquinaria', 'Maquinaria'), ('instalaciones', 'Instalaciones')]),
    ('administracion', 'Gastos de Administración', [
        ('electricidad', 'Electricidad'), ('telefono', 'Teléfono'), ('agua', 'Agua'),
        ('alquileres', 'Alquileres'),
        ('seguro', 'Seguro de Accidentes Personales (participantes)'), ('otros', 'Otros')]),
]


class EjecucionCurso(models.Model):
    anio         = models.PositiveSmallIntegerField('Año', default=2025, db_index=True)
    taller       = models.CharField('Taller', max_length=20, choices=TALLER_CHOICES)
    taller_anio  = models.PositiveSmallIntegerField('Año del taller (Mecánica: 1 o 2)', null=True, blank=True)
    no_ejecucion = models.CharField('No. de Ejecución', max_length=40, blank=True)
    no_curso     = models.CharField('No. del Curso', max_length=40, blank=True)
    no_contrato  = models.CharField('No. de Contrato', max_length=60, blank=True)
    nombre_curso = models.CharField('Nombre del Curso', max_length=120)
    horas        = models.PositiveIntegerField('Horas', default=0)
    part_inicial = models.PositiveIntegerField('Participantes inicial', default=0)
    part_pago    = models.PositiveIntegerField('Participantes final', default=0)
    costo_hora   = models.DecimalField('Costo por Hora', max_digits=8, decimal_places=2, default=0)
    horario      = models.CharField('Horario', max_length=80, blank=True)
    creado       = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['anio', 'taller', 'no_ejecucion', 'id']
        verbose_name = 'Ejecución de Curso'
        verbose_name_plural = 'Ejecuciones de Curso'

    def __str__(self):
        return f"{self.no_ejecucion or self.id} – {self.nombre_curso}"

    # ── Cálculos (Tab 1) ──
    @property
    def monto_contrato(self):
        return round(self.horas * self.part_pago * float(self.costo_hora), 2)

    @property
    def perdida(self):
        return round(self.horas * max(0, self.part_inicial - self.part_pago) * float(self.costo_hora), 2)

    @property
    def anticipo(self):
        return round(self.monto_contrato * 0.5, 2)

    @property
    def cancelacion(self):
        return round(self.monto_contrato * 0.5 - self.perdida, 2)

    @property
    def costo_real(self):
        return round(self.anticipo + self.cancelacion, 2)

    @property
    def monto_cfp(self):
        return self.costo_real

    # ── Distribución (Tab 2) ──
    @property
    def dist_seguro(self):
        return round(self.monto_cfp * PCT_SEGURO, 2)

    @property
    def dist_instr(self):
        return round(self.monto_cfp * PCT_INSTR, 2)

    @property
    def dist_admin(self):
        return round(self.monto_cfp * PCT_ADMIN, 2)


class InformeContable(models.Model):
    """Informe contable (Tab 3) — uno por ejecución."""
    ejecucion       = models.OneToOneField(EjecucionCurso, on_delete=models.CASCADE, related_name='informe')
    localidad       = models.CharField(max_length=200, blank=True)
    direccion       = models.CharField(max_length=300, blank=True)
    fecha_inicio    = models.DateField(null=True, blank=True)
    fecha_fin       = models.DateField(null=True, blank=True)
    convenio        = models.CharField(max_length=60, blank=True)
    instructor      = models.CharField(max_length=200, blank=True)
    regional        = models.CharField(max_length=20, blank=True)
    centro_programa = models.CharField(max_length=40, blank=True)
    horario         = models.CharField(max_length=80, blank=True)
    lugar_fecha     = models.CharField('Lugar y fecha', max_length=300, blank=True)  # (legado)
    lugar           = models.CharField('Lugar', max_length=300, blank=True)
    fecha_lugar     = models.DateField('Fecha (lugar y fecha)', null=True, blank=True)
    egresados       = models.PositiveIntegerField('Participantes egresados', default=0)
    # Egresos planos: {'personal_instructor': 20475.0, ...}
    egresos         = models.JSONField(default=dict, blank=True)
    actualizado     = models.DateTimeField(auto_now=True)

    def grupo_subtotal(self, grupo):
        keys = [k for g, _, items in EGRESO_GRUPOS if g == grupo for k, _ in items]
        return round(sum(float(self.egresos.get(f'{grupo}_{k}', 0) or 0) for k in keys), 2)

    @property
    def total_egresos(self):
        return round(sum(float(v or 0) for v in (self.egresos or {}).values()), 2)

    @property
    def ingreso_neto(self):
        return self.ejecucion.costo_real

    @property
    def utilidad(self):
        return round(self.ingreso_neto - self.total_egresos, 2)


class CfpDatosGenerales(models.Model):
    """Datos generales COMPARTIDOS por todos los informes/cursos (registro único id=1)."""
    localidad   = models.CharField(max_length=300, blank=True, default='')
    direccion   = models.CharField(max_length=300, blank=True, default='')
    instructor  = models.CharField(max_length=300, blank=True, default='')
    horario     = models.CharField(max_length=80,  blank=True, default='')
    lugar       = models.CharField(max_length=300, blank=True, default='')
    fecha_lugar = models.DateField(null=True, blank=True)

    def __str__(self):
        return 'Datos generales CFP (compartidos)'


class CfpOpcion(models.Model):
    """Catálogo de opciones reutilizables para campos del informe (selects agregables)."""
    campo = models.CharField(max_length=20)   # localidad | direccion | instructor | horario | lugar
    valor = models.CharField(max_length=300)

    class Meta:
        unique_together = ('campo', 'valor')
        ordering = ['valor']

    def __str__(self):
        return f"{self.campo}: {self.valor}"
