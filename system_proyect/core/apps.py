from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'

    def ready(self):
        try:
            from . import audit_registry
            audit_registry.register_all()
        except Exception:
            pass
        # <--- hecho por claude code (09-nov-2026, ISO 27001): bitácora de eventos de seguridad (logins, privilegios, grupos, configuración)
        from . import seguridad_eventos
        seguridad_eventos.conectar()
        # <--- hecho por claude code (seguridad 05-nov-2026): Pillow NO abre EPS/PostScript: al cargarlos ejecuta Ghostscript del servidor con el contenido del archivo subido. Ninguna subida de TechCare los necesita (hay 14 Image.open sin formats=).
        try:
            from PIL import Image as _PILImage
            _PILImage.init()
            _PILImage.OPEN.pop('EPS', None)
            if 'EPS' in _PILImage.ID:
                _PILImage.ID.remove('EPS')
        except Exception:
            pass
