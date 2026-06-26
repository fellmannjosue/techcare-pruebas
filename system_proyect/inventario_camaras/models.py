import uuid

from django.db import models
from django.utils import timezone

from core.models import AuditModel


# ─────────────────────────────────────────────────────────────
# Helper: genera el siguiente ID personalizado con prefijo
# (ej: ANASRV001, ANANVR002, ...). Se usa en cada modelo.
# ─────────────────────────────────────────────────────────────
def siguiente_id(modelo, campo, prefijo, ancho=3):
    ultimo = (
        modelo.objects
        .filter(**{f"{campo}__startswith": prefijo})
        .order_by(f"-{campo}")
        .values_list(campo, flat=True)
        .first()
    )
    n = 0
    if ultimo:
        try:
            n = int(ultimo[len(prefijo):])
        except (ValueError, TypeError):
            n = 0
    return f"{prefijo}{n + 1:0{ancho}d}"


ESTADO_MANT_CHOICES = [
    ('Pendiente', 'Pendiente'),
    ('En Proceso', 'En Proceso'),
    ('Completado', 'Completado'),
]


# ─────────────────────────────────────────────────────────────
# 1) SERVIDOR  (nivel más alto de la jerarquía)
#    Servidor → NVR → Gabinete → Cámara
# ─────────────────────────────────────────────────────────────
class Servidor(AuditModel):
    server_id     = models.CharField("ID Servidor", max_length=20, unique=True, blank=True)
    nombre        = models.CharField("Nombre", max_length=120)
    ubicacion     = models.CharField("Ubicación", max_length=150, blank=True)
    ip            = models.GenericIPAddressField("IP", protocol='both', unpack_ipv4=True, blank=True, null=True)
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        verbose_name = "Servidor"
        verbose_name_plural = "Servidores"
        ordering = ['server_id']

    def save(self, *args, **kwargs):
        if not self.server_id:
            self.server_id = siguiente_id(Servidor, 'server_id', 'ANASRV')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.server_id} – {self.nombre}"


# ─────────────────────────────────────────────────────────────
# 2) NVR  (pertenece a un Servidor)
# ─────────────────────────────────────────────────────────────
class NVR(AuditModel):
    nvr_id        = models.CharField("ID NVR", max_length=20, unique=True, blank=True)
    nombre        = models.CharField("Nombre", max_length=120)
    modelo        = models.CharField("Modelo", max_length=120, blank=True)
    serie         = models.CharField("Serie", max_length=120, blank=True)
    ip            = models.GenericIPAddressField("IP", protocol='both', unpack_ipv4=True, blank=True, null=True)
    canales       = models.PositiveIntegerField("Canales", blank=True, null=True)
    servidor      = models.ForeignKey(
        Servidor, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='nvrs', verbose_name="Servidor"
    )
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        verbose_name = "NVR"
        verbose_name_plural = "NVRs"
        ordering = ['nvr_id']

    def save(self, *args, **kwargs):
        if not self.nvr_id:
            self.nvr_id = siguiente_id(NVR, 'nvr_id', 'ANANVR')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nvr_id} – {self.nombre}"


# ─────────────────────────────────────────────────────────────
# 3) COMPONENTE  (catálogo seleccionable en cada Gabinete)
# ─────────────────────────────────────────────────────────────
class Componente(AuditModel):
    comp_id     = models.CharField("ID Componente", max_length=20, unique=True, blank=True)
    detalle     = models.CharField("Detalle", max_length=150)
    sub_detalle = models.CharField("Sub detalle", max_length=200, blank=True)

    class Meta:
        verbose_name = "Componente"
        verbose_name_plural = "Componentes"
        ordering = ['detalle', 'sub_detalle']

    def save(self, *args, **kwargs):
        if not self.comp_id:
            self.comp_id = siguiente_id(Componente, 'comp_id', 'ANACMP')
        super().save(*args, **kwargs)

    def __str__(self):
        if self.sub_detalle:
            return f"{self.detalle} / {self.sub_detalle}"
        return self.detalle


# ─────────────────────────────────────────────────────────────
# 4) GABINETE  (pertenece a un NVR, contiene varios Componentes)
# ─────────────────────────────────────────────────────────────
class Gabinete(AuditModel):
    gabinete_id   = models.CharField("ID Gabinete", max_length=20, unique=True, blank=True)
    nombre        = models.CharField("Gabinete", max_length=120)
    ubicacion     = models.CharField("Ubicación", max_length=150, blank=True)
    nvr           = models.ForeignKey(
        NVR, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='gabinetes', verbose_name="NVR"
    )
    componentes   = models.ManyToManyField(
        Componente, blank=True, related_name='gabinetes', verbose_name="Componentes"
    )
    observaciones = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        verbose_name = "Gabinete"
        verbose_name_plural = "Gabinetes"
        ordering = ['gabinete_id']

    def save(self, *args, **kwargs):
        if not self.gabinete_id:
            self.gabinete_id = siguiente_id(Gabinete, 'gabinete_id', 'ANAGAB')
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.gabinete_id} – {self.nombre}"


# ─────────────────────────────────────────────────────────────
# 5) CÁMARA  (pertenece a un Gabinete)
#    El NVR de la cámara se deriva por la cadena gabinete → nvr.
# ─────────────────────────────────────────────────────────────
class Camara(AuditModel):
    camara_id           = models.CharField("ID Cámara", max_length=20, unique=True, blank=True)
    modelo              = models.CharField("Modelo", max_length=120)
    serie               = models.CharField("Serie", max_length=120, blank=True)
    ubicacion           = models.CharField("Ubicación", max_length=150, blank=True)
    gabinete            = models.ForeignKey(
        Gabinete, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='camaras', verbose_name="Gabinete"
    )
    grupo               = models.CharField("Grupo", max_length=100, blank=True,
                                           help_text="Agrupa cámaras (ej: Edificio A, Bloque 1)")
    estado              = models.CharField("Estado", max_length=100, blank=True)
    version_actualizada = models.CharField("Versión actualizada", max_length=100, blank=True)
    observaciones       = models.TextField("Observaciones", blank=True, null=True)

    class Meta:
        verbose_name = "Cámara"
        verbose_name_plural = "Cámaras"
        ordering = ['camara_id']

    def save(self, *args, **kwargs):
        if not self.camara_id:
            self.camara_id = siguiente_id(Camara, 'camara_id', 'ANACAM')
        super().save(*args, **kwargs)

    @property
    def nvr(self):
        """NVR derivado de la cadena gabinete → nvr (solo lectura)."""
        return self.gabinete.nvr if self.gabinete else None

    @property
    def servidor(self):
        nvr = self.nvr
        return nvr.servidor if nvr else None

    def __str__(self):
        return f"{self.camara_id} – {self.modelo}"


# ─────────────────────────────────────────────────────────────
# Catálogo de tipos de falla para mantenimiento de cámaras
# ─────────────────────────────────────────────────────────────
class TipoFallaCamara(AuditModel):
    nombre = models.CharField("Tipo de Falla", max_length=120)

    class Meta:
        verbose_name = "Tipo de Falla (Cámara)"
        verbose_name_plural = "Tipos de Falla (Cámara)"
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# ─────────────────────────────────────────────────────────────
# 6) MANTENIMIENTO DE CÁMARA
#    Doble firma: responsable (interno) + técnico (remoto por link/token)
# ─────────────────────────────────────────────────────────────
class MantenimientoCamara(AuditModel):
    record_id     = models.CharField("ID Registro", max_length=25, unique=True, blank=True)
    # La ficha corresponde a un GRUPO de cámaras (no a una sola).
    grupo         = models.CharField("Grupo", max_length=100, blank=True)
    camara        = models.ForeignKey(
        Camara, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='mantenimientos', verbose_name="Cámara (legado)"
    )
    # Snapshot de datos (legado de fichas por cámara individual)
    modelo        = models.CharField("Modelo", max_length=120, blank=True)
    serie         = models.CharField("Serie", max_length=120, blank=True)
    ubicacion     = models.CharField("Ubicación", max_length=150, blank=True)

    tipo_falla    = models.ForeignKey(
        TipoFallaCamara, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name="Tipo de Falla"
    )
    solucion      = models.TextField("Solución Aplicada", null=True, blank=True)
    date          = models.DateField("Fecha del Mantenimiento")
    status        = models.CharField("Estado", max_length=50, choices=ESTADO_MANT_CHOICES, default='Pendiente')
    observaciones = models.TextField("Observaciones", null=True, blank=True)

    # ── Firmas ──
    responsable_nombre = models.CharField("Nombre del responsable", max_length=150, blank=True)
    firma_responsable  = models.TextField("Firma responsable (base64)", blank=True, null=True)

    tecnico_nombre     = models.CharField("Nombre del técnico", max_length=150, blank=True)
    firma_tecnico      = models.TextField("Firma técnico (base64)", blank=True, null=True)

    # ── Firma remota por link ──
    token_firma     = models.UUIDField("Token de firma", default=uuid.uuid4, unique=True, editable=False)
    firma_solicitada = models.BooleanField("Firma solicitada", default=False)
    firmado_en      = models.DateTimeField("Firmado el", null=True, blank=True)

    class Meta:
        verbose_name = "Mantenimiento de Cámara"
        verbose_name_plural = "Mantenimientos de Cámara"
        ordering = ['-date']

    def save(self, *args, **kwargs):
        if not self.record_id:
            self.record_id = siguiente_id(MantenimientoCamara, 'record_id', 'ANAMANCAM')
        super().save(*args, **kwargs)

    @property
    def firmado(self):
        return bool(self.firma_tecnico)

    @property
    def camaras_grupo(self):
        """Todas las cámaras del grupo de esta ficha."""
        if not self.grupo:
            return Camara.objects.none()
        return Camara.objects.filter(grupo=self.grupo).order_by('camara_id')

    def __str__(self):
        return f"{self.record_id} – {self.grupo or 'sin grupo'}"


class FotoMantenimientoCamara(models.Model):
    registro = models.ForeignKey(
        MantenimientoCamara, on_delete=models.CASCADE,
        related_name='fotos', verbose_name="Registro"
    )
    imagen   = models.ImageField("Foto", upload_to='inventario_camaras/fotos/')
    orden    = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ['orden']
        verbose_name = "Foto de Mantenimiento (Cámara)"
        verbose_name_plural = "Fotos de Mantenimiento (Cámara)"
