# <--- hecho por claude code: app del portal nuevo del superusuario (SPA Next.js + API DRF)
from django.apps import AppConfig


class PortalSuperConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'portal_super'
    verbose_name = 'Portal SuperUser (nuevo)'
