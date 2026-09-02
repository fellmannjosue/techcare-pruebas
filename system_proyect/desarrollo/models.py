# <--- hecho por claude code: módulo Gestión de Desarrollo (registro histórico oficial
# del ciclo de desarrollo de TechCare). FASE 1: modelos + choices + secuencia de códigos.
from django.db import models, transaction
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.utils.text import slugify

from core.models import AuditModel


# ─────────────────────────── Catálogos (TextChoices) ───────────────────────────
class EstadoReq(models.TextChoices):
    RECIBIDO        = 'recibido',        'Recibido'
    EVALUACION      = 'evaluacion',      'En evaluación'
    PENDIENTE_APROB = 'pendiente_aprob', 'Pendiente de aprobación'
    APROBADO        = 'aprobado',        'Aprobado'
    RECHAZADO       = 'rechazado',       'Rechazado'
    PLANIFICADO     = 'planificado',     'Planificado'
    DESARROLLO      = 'desarrollo',      'En desarrollo'
    PRUEBAS         = 'pruebas',         'En pruebas'
    LISTO_PROD      = 'listo_prod',      'Listo para producción'
    PRODUCCION      = 'produccion',      'Producción'
    PAUSADO         = 'pausado',         'Pausado'
    CANCELADO       = 'cancelado',       'Cancelado'


# Estados que ya NO se consideran "atrasados" ni activos para el semáforo.
ESTADOS_CERRADOS = {EstadoReq.PRODUCCION, EstadoReq.RECHAZADO, EstadoReq.CANCELADO}


class Prioridad(models.TextChoices):
    CRITICA = 'critica', 'Crítica'
    ALTA    = 'alta',    'Alta'
    MEDIA   = 'media',   'Media'
    BAJA    = 'baja',    'Baja'


class Impacto(models.TextChoices):
    ALTO  = 'alto',  'Alto'
    MEDIO = 'medio', 'Medio'
    BAJO  = 'bajo',  'Bajo'


class Urgencia(models.TextChoices):
    URGENTE = 'urgente', 'Urgente'
    NORMAL  = 'normal',  'Normal'
    ESPERAR = 'esperar', 'Puede esperar'


class TipoReq(models.TextChoices):
    FUNCIONALIDAD   = 'funcionalidad',   'Nueva funcionalidad'
    MODULO          = 'modulo',          'Nuevo módulo'
    MEJORA          = 'mejora',          'Mejora'
    CORRECCION      = 'correccion',      'Corrección'
    AUTOMATIZACION  = 'automatizacion',  'Automatización'
    REPORTE         = 'reporte',         'Reporte'
    DASHBOARD       = 'dashboard',       'Dashboard'
    REDISENO        = 'rediseno',        'Rediseño'
    INTEGRACION     = 'integracion',     'Integración'
    BASE_DATOS      = 'base_datos',      'Base de datos'
    SEGURIDAD       = 'seguridad',       'Seguridad'
    RENDIMIENTO     = 'rendimiento',     'Rendimiento'
    INFRAESTRUCTURA = 'infraestructura', 'Infraestructura'
    OTRO            = 'otro',            'Otro'


class Clasificacion(models.TextChoices):
    NUEVO_PROYECTO   = 'nuevo_proyecto',   'Nuevo Proyecto'
    MEJORA_EXISTENTE = 'mejora_existente', 'Mejora de Proyecto Existente'
    CORRECCION       = 'correccion',       'Corrección'
    MANTENIMIENTO    = 'mantenimiento',    'Mantenimiento'
    CAMBIO_MENOR     = 'cambio_menor',     'Cambio Menor'


class EstadoProyecto(models.TextChoices):
    ACTIVO        = 'activo',        'Activo'
    EN_DESARROLLO = 'en_desarrollo', 'En desarrollo'
    PRODUCCION    = 'produccion',    'En producción'
    PAUSADO       = 'pausado',       'Pausado'
    ARCHIVADO     = 'archivado',     'Archivado'


# ─────────────────────── Secuencia atómica de códigos ───────────────────────
class SecuenciaCodigo(models.Model):
    """Contador para generar códigos únicos sin colisiones (select_for_update).
    clave='REQ' se lleva por año; clave='PRY' es continuo (anio=0)."""
    clave = models.CharField(max_length=10)
    anio  = models.PositiveIntegerField(default=0)
    valor = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'desarrollo_secuencia'
        unique_together = ('clave', 'anio')

    def __str__(self):
        return f'{self.clave}-{self.anio}: {self.valor}'


def _siguiente(clave, anio=0):
    """Incrementa y devuelve el siguiente valor de forma atómica. Requiere estar
    dentro de una transacción (lo garantiza select_for_update en atomic)."""
    with transaction.atomic():
        seq, _ = (SecuenciaCodigo.objects
                  .select_for_update()
                  .get_or_create(clave=clave, anio=anio))
        seq.valor = seq.valor + 1
        seq.save(update_fields=['valor'])
        return seq.valor


def generar_codigo_requerimiento(anio=None):
    anio = anio or timezone.now().year
    return f'REQ-{anio}-{_siguiente("REQ", anio):04d}'


def generar_codigo_proyecto():
    return f'TC-PRY-{_siguiente("PRY", 0):04d}'


# ─────────────────────────────── Proyecto ───────────────────────────────
class ProyectoDesarrollo(AuditModel):
    """Un sistema/módulo/desarrollo grande (ej. Sistema de Agendas). Agrupa
    muchos requerimientos. Código auto TC-PRY-XXXX."""
    codigo = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Código")
    nombre = models.CharField(max_length=160, verbose_name="Nombre")
    slug   = models.SlugField(max_length=180, blank=True)
    modulo = models.CharField(max_length=120, blank=True, verbose_name="Módulo")
    descripcion            = models.TextField(blank=True, verbose_name="Descripción")
    problema_que_resuelve  = models.TextField(blank=True, verbose_name="Problema que resuelve")
    area     = models.CharField(max_length=60, blank=True, verbose_name="Área")
    subarea  = models.CharField(max_length=60, blank=True, verbose_name="Subárea")
    solicitado_por = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='proyectos_solicitados', verbose_name="Solicitado por")
    responsable    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name='proyectos_responsable', verbose_name="Responsable")
    fecha_solicitud      = models.DateField(null=True, blank=True)
    fecha_inicio         = models.DateField(null=True, blank=True)
    fecha_implementacion = models.DateField(null=True, blank=True)
    estado    = models.CharField(max_length=20, choices=EstadoProyecto.choices,
                                 default=EstadoProyecto.ACTIVO, db_index=True)
    prioridad = models.CharField(max_length=10, choices=Prioridad.choices,
                                 default=Prioridad.MEDIA, db_index=True)
    version_inicial     = models.CharField(max_length=30, blank=True)
    version_actual      = models.CharField(max_length=30, blank=True)
    tecnologia_principal = models.CharField(max_length=80, blank=True)
    tecnologias   = models.CharField(max_length=255, blank=True)
    base_datos    = models.CharField(max_length=80, blank=True)
    app_django    = models.CharField(max_length=80, blank=True)
    ruta          = models.CharField(max_length=200, blank=True)
    url           = models.CharField(max_length=200, blank=True)
    dependencias  = models.TextField(blank=True)
    usuarios_beneficiados = models.CharField(max_length=200, blank=True)
    en_produccion = models.BooleanField(default=False, verbose_name="¿En producción?")
    documentacion = models.TextField(blank=True)
    repositorio_referencia = models.CharField(max_length=200, blank=True)
    proxima_mejora = models.CharField(max_length=200, blank=True)
    observaciones  = models.TextField(blank=True)

    class Meta:
        db_table = 'desarrollo_proyecto'
        verbose_name = 'Proyecto de desarrollo'
        verbose_name_plural = 'Proyectos de desarrollo'
        ordering = ['-fecha_creado']

    def __str__(self):
        return f'{self.codigo} · {self.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo_proyecto()
        if not self.slug and self.nombre:
            self.slug = slugify(self.nombre)[:180]
        super().save(*args, **kwargs)


# ─────────────────────────── Catálogo de solicitantes ───────────────────────────
class SolicitanteCatalogo(models.Model):
    """Catálogo editable de solicitantes (áreas/personas que piden desarrollo).
    Agregable desde el formulario y desde el admin. 'Soporte Técnico' por defecto."""
    nombre = models.CharField(max_length=120, unique=True, verbose_name="Solicitante")
    activo = models.BooleanField(default=True)
    orden  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'desarrollo_solicitante_cat'
        ordering = ['orden', 'nombre']
        verbose_name = 'Solicitante (catálogo)'
        verbose_name_plural = 'Solicitantes (catálogo)'

    def __str__(self):
        return self.nombre


class OpcionCatalogo(models.Model):
    """Catálogo genérico agregable para Área y Módulo (guardan texto)."""
    grupo  = models.CharField(max_length=20)   # 'area' | 'modulo'
    valor  = models.CharField(max_length=120)
    activo = models.BooleanField(default=True)
    orden  = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = 'desarrollo_opcion_cat'
        unique_together = ('grupo', 'valor')
        ordering = ['grupo', 'orden', 'valor']
        verbose_name = 'Opción de catálogo'
        verbose_name_plural = 'Opciones de catálogo (Área/Módulo)'

    def __str__(self):
        return f'{self.grupo}: {self.valor}'


# ─────────────────────────────── Requerimiento ───────────────────────────────
class RequerimientoDesarrollo(AuditModel):
    """Una solicitud específica (ej. 'autoguardado en agendas'). Puede pertenecer
    a un proyecto (o no, al inicio). Código auto REQ-AAAA-XXXX."""
    codigo = models.CharField(max_length=20, unique=True, editable=False, verbose_name="Código")
    titulo = models.CharField(max_length=200, verbose_name="Título")
    descripcion       = models.TextField(blank=True, verbose_name="Descripción")
    problema_actual   = models.TextField(blank=True, verbose_name="Problema actual")
    resultado_esperado = models.TextField(blank=True, verbose_name="Resultado esperado")

    proyecto = models.ForeignKey(ProyectoDesarrollo, null=True, blank=True, on_delete=models.SET_NULL,
                                 related_name='requerimientos', verbose_name="Proyecto")
    modulo   = models.CharField(max_length=120, blank=True, verbose_name="Módulo relacionado")

    solicitante = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='req_solicitados', verbose_name="Registrado por")
    # <--- hecho por claude code: solicitante visible como catálogo agregable (área/persona)
    solicitante_cat = models.ForeignKey('SolicitanteCatalogo', null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='requerimientos',
                                        verbose_name="Solicitante")
    area        = models.CharField(max_length=60, blank=True, verbose_name="Área")
    responsable = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name='req_responsable', verbose_name="Responsable")

    tipo          = models.CharField(max_length=20, choices=TipoReq.choices, default=TipoReq.MEJORA, db_index=True)
    prioridad     = models.CharField(max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA, db_index=True)
    impacto       = models.CharField(max_length=10, choices=Impacto.choices, default=Impacto.MEDIO)
    urgencia      = models.CharField(max_length=10, choices=Urgencia.choices, default=Urgencia.NORMAL)
    clasificacion = models.CharField(max_length=20, choices=Clasificacion.choices,
                                     default=Clasificacion.MEJORA_EXISTENTE, db_index=True)
    estado        = models.CharField(max_length=20, choices=EstadoReq.choices,
                                     default=EstadoReq.RECIBIDO, db_index=True)

    usuarios_afectados = models.CharField(max_length=200, blank=True)

    fecha_solicitud   = models.DateField(null=True, blank=True)
    fecha_evaluacion  = models.DateField(null=True, blank=True)
    fecha_inicio      = models.DateField(null=True, blank=True)
    fecha_estimada    = models.DateField(null=True, blank=True)
    fecha_finalizacion = models.DateField(null=True, blank=True)

    porcentaje_avance = models.PositiveSmallIntegerField(
        default=0, validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Avance (%)")
    version_implementada = models.CharField(max_length=30, blank=True)
    observaciones = models.TextField(blank=True)

    class Meta:
        db_table = 'desarrollo_requerimiento'
        verbose_name = 'Requerimiento'
        verbose_name_plural = 'Requerimientos'
        ordering = ['-fecha_creado']
        indexes = [
            models.Index(fields=['estado', 'prioridad']),
            models.Index(fields=['area']),
            models.Index(fields=['fecha_estimada']),
        ]

    def __str__(self):
        return f'{self.codigo} · {self.titulo}'

    def save(self, *args, **kwargs):
        if not self.codigo:
            self.codigo = generar_codigo_requerimiento()
        super().save(*args, **kwargs)

    @property
    def cerrado(self):
        return self.estado in ESTADOS_CERRADOS

    @property
    def semaforo(self):
        """🟢 en tiempo · 🟡 próximo a vencer · 🔴 atrasado · ⚪ sin fecha.
        Se calcula en backend; NUNCA se guarda. Cerrado = nunca 'atrasado'."""
        if self.cerrado:
            return 'verde'
        if not self.fecha_estimada:
            return 'gris'
        hoy = timezone.now().date()   # USE_TZ=False → now() es naive local
        dias = (self.fecha_estimada - hoy).days
        if dias < 0:
            return 'rojo'
        if dias <= 3:
            return 'amarillo'
        return 'verde'


# ─────────────────────────── Historial (automático) ───────────────────────────
class HistorialRequerimiento(models.Model):
    """Timeline automático de cambios del sistema (estado/responsable/avance).
    NUNCA se borra. Distinto de la bitácora humana."""
    requerimiento = models.ForeignKey(RequerimientoDesarrollo, on_delete=models.CASCADE,
                                      related_name='historial')
    fecha = models.DateTimeField(default=timezone.now, db_index=True)
    estado_anterior = models.CharField(max_length=20, blank=True)
    estado_nuevo    = models.CharField(max_length=20, blank=True)
    porcentaje_anterior = models.PositiveSmallIntegerField(null=True, blank=True)
    porcentaje_nuevo    = models.PositiveSmallIntegerField(null=True, blank=True)
    responsable_anterior = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+')
    responsable_nuevo    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL,
                                             related_name='+')
    comentario = models.CharField(max_length=255, blank=True)
    usuario    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')

    class Meta:
        db_table = 'desarrollo_historial'
        verbose_name = 'Historial de requerimiento'
        verbose_name_plural = 'Historial de requerimientos'
        ordering = ['fecha', 'id']

    def __str__(self):
        return f'{self.requerimiento_id} · {self.estado_anterior}→{self.estado_nuevo}'


# ─────────────────────────── Bitácora (notas humanas) ───────────────────────────
class ComentarioRequerimiento(models.Model):
    """Notas humanas (bitácora). Separado del historial automático."""
    requerimiento = models.ForeignKey(RequerimientoDesarrollo, on_delete=models.CASCADE,
                                      related_name='comentarios')
    usuario    = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    comentario = models.TextField()
    fecha      = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        db_table = 'desarrollo_comentario'
        verbose_name = 'Comentario de requerimiento'
        verbose_name_plural = 'Comentarios de requerimiento'
        ordering = ['fecha', 'id']

    def __str__(self):
        return f'{self.requerimiento_id} · {self.usuario_id}'


# ─────────────────────────────── Adjuntos ───────────────────────────────
def _upload_adjunto(instance, filename):
    return f'desarrollo/adjuntos/{instance.requerimiento_id}/{filename}'


class AdjuntoRequerimiento(models.Model):
    """Evidencia adjunta (PDF, imágenes, Word, Excel, texto). Validado en forms."""
    requerimiento = models.ForeignKey(RequerimientoDesarrollo, on_delete=models.CASCADE,
                                      related_name='adjuntos')
    archivo        = models.FileField(upload_to=_upload_adjunto)
    nombre_original = models.CharField(max_length=200, blank=True)
    descripcion    = models.CharField(max_length=255, blank=True)
    usuario        = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='+')
    fecha          = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'desarrollo_adjunto'
        verbose_name = 'Adjunto de requerimiento'
        verbose_name_plural = 'Adjuntos de requerimiento'
        ordering = ['-fecha']

    def __str__(self):
        return self.nombre_original or f'Adjunto {self.pk}'
