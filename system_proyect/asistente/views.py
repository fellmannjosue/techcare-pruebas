# <--- hecho por claude code (26-oct-2026): asistente IA (proxy seguro a la API de Claude)
"""Endpoint del asistente IA.

La API key vive SOLO en el servidor (.env: ANTHROPIC_API_KEY) — nunca en el .exe.
El permiso se valida en el servidor: todo usuario con sesión usa el asistente de GUÍA;
el superusuario usa el de DIAGNÓSTICO. Solo responde desde la app de escritorio (Electron)
para mantener el uso —y el gasto de créditos— dentro del .exe.
"""
import json
import logging
import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .prompts import system_prompt_para

log = logging.getLogger('asistente')

MODELO = getattr(settings, 'ASISTENTE_MODELO', 'claude-sonnet-5-5')
MAX_MENSAJES = 12            # cuántos mensajes recientes se mandan (control de costo)
MAX_LARGO_MSG = 6000         # recorte por mensaje (caracteres)
MAX_TOKENS_GUIA = 1000
MAX_TOKENS_DIAG = 2000


def _es_app_escritorio(request):
    return 'Electron' in request.META.get('HTTP_USER_AGENT', '')


def _api_key():
    return os.getenv('ANTHROPIC_API_KEY') or getattr(settings, 'ANTHROPIC_API_KEY', '') or ''


@login_required
@require_POST
def chat(request):
    # El asistente es exclusivo de la app de escritorio.
    if not _es_app_escritorio(request):
        return JsonResponse(
            {'ok': False, 'error': 'El asistente solo está disponible en la app de escritorio.'},
            status=403)

    api_key = _api_key()
    if not api_key:
        return JsonResponse(
            {'ok': False, 'error': 'El asistente aún no está configurado en el servidor.'},
            status=503)

    try:
        datos = json.loads(request.body.decode('utf-8'))
    except (ValueError, UnicodeDecodeError):
        return JsonResponse({'ok': False, 'error': 'Petición inválida.'}, status=400)

    # Sanitizar el historial: solo role user/assistant con texto, los últimos N.
    mensajes = []
    for m in (datos.get('mensajes') or [])[-MAX_MENSAJES:]:
        role = m.get('role')
        contenido = (m.get('content') or '').strip()
        if role in ('user', 'assistant') and contenido:
            mensajes.append({'role': role, 'content': contenido[:MAX_LARGO_MSG]})
    if not mensajes or mensajes[-1]['role'] != 'user':
        return JsonResponse({'ok': False, 'error': 'No hay un mensaje para responder.'}, status=400)

    es_super = request.user.is_superuser
    system = system_prompt_para(request.user, es_super)
    max_tokens = MAX_TOKENS_DIAG if es_super else MAX_TOKENS_GUIA
    effort = 'medium' if es_super else 'low'

    try:
        import anthropic
    except ImportError:
        return JsonResponse(
            {'ok': False, 'error': 'El asistente no está instalado en el servidor.'}, status=503)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model=MODELO,
            max_tokens=max_tokens,
            output_config={'effort': effort},
            system=[{'type': 'text', 'text': system, 'cache_control': {'type': 'ephemeral'}}],
            messages=mensajes,
        )
        texto = ''.join(
            getattr(b, 'text', '') for b in resp.content if getattr(b, 'type', '') == 'text'
        ).strip()
        uso = getattr(resp, 'usage', None)
        if uso:
            log.info('asistente user=%s super=%s in=%s out=%s',
                     request.user.username, es_super,
                     getattr(uso, 'input_tokens', '?'), getattr(uso, 'output_tokens', '?'))
        return JsonResponse({'ok': True, 'reply': texto or '(sin respuesta)'})
    except Exception as e:                                   # noqa: BLE001 - no filtrar detalles al cliente
        log.warning('asistente error: %s', e)
        return JsonResponse(
            {'ok': False, 'error': 'No se pudo contactar al asistente. Intenta de nuevo.'},
            status=502)
