from django.db import models
from simple_history.models import HistoricalRecords   # <--- hecho por claude code (30-sep-2026): auditoría de Notas CFP
from django.conf import settings

# ── Talleres (subdashboards) ──────────────────────────────────────────────────
TALLER_CHOICES = [
    ('belleza',     'Belleza'),
    ('computacion', 'Computación'),
    ('panaderia',   'Panadería / Repostería'),
    ('mecanica',    'Mecánica Automotriz'),
]
TALLER_LABEL = dict(TALLER_CHOICES)

# Distribución fija
PCT_SEGURO = 0.60   # Materia Prima y Mantenimiento
PCT_INSTR  = 0.20   # Instructores y director
PCT_ADMIN  = 0.20   # Administración

# ── Estructura fija de egresos del informe (Tab 3) ───────────────────────────
# <--- hecho por claude code: los 3 grupos calcan la distribución 20/60/20 del curso.
# Se fusionaron "Materia Prima y Material Didáctico" + "Mantenimiento" en el 60% y
# se eliminó "Amortización y Depreciación".
EGRESO_GRUPOS = [
    ('personal', 'Gastos de Personal', [
        ('instructor', 'Instructor'), ('encargado', 'Encargado del centro'),
        ('apoyo', 'Personal de apoyo'),
        # <--- hecho por claude code (pedido del usuario 09-sep-2026): gastos y viáticos del personal
        ('viaticos', 'Gastos y viáticos')]),
    ('materia', 'Materia Prima y Mantenimiento', [
        # <--- hecho por claude code: "Disketes" del formulario viejo pasó a "Imprevistos"
        ('materiales', 'Materiales'), ('manual', 'Manual'), ('imprevistos', 'Imprevistos'),
        # <--- hecho por claude code (09-sep-2026): Papel y Marcadores pasaron a Administración;
        # el Seguro de Accidentes Personales vino de Administración a este grupo (60%).
        ('seguro', 'Seguro de Accidentes Personales (participantes)'),
        ('equipos', 'Equipos'), ('maquinaria', 'Maquinaria'), ('instalaciones', 'Instalaciones'),
        # <--- hecho por claude code (10-sep-2026): casilla "Mantenimiento" pedida por el usuario
        ('mantenimiento', 'Mantenimiento'),
        ('otros', 'Otros')]),
    ('administracion', 'Gastos de Administración', []),   # se rellena abajo
]

# ── Grupo de Administración: dos naturalezas distintas ───────────────────────
# <--- hecho por claude code: primero se CAPTURAN teléfono/papel/marcadores/otros y lo
# que queda del 20% es el DISPONIBLE para la PLANILLA. Desde el 09-sep-2026 el monto de
# cada persona se escribe A MANO (ya no se reparte automático); los cargos del informe
# se siguen escribiendo desde la planilla (sincronizar_cargos).
CARGOS_ADMIN = [
    ('administracion', 'Administración'), ('contador', 'Contador'),
    ('asistente', 'Asistente Administrativo'), ('soporte', 'Soporte Técnico'),
    ('vigilancia', 'Vigilancia'), ('auditor', 'Auditor'),
]
ADMIN_CAPTURADOS = [
    ('telefono', 'Teléfono'),
    # <--- hecho por claude code (09-sep-2026): Papel y Marcadores vinieron de Materia Prima;
    # el Seguro se fue a Materia Prima y Mantenimiento.
    ('papel', 'Papel'), ('marcadores', 'Marcadores'),
    ('otros', 'Otros'),
]
CARGO_LABEL = dict(CARGOS_ADMIN)
_CLAVES_CARGO     = [k for k, _ in CARGOS_ADMIN]
_CLAVES_CAPTURADO = [k for k, _ in ADMIN_CAPTURADOS]

# El informe conserva el orden visual: cargos primero, luego lo capturado.
EGRESO_GRUPOS[2] = ('administracion', 'Gastos de Administración',
                    CARGOS_ADMIN + ADMIN_CAPTURADOS)

# <--- hecho por claude code: a qué porcentaje del curso corresponde cada grupo
EGRESO_GRUPO_PCT = {
    'personal':       (PCT_INSTR,  'Instructores y Director'),
    'materia':        (PCT_SEGURO, 'Materia Prima y Mantenimiento'),
    'administracion': (PCT_ADMIN,  'Administración'),
}


import re  # <--- hecho por claude code: para leer el correlativo del No. de Ejecución

# ── Código automático de ejecución: CFP-ANA-<correlativo>-<año> ───────────────
# <--- hecho por claude code: el correlativo es de 3 dígitos y se REINICIA cada año;
# el sufijo son los 2 últimos dígitos del año (2026 -> 26).
NO_EJEC_PREFIJO = 'CFP-ANA-'
_RE_NO_EJEC = re.compile(r'^CFP-ANA-(\d{3})-(\d{2})$')


def generar_no_ejecucion(anio):
    """Siguiente código libre del año: CFP-ANA-001-26, CFP-ANA-002-26…

    Solo mira los códigos con el formato nuevo, así los antiguos escritos a mano
    (ej. ANA-RC-2025-005) se respetan y no estorban la numeración.
    """
    sufijo = f'{anio % 100:02d}'
    usados = set()
    for codigo in (EjecucionCurso.objects
                   .filter(no_ejecucion__startswith=NO_EJEC_PREFIJO)
                   .values_list('no_ejecucion', flat=True)):
        m = _RE_NO_EJEC.match(codigo or '')
        if m and m.group(2) == sufijo:
            usados.add(int(m.group(1)))
    n = 1
    while n in usados:          # salta huecos por si se borró un curso intermedio
        n += 1
    return f'{NO_EJEC_PREFIJO}{n:03d}-{sufijo}'


class EjecucionCurso(models.Model):
    anio         = models.PositiveSmallIntegerField('Año', default=2025, db_index=True)
    taller       = models.CharField('Taller', max_length=20, choices=TALLER_CHOICES)
    taller_anio  = models.PositiveSmallIntegerField('Año del taller (Mecánica: 1 o 2)', null=True, blank=True)
    no_ejecucion = models.CharField('N° de Expediente', max_length=40, blank=True)
    no_curso     = models.CharField('No. del Curso', max_length=40, blank=True)
    no_contrato  = models.CharField('No. de Contrato', max_length=60, blank=True)
    nombre_curso = models.CharField('Nombre del Curso', max_length=120)
    horas        = models.PositiveIntegerField('Horas', default=0)
    part_inicial = models.PositiveIntegerField('Participantes inicial', default=0)
    part_pago    = models.PositiveIntegerField('Participantes final', default=0)
    costo_hora   = models.DecimalField('Costo por Hora', max_digits=8, decimal_places=2, default=0)
    horario      = models.CharField('Horario', max_length=80, blank=True)
    creado       = models.DateTimeField(auto_now_add=True)

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

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

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

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

    # ── Planilla de gastos administrativos ──────────────────────────────────
    # <--- hecho por claude code: el 20% NO se reparte entero. Primero se descuenta
    # lo que ya está determinado (teléfono, papel, marcadores, otros); lo que queda es el
    # DISPONIBLE para la planilla. El monto por persona se escribe a mano (09-sep-2026).
    @property
    def admin_capturado(self):
        """Teléfono + Papel + Marcadores + Otros: lo que se escribe a mano y no se reparte."""
        return round(sum(float(self.egresos.get(f'administracion_{k}', 0) or 0)
                         for k in _CLAVES_CAPTURADO), 2)

    @property
    def admin_a_repartir(self):
        """Lo que queda del 20% de Administración para la planilla."""
        return round(self.ejecucion.dist_admin - self.admin_capturado, 2)

    def reparto_planilla(self):
        """[(persona, monto)] con el monto ESCRITO A MANO en cada persona.
        <--- hecho por claude code (09-sep-2026): ya no se reparte en partes iguales."""
        return [(p, round(float(p.monto or 0), 2)) for p in self.ejecucion.planilla.all()]

    @property
    def total_repartido(self):
        """Suma de los montos escritos en la planilla (para compararlo con el disponible)."""
        return round(sum(m for _, m in self.reparto_planilla()), 2)

    def sincronizar_cargos(self, guardar=True):
        """Vuelca el reparto de la planilla en los egresos del informe (por cargo)."""
        eg = dict(self.egresos or {})
        for k in _CLAVES_CARGO:
            eg.pop(f'administracion_{k}', None)
        for persona, monto in self.reparto_planilla():
            clave = f'administracion_{persona.cargo}'
            eg[clave] = round(eg.get(clave, 0) + monto, 2)
        self.egresos = eg
        if guardar:
            self.save(update_fields=['egresos'])
        return eg


class GastoAdministrativo(models.Model):
    """<--- hecho por claude code: una persona de la planilla administrativa de un curso.

    El MONTO se escribe a mano por persona (pedido del usuario 09-sep-2026; antes se
    repartía automáticamente en partes iguales el resto del 20%). La pantalla muestra el
    "disponible" (20% − capturados) solo como referencia para que cuadre.
    """
    ejecucion = models.ForeignKey(EjecucionCurso, on_delete=models.CASCADE, related_name='planilla')
    nombre    = models.CharField('Nombre completo', max_length=200)
    dni       = models.CharField('DNI', max_length=30, blank=True, default='')
    cargo     = models.CharField('Cargo', max_length=40, choices=CARGOS_ADMIN)
    orden     = models.PositiveSmallIntegerField(default=0)
    # <--- hecho por claude code (09-sep-2026): monto editable, ya no automático
    monto     = models.DecimalField('Monto', max_digits=10, decimal_places=2, default=0)

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        ordering = ['orden', 'id']
        verbose_name        = 'Planilla administrativa'
        verbose_name_plural = 'Planilla administrativa'

    def __str__(self):
        return f'{self.nombre} — {self.get_cargo_display()}'



class PersonaCargoPlanilla(models.Model):
    """<--- hecho por claude code (09-sep-2026): quién ocupa cada cargo administrativo.

    Catálogo que se mantiene desde el admin. En la planilla, al elegir el cargo se
    rellenan solos el nombre y el DNI de la persona registrada aquí (pedido del usuario).
    """
    cargo  = models.CharField('Cargo', max_length=40, choices=CARGOS_ADMIN, unique=True)
    nombre = models.CharField('Nombre completo', max_length=200, blank=True)
    dni    = models.CharField('DNI', max_length=30, blank=True)

    class Meta:
        verbose_name = 'Persona por cargo (planilla)'
        verbose_name_plural = 'Personas por cargo (planilla)'
        ordering = ['cargo']

    def __str__(self):
        return f'{self.get_cargo_display()}: {self.nombre or "(sin asignar)"}'

    @classmethod
    def mapa(cls):
        """{cargo: {'nombre','dni'}} solo de los cargos que ya tienen persona."""
        return {p.cargo: {'nombre': p.nombre, 'dni': p.dni}
                for p in cls.objects.all() if (p.nombre or '').strip()}

class CfpDatosGenerales(models.Model):
    """Datos generales COMPARTIDOS por todos los informes/cursos (registro único id=1)."""
    localidad   = models.CharField(max_length=300, blank=True, default='')
    direccion   = models.CharField(max_length=300, blank=True, default='')
    instructor  = models.CharField(max_length=300, blank=True, default='')
    horario     = models.CharField(max_length=80,  blank=True, default='')
    lugar       = models.CharField(max_length=300, blank=True, default='')
    fecha_lugar = models.DateField(null=True, blank=True)
    # <--- hecho por claude code: son del CENTRO, iguales para todos los cursos.
    # En el informe se muestran de solo lectura; se cambian desde el admin.
    regional        = models.CharField('Regional', max_length=20, blank=True, default='01')
    centro_programa = models.CharField('Centro-Programa-Proyecto', max_length=40,
                                       blank=True, default='6400')

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


# ══════════════════════════════════════════════════════════════════════════════
#  PROGRAMA 2 — SISTEMA DE NOTAS CFP
#  (4 vistas/tabs por curso: Progreso · Compilación · Módulos · Horas)
# ══════════════════════════════════════════════════════════════════════════════

# Teórico aprobado = nota ≥ 90 (la fórmula del Excel usa > 89)
NOTA_APROBADO = 90
# Práctico aprobado = 100 (el máximo); si es menos, reprobado
NOTA_APROBADO_PRACTICO = 100
# Meses de la formación: Febrero (2) … Noviembre (11)
MESES_FORMACION = [2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
MES_LABEL = {2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
             7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre'}


def _primer_aprobado(intentos, umbral=NOTA_APROBADO):
    """Devuelve el primer intento que aprueba (≥ umbral); si ninguno pasa → 0."""
    for v in intentos:
        if v is not None and float(v) >= umbral:
            return float(v)
    return 0.0


JORNADA_CHOICES = [('unica', 'Única'), ('matutina', 'Matutina'), ('vespertina', 'Vespertina')]
JORNADA_LABEL = dict(JORNADA_CHOICES)


class CursoNota(models.Model):
    """Un curso técnico (año, jornada) con sus módulos, notas y horas. La 'app' del Programa 2."""
    anio    = models.PositiveSmallIntegerField('Año', default=2026, db_index=True)
    curso   = models.CharField('Curso', max_length=160)   # = tc.Descripcion (SQL Server)
    jornada = models.CharField('Jornada', max_length=12, choices=JORNADA_CHOICES, default='unica')
    codigo  = models.CharField('Prefijo de código de módulo', max_length=20, blank=True, default='')

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        unique_together = ('anio', 'curso', 'jornada')
        ordering = ['curso', 'jornada']
        verbose_name = 'Curso (Notas)'
        verbose_name_plural = 'Cursos (Notas)'

    def __str__(self):
        j = '' if self.jornada == 'unica' else f" · {JORNADA_LABEL[self.jornada]}"
        return f"{self.curso}{j} ({self.anio})"

    @property
    def prefijo(self):
        return self.codigo or 'M'


class Participante(models.Model):
    """Roster de alumnos asignado a un grupo/jornada (cuando SQL Server no separa grupos)."""
    curso      = models.ForeignKey(CursoNota, on_delete=models.CASCADE, related_name='participantes')
    persona_id = models.IntegerField()
    nombre     = models.CharField(max_length=200, blank=True, default='')
    identidad  = models.CharField(max_length=40, blank=True, default='')
    sub_grupo  = models.CharField(max_length=20, blank=True, default='')
    orden      = models.PositiveSmallIntegerField(default=0)

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        unique_together = ('curso', 'persona_id')
        ordering = ['orden', 'nombre']

    def __str__(self):
        return self.nombre


class ModuloNota(models.Model):
    """Módulo/unidad de un curso. Define el código, puntaje y fechas (modal del instructor)."""
    curso        = models.ForeignKey(CursoNota, on_delete=models.CASCADE, related_name='modulos')
    numero       = models.PositiveSmallIntegerField('No.')
    codigo       = models.CharField('Código', max_length=40, blank=True, default='')
    puntaje      = models.DecimalField('Puntaje', max_digits=6, decimal_places=2, default=100)
    fecha_inicio = models.DateField('Fecha inicio', null=True, blank=True)
    fecha_fin    = models.DateField('Fecha final', null=True, blank=True)

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        unique_together = ('curso', 'numero')
        ordering = ['numero']
        verbose_name = 'Módulo'
        verbose_name_plural = 'Módulos'

    def __str__(self):
        return self.codigo or f"Módulo {self.numero}"

    @property
    def codigo_auto(self):
        return self.codigo or f"{self.curso.prefijo}-{self.numero:02d}"


class NotaIntento(models.Model):
    """Notas por intento de un participante en un módulo (Tab 1 · lo llena el instructor)."""
    modulo     = models.ForeignKey(ModuloNota, on_delete=models.CASCADE, related_name='notas')
    persona_id = models.IntegerField(db_index=True)
    nombre     = models.CharField(max_length=200, blank=True, default='')
    identidad  = models.CharField(max_length=40, blank=True, default='')
    t1 = models.DecimalField('Teórico 1', max_digits=5, decimal_places=2, null=True, blank=True)
    t2 = models.DecimalField('Teórico 2', max_digits=5, decimal_places=2, null=True, blank=True)
    t3 = models.DecimalField('Teórico 3', max_digits=5, decimal_places=2, null=True, blank=True)
    p1 = models.DecimalField('Práctico 1', max_digits=5, decimal_places=2, null=True, blank=True)
    p2 = models.DecimalField('Práctico 2', max_digits=5, decimal_places=2, null=True, blank=True)
    p3 = models.DecimalField('Práctico 3', max_digits=5, decimal_places=2, null=True, blank=True)

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        unique_together = ('modulo', 'persona_id')
        verbose_name = 'Nota por intento'
        verbose_name_plural = 'Notas por intento'

    @property
    def teoricos(self):
        return [self.t1, self.t2, self.t3]

    @property
    def practicos(self):
        return [self.p1, self.p2, self.p3]

    @property
    def teorico_compilado(self):
        return _primer_aprobado(self.teoricos)

    @property
    def practico_compilado(self):
        return _primer_aprobado(self.practicos, NOTA_APROBADO_PRACTICO)

    @property
    def resultado_modulo(self):
        """(Teórico compilado + Práctico compilado) / 2 (Tab 3)."""
        return round((self.teorico_compilado + self.practico_compilado) / 2, 2)


class HorasMetaMes(models.Model):
    """Horas-meta por mes (la jornada que define el DIRECTOR · Tab 4)."""
    curso = models.ForeignKey(CursoNota, on_delete=models.CASCADE, related_name='horas_meta')
    mes   = models.PositiveSmallIntegerField()  # 2..11 (Febrero..Noviembre)
    horas = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        unique_together = ('curso', 'mes')
        ordering = ['mes']


class HorasParticipanteMes(models.Model):
    """Horas reales por mes de cada participante (las llena el INSTRUCTOR · Tab 4)."""
    curso      = models.ForeignKey(CursoNota, on_delete=models.CASCADE, related_name='horas_part')
    persona_id = models.IntegerField(db_index=True)
    mes        = models.PositiveSmallIntegerField()
    horas      = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        unique_together = ('curso', 'persona_id', 'mes')
        ordering = ['persona_id', 'mes']


# ─────────────────────────────────────────────────────────────
# Asignación instructor → curso (Programa 2 / Notas)
# <--- hecho por claude code: cada instructor ve/edita solo SUS cursos.
# El director y el superusuario ven todos (no necesitan filas aquí).
# ─────────────────────────────────────────────────────────────
class InstructorCurso(models.Model):
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name='cfp_cursos', verbose_name='Instructor',
    )
    curso = models.CharField('Curso', max_length=160)   # una clave de CURSOS_CFP

    history = HistoricalRecords()   # <--- hecho por claude code (30-sep-2026): auditoría

    class Meta:
        verbose_name = 'Instructor – Curso CFP'
        verbose_name_plural = 'Instructores – Cursos CFP'
        unique_together = ('instructor', 'curso')
        ordering = ['instructor__username', 'curso']

    def __str__(self):
        return f'{self.instructor} → {self.curso}'
