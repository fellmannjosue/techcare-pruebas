# <--- hecho por claude code (26-oct-2026): marca si la petición viene de la app .exe (Electron)
def asistente_context(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    # <--- hecho por claude code (06-nov-2026): el botón solo aparece si el servidor tiene ANTHROPIC_API_KEY (si no, no respondería)
    import os
    from django.conf import settings
    activo = bool(os.getenv('ANTHROPIC_API_KEY') or getattr(settings, 'ANTHROPIC_API_KEY', ''))
    # <--- hecho por claude code (09-nov-2026): el Asistente IA también se configura por canal (core/canales.py)
    try:
        from core.canales import OCULTOS_ACTUAL
        if 'asistente' in OCULTOS_ACTUAL.get():
            activo = False
    except Exception:
        pass
    return {'es_app_escritorio': 'Electron' in ua, 'asistente_activo': activo}
