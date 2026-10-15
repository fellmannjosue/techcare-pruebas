# <--- hecho por claude code (14-oct-2026): "Subir a Moodle" — SOLO en techcare-pruebas, para probar la publicación
# de imágenes (agendas) en un curso de Moodle con el plugin local_techcareagenda.
from django.conf import settings
from django.db import models


class ConexionMoodle(models.Model):
    """Conexiones guardadas (p. ej. Moodle de pruebas y Moodle real): dirección + token cifrado (red.crypto).
    <--- hecho por claude code (15-oct-2026): varias conexiones, UNA activa (se cambia con "Conectar") y la fecha
    de vencimiento del token para avisar con cuenta regresiva."""
    nombre     = models.CharField('Nombre', max_length=60, default='Moodle')
    url        = models.CharField('Dirección de Moodle', max_length=200, default='http://192.168.10.6:452')
    token_enc  = models.TextField('Token (cifrado)', blank=True, default='')
    activa     = models.BooleanField('Activa', default=False)
    vence      = models.DateTimeField('El token vence', null=True, blank=True)
    actualizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                        on_delete=models.SET_NULL, related_name='+')
    actualizado_en  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'moodle_upload_conexion'
        verbose_name = 'Conexión a Moodle'

    @classmethod
    def actual(cls):
        """La conexión activa (si ninguna lo está, la primera; si no hay ninguna, se crea vacía)."""
        return (cls.objects.filter(activa=True).order_by('id').first() or cls.objects.order_by('id').first()
                or cls.objects.create(activa=True))

    def activar(self):
        type(self).objects.exclude(pk=self.pk).update(activa=False)
        self.activa = True
        self.save(update_fields=['activa'])

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
    # <--- hecho por claude code (14-oct-2026): publicación hecha desde el Dashboard de Agendas (vacío = desde /moodle-upload/)
    agenda       = models.ForeignKey('agendas.Agenda', null=True, blank=True, on_delete=models.SET_NULL,
                                     related_name='publicaciones_moodle')
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
