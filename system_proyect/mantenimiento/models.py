import uuid

from django.db import models
from core.models import AuditModel


class TipoFalla(AuditModel):
    nombre = models.CharField(max_length=100, verbose_name="Tipo de Falla")

    class Meta:
        db_table = 'tipo_falla'
        verbose_name = "Tipo de Falla"
        verbose_name_plural = "Tipos de Falla"

    def __str__(self):
        return self.nombre


class MaestroMantenimiento(models.Model):
    nombre = models.CharField("Nombre", max_length=150, unique=True)

    class Meta:
        verbose_name = "Maestro"
        verbose_name_plural = "Maestros"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class GradoMantenimiento(models.Model):
    nombre = models.CharField("Nombre", max_length=100, unique=True)

    class Meta:
        verbose_name = "Grado"
        verbose_name_plural = "Grados"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class MaintenanceRecord(AuditModel):
    # <--- hecho por claude code: registro polimórfico computadora / impresora
    TIPO_EQUIPO_CHOICES = [
        ('computadora', 'Computadora'),
        ('impresora',   'Impresora'),
        ('control',     'Control de equipo'),   # <--- hecho por claude code: evaluación periódica del equipo del maestro
        ('inspeccion',  'Inspección'),          # <--- hecho por claude code: inspección del espacio de trabajo (checklist)
        # <--- hecho por claude code (17-sep-2026): movimientos de equipo (mismo checklist en los dos sentidos)
        ('entrega',     'Entrega de equipo'),   # soporte técnico ENTREGA al usuario
        ('recogida',    'Recogida de equipo'),  # soporte técnico RECIBE del usuario
        # <--- hecho por claude code (28-sep-2026): recogida por CASO ESPECIAL, nace desde un Control de equipo (checkbox al crearlo)
        ('caso_especial', 'Caso especial'),
        # <--- hecho por claude code (28-sep-2026): cambio de equipo (nace desde un Control: equipo anterior → equipo nuevo)
        ('cambio_equipo', 'Cambio de equipo'),
        # <--- hecho por claude code (12-oct-2026): REASIGNACIÓN — la misma computadora pasa del maestro A al maestro B (nace desde un Control)
        ('reasignacion', 'Reasignación de computadora'),
    ]
    # <--- hecho por claude code (17-sep-2026): checklist de Entrega/Recogida: (campo, texto en entrega, texto en recogida)
    MOVIMIENTO_ITEMS = [
        ('ent_equipo',        'Se entrega el equipo',                                   'Se recibe el equipo'),
        ('ent_mouse_teclado', 'Se le entrega mouse y teclado',                          'Se recibe mouse y teclado'),
        ('ent_televisor',     'Se le entrega televisor',                                'Se recibe televisor'),
        ('ent_control_tv',    'Se le entrega control del televisor más batería',        'Se recibe control del televisor más batería'),
    ]
    # <--- hecho por claude code: checklist de la Inspección (checkbox = Sí, sin marcar = No)
    INSPECCION_ITEMS = [
        ('insp_limpio',    '1. ¿Mantiene limpio el espacio de trabajo?'),
        ('insp_ordenado',  '2. ¿Tiene ordenado el espacio de trabajo?'),
        ('insp_cables',    '3. ¿Los cables del equipo están ordenados y en buen estado?'),
        ('insp_alimentos', '4. ¿El equipo está libre de comida y bebidas cerca?'),
    ]
    # <--- hecho por claude code: Control de equipo — preguntas de evaluación al maestro
    EVAL_TRABAJO_CHOICES = [
        ('excelente', 'Excelente'),
        ('bien',      'Bien'),
        ('regular',   'Regular'),
        ('mal',       'Mal'),
    ]
    EVAL_FALLAS_CHOICES = [
        ('no', 'No'),
        ('si', 'Sí'),
    ]
    # Estado del EQUIPO (solo control): condición física/funcional, no el avance del trámite
    ESTADO_EQUIPO_CHOICES = [
        ('bueno',   'Buen estado'),
        ('regular', 'Regular'),
        ('malo',    'Mal estado'),
        ('fuera',   'Fuera de servicio'),
    ]
    # Firmas FIJAS del control de equipo (no se dibujan; van impresas en la ficha)
    FIRMA_TECNICO_FIJA  = ('Josué Fellmann', 'Soporte Técnico')
    FIRMA_AUDITORA_FIJA = ('Yeny Lagos', 'Auditora')
    TIPO_MANT_IMPRESORA_CHOICES = [
        ('llenado_tinta',         'Llenado de tinta'),
        ('actualizacion_sistema', 'Actualización de sistema'),
    ]
    ESTADO_TINTA_CHOICES = [
        ('vacio', 'Vacío'),
        ('media', 'Media'),
        ('llena', 'Llena'),
        ('full',  'Full'),
    ]
    TIPO_TINTA_CHOICES = [
        ('544', '544'),
        ('504', '504'),
    ]

    record_id    = models.CharField("ID Registro", max_length=20, unique=True, blank=True)
    tipo_equipo  = models.CharField("Tipo de equipo", max_length=20, choices=TIPO_EQUIPO_CHOICES, default='computadora')
    computadora  = models.ForeignKey(
        'inventario.Computadora',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Computadora"
    )
    impresora    = models.ForeignKey(
        'inventario.Impresora',
        on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Impresora"
    )
    model        = models.CharField("Modelo", max_length=100, blank=True)
    serie        = models.CharField("Serie", max_length=100, blank=True)
    teacher_name = models.CharField("Nombre del Maestro", max_length=150, blank=True)
    grade        = models.CharField("Grado", max_length=100, blank=True)
    area         = models.CharField("Área", max_length=100, blank=True)  # <--- hecho por claude code: área manual (impresora)
    tipo_falla   = models.ForeignKey(TipoFalla, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Tipo de Falla")
    # <--- hecho por claude code: campos específicos de mantenimiento de impresora
    tipo_mant_impresora = models.CharField("Tipo de mantenimiento (impresora)", max_length=30, choices=TIPO_MANT_IMPRESORA_CHOICES, blank=True)
    estado_tinta = models.CharField("Estado de la tinta", max_length=10, choices=ESTADO_TINTA_CHOICES, blank=True)
    tinta_negra    = models.BooleanField("Tinta negra rellenada", default=False)
    tinta_magenta  = models.BooleanField("Tinta magenta rellenada", default=False)
    tinta_amarillo = models.BooleanField("Tinta amarillo rellenada", default=False)
    tinta_cyan     = models.BooleanField("Tinta cyan rellenada", default=False)
    tipo_tinta   = models.CharField("Tipo de tinta", max_length=10, choices=TIPO_TINTA_CHOICES, blank=True)
    # <--- hecho por claude code: campos del Control de equipo (tipo_equipo='control')
    eval_trabajo        = models.CharField("¿Qué tal ha trabajado su equipo de trabajo?", max_length=12, choices=EVAL_TRABAJO_CHOICES, blank=True)
    eval_fallas         = models.CharField("¿Le ha presentado fallas su equipo de trabajo?", max_length=2, choices=EVAL_FALLAS_CHOICES, blank=True)
    eval_fallas_detalle = models.TextField("¿Cuáles fallas?", blank=True)
    obs_auditora        = models.TextField("Observaciones de la auditora", blank=True)
    obs_tecnico         = models.TextField("Observaciones del técnico", blank=True)
    estado_equipo       = models.CharField("Estado del equipo", max_length=10, choices=ESTADO_EQUIPO_CHOICES, blank=True)
    # <--- hecho por claude code: respuestas de la Inspección
    insp_limpio    = models.BooleanField("Mantiene limpio el espacio de trabajo", default=False)
    insp_ordenado  = models.BooleanField("Tiene ordenado el espacio de trabajo", default=False)
    insp_cables    = models.BooleanField("Cables ordenados y en buen estado", default=False)
    insp_alimentos = models.BooleanField("Libre de comida y bebidas cerca", default=False)
    # <--- hecho por claude code (17-sep-2026): Entrega / Recogida de equipo
    ent_equipo        = models.BooleanField("Equipo (computadora)", default=False)
    ent_mouse_teclado = models.BooleanField("Mouse y teclado", default=False)
    ent_televisor     = models.BooleanField("Televisor", default=False)
    ent_control_tv    = models.BooleanField("Control del televisor más batería", default=False)
    televisor    = models.ForeignKey('inventario.Televisor', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='movimientos_mantenimiento', verbose_name="Televisor")
    firma_nombre = models.CharField("Firma (nombre escrito por el usuario)", max_length=150, blank=True)
    # <--- hecho por claude code (28-sep-2026): control que originó el caso especial (se conserva si el control se borra)
    control_origen = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='casos_especiales',
                                       verbose_name='Control de origen (caso especial)')
    # <--- hecho por claude code (28-sep-2026): CAMBIO DE EQUIPO. El Asset ID se queda con el maestro; cambia el hardware.
    # La ficha guarda el ANTES (lo que tenía la computadora) y el DESPUÉS (lo que se registró como equipo nuevo);
    # la computadora del inventario se actualiza con los datos nuevos y su historial conserva los anteriores.
    modelo_anterior = models.CharField('Modelo anterior', max_length=100, blank=True)
    serie_anterior  = models.CharField('Serie anterior', max_length=100, blank=True)
    ip_anterior     = models.CharField('IP anterior', max_length=50, blank=True)
    modelo_nuevo    = models.CharField('Modelo nuevo', max_length=100, blank=True)
    serie_nuevo     = models.CharField('Serie nueva', max_length=100, blank=True)
    ip_nuevo        = models.CharField('IP nueva', max_length=50, blank=True)
    # <--- hecho por claude code (12-oct-2026): REASIGNACIÓN. La computadora (mismo Asset ID y hardware) cambia de dueño.
    # La ficha guarda a quién estaba asignada (A) y a quién pasa (B); el inventario se actualiza y su historial conserva A.
    asignado_anterior = models.CharField('Asignado anterior', max_length=150, blank=True)
    area_anterior     = models.CharField('Área anterior', max_length=100, blank=True)
    grado_anterior    = models.CharField('Grado anterior', max_length=50, blank=True)
    edificio_anterior = models.CharField('Edificio anterior', max_length=100, blank=True)
    asignado_nuevo    = models.CharField('Asignado nuevo', max_length=150, blank=True)
    area_nueva        = models.CharField('Área nueva', max_length=100, blank=True)
    grado_nuevo       = models.CharField('Grado nuevo', max_length=50, blank=True)
    edificio_nuevo    = models.CharField('Edificio nuevo', max_length=100, blank=True)
    fecha_hora   = models.DateTimeField("Fecha y hora", null=True, blank=True)
    solucion     = models.TextField("Solución Aplicada", null=True, blank=True)
    date         = models.DateField("Fecha del Mantenimiento")
    status       = models.CharField(
        max_length=50,
        choices=[
            ('Pendiente', 'Pendiente'),
            ('En Proceso', 'En Proceso'),
            ('Completado', 'Completado'),
        ],
        verbose_name="Estado"
    )
    observaciones = models.TextField(null=True, blank=True, verbose_name="Observaciones")
    # Firma del MAESTRO (evidencia de la reparación). En persona o remota (link wa.me).
    firma         = models.TextField("Firma del maestro (base64)", blank=True, null=True)
    # Firma del TÉCNICO / soporte (en persona, quien hace la reparación).
    firma_tecnico = models.TextField("Firma del técnico (base64)", blank=True, null=True)
    # Firma remota del maestro por link (token público, sin login).
    token_firma      = models.UUIDField("Token de firma", default=uuid.uuid4, unique=True, editable=False)
    firma_solicitada = models.BooleanField("Firma solicitada", default=False)
    firmado_en       = models.DateTimeField("Firmado el", null=True, blank=True)

    @property
    def firmado_maestro(self):
        return bool((self.firma or '').strip())

    @property
    def es_control(self):
        return self.tipo_equipo == 'control'

    @property
    def es_inspeccion(self):
        return self.tipo_equipo == 'inspeccion'

    @property
    def inspeccion_respuestas(self):
        return [(lbl, bool(getattr(self, campo))) for campo, lbl in self.INSPECCION_ITEMS]

    # <--- hecho por claude code (17-sep-2026): Entrega / Recogida de equipo
    @property
    def es_entrega(self):
        return self.tipo_equipo == 'entrega'

    @property
    def es_recogida(self):
        return self.tipo_equipo == 'recogida'

    @property
    def es_caso_especial(self):
        return self.tipo_equipo == 'caso_especial'

    @property
    def es_cambio(self):
        return self.tipo_equipo == 'cambio_equipo'

    @property
    def es_reasignacion(self):   # <--- hecho por claude code (12-oct-2026)
        return self.tipo_equipo == 'reasignacion'

    @property
    def es_movimiento(self):
        # <--- hecho por claude code (28-sep-2026): el caso especial es una recogida con origen en un control
        return self.tipo_equipo in ('entrega', 'recogida', 'caso_especial')

    @property
    def caso_especial(self):
        """Caso especial generado desde este control (None si no tiene)."""
        return self.casos_especiales.filter(tipo_equipo='caso_especial').first() if self.tipo_equipo == 'control' else None

    @property
    def cambio_equipo(self):
        """Cambio de equipo generado desde este control (None si no tiene)."""
        return self.casos_especiales.filter(tipo_equipo='cambio_equipo').first() if self.tipo_equipo == 'control' else None

    @property
    def reasignacion(self):   # <--- hecho por claude code (12-oct-2026): reasignación nacida de este control
        return self.casos_especiales.filter(tipo_equipo='reasignacion').first() if self.tipo_equipo == 'control' else None

    @property
    def movimiento_respuestas(self):
        """[(texto, marcado, detalle)] — el equipo y el televisor dicen CUÁL es."""
        out = []
        for campo, txt_ent, txt_rec in self.MOVIMIENTO_ITEMS:
            ok = bool(getattr(self, campo))
            det = ''
            if ok and campo == 'ent_equipo':
                comp = self.computadora if self.computadora_id else None
                modelo = self.model or (getattr(comp, 'modelo', '') or '')
                serie = self.serie or (getattr(comp, 'serie', '') or '')
                det = ' · '.join(x for x in [getattr(comp, 'asset_id', '') if comp else '',
                                             modelo, ('Serie ' + serie) if serie else ''] if x)
            elif ok and campo == 'ent_televisor' and self.televisor_id:
                tv = self.televisor
                det = ' · '.join(x for x in [tv.asset_id, tv.modelo or '', ('Serie ' + tv.serie) if tv.serie else ''] if x)
            out.append((txt_rec if self.es_recogida else txt_ent, ok, det))
        return out

    class Meta:
        db_table = 'maintenance_record'
        verbose_name = "Registro de Mantenimiento"
        verbose_name_plural = "Registros de Mantenimiento"

    def __str__(self):
        return f"{self.record_id} - {self.teacher_name}"


class FotoMantenimiento(models.Model):
    registro = models.ForeignKey(
        MaintenanceRecord, on_delete=models.CASCADE,
        related_name='fotos', verbose_name="Registro"
    )
    imagen   = models.ImageField("Foto", upload_to='mantenimiento/fotos/')
    orden    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = "Foto de Mantenimiento"
        verbose_name_plural = "Fotos de Mantenimiento"
