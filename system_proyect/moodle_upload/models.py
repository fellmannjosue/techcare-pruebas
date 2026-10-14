# <--- hecho por claude code (14-oct-2026): "Subir a Moodle" — SOLO en techcare-pruebas, para probar la publicación
# de imágenes (agendas) en un curso de Moodle con el plugin local_techcareagenda.
from django.conf import settings
from django.db import models


class ConexionMoodle(models.Model):
    """Registro único: dirección del Moodle y token del servicio web (cifrado con red.crypto)."""
    url        = models.CharField('Dirección de Moodle', max_length=200, default='http://192.168.10.6:452')
    token_enc  = models.TextField('Token (cifrado)', blank=True, default='')
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='+')
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'moodle_upload_conexion'
        verbose_name = 'Conexión a Moodle'

    @classmethod
    def actual(cls):
        return cls.objects.order_by('id').first() or cls.objects.create()

    @property
    def token(self):
        if not self.token_enc:
            return ''
        from red.crypto import descifrar
        try:
            return descifrar(self.token_enc) or ''
        except Exception:
            return ''

    def set_token(self, valor):
        from red.crypto import cifrar
        self.token_enc = cifrar(valor) if valor else ''


class PublicacionMoodle(models.Model):
    """Bitácora de cada intento de publicación (no guarda la imagen, solo sus datos)."""
    curso_id     = models.IntegerField('ID del curso')
    curso_nombre = models.CharField('Curso', max_length=255, blank=True, default='')
    archivo      = models.CharField('Archivo', max_length=255)
    tamano_kb    = models.IntegerField('Tamaño (KB)', default=0)
    alt          = models.CharField('Texto alternativo', max_length=200, blank=True, default='')
    ok           = models.BooleanField('Publicada', default=False)
    creada       = models.BooleanField('Creada por primera vez', default=False)
    cmid         = models.IntegerField('Módulo en Moodle', null=True, blank=True)
    mensaje      = models.TextField('Mensaje', blank=True, default='')
    usuario      = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name='+')
    fecha        = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'moodle_upload_publicacion'
        ordering = ['-fecha']
        verbose_name = 'Publicación en Moodle'
        verbose_name_plural = 'Publicaciones en Moodle'
