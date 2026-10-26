# <--- hecho por claude code (26-oct-2026): marca si la petición viene de la app .exe (Electron)
def asistente_context(request):
    ua = request.META.get('HTTP_USER_AGENT', '')
    return {'es_app_escritorio': 'Electron' in ua}
