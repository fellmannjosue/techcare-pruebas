# <--- hecho por claude code (16-oct-2026): TODO modelo de las apps propias aparece en el panel admin.
# Los que ya tienen su admin.py se respetan; los que no, se registran aquí con un admin genérico de Unfold
# (columnas, búsqueda y filtros armados desde sus campos). Así un módulo nuevo sale en /admin/ sin hacer nada.
# Se llama desde system_proyect/urls.py ANTES de `admin.site.urls` (cuando todos los admin.py ya cargaron).
from django.apps import apps
from django.conf import settings
from django.contrib import admin
from django.db import models

# Bitácoras y datos que no se deben tocar a mano: solo se pueden VER.
SOLO_LECTURA = {
    'core.AuditLog', 'core.Notificacion', 'accounts.Verificacion2FA', 'ingresos_notas.EscrituraNota',
    'desarrollo.HistorialRequerimiento', 'tickets.TicketPausaSLA', 'salidas_bano.NotificacionSalida',
    'moodle_upload.PublicacionMoodle',
}


def _sensible(nombre):
    n = nombre.lower()
    return n.endswith('_enc') or 'password' in n or 'token' in n or n in ('codigo_hash', 'secret', 'clave')


def _admin_para(modelo):
    from unfold.admin import ModelAdmin
    campos = [f for f in modelo._meta.concrete_fields if not f.primary_key]
    visibles = [f for f in campos if not _sensible(f.name)]
    columnas = ['__str__'] + [f.name for f in visibles
                              if not isinstance(f, (models.TextField, models.JSONField, models.BinaryField, models.FileField))][:5]
    busqueda = [f.name for f in visibles if isinstance(f, (models.CharField, models.EmailField)) and not f.choices][:4]
    filtros = [f.name for f in visibles
               if isinstance(f, models.BooleanField) or f.choices or isinstance(f, models.DateField)][:4]
    etiqueta = f'{modelo._meta.app_label}.{modelo.__name__}'
    bases = (ModelAdmin,)
    if hasattr(modelo, 'history'):
        from simple_history.admin import SimpleHistoryAdmin
        bases = (SimpleHistoryAdmin, ModelAdmin)
    atributos = {
        'list_display': columnas, 'search_fields': busqueda, 'list_filter': filtros, 'list_per_page': 50,
        'exclude': [f.name for f in campos if _sensible(f.name)] or None,
    }
    if etiqueta in SOLO_LECTURA:
        atributos.update({'has_add_permission': lambda self, request: False,
                          'has_change_permission': lambda self, request, obj=None: False,
                          'has_delete_permission': lambda self, request, obj=None: False})
    return type(f'{modelo.__name__}AdminAuto', bases, atributos)


def registrar_faltantes(sitio=admin.site):
    """Registra los modelos propios (managed, no históricos) que todavía no tienen admin. Devuelve cuántos."""
    base = str(settings.BASE_DIR)
    n = 0
    for app in apps.get_app_configs():
        if not app.path.startswith(base) or app.path == base:
            continue
        for modelo in app.get_models():
            meta = modelo._meta
            if (sitio.is_registered(modelo) or not meta.managed or meta.proxy
                    or modelo.__name__.startswith('Historical')):
                continue
            try:
                sitio.register(modelo, _admin_para(modelo))
                n += 1
            except Exception:   # nunca tumbar las URLs por un modelo raro
                continue
    return n
