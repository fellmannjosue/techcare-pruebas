# core/utils_ai.py

import openai
from django.conf import settings

def consultar_ia(mensajes, modelo=None, max_tokens=None, temperatura=0.7, timeout=None):
    """
    Llama a la API de OpenAI para obtener una respuesta de IA en formato chat.
    - mensajes: lista de diccionarios [{"role": "user"/"assistant"/"system", "content": "..."}]
    - modelo: modelo a usar (por defecto, el configurado en settings)
    - max_tokens: límite máximo de tokens (por defecto, el configurado en settings)
    - temperatura: creatividad (por defecto 0.7)
    - timeout: tiempo máximo de espera (por defecto, el configurado en settings)
    Retorna: string (respuesta de la IA) o None si hay error.
    """
    api_key = settings.OPENAI_API_KEY
    if not api_key:
        raise Exception("No se ha configurado la API KEY de OpenAI.")

    # Valores por defecto desde settings si no se pasan
    modelo = modelo or getattr(settings, "OPENAI_MODEL_DEFAULT", "gpt-4-1-mini")
    max_tokens = max_tokens or getattr(settings, "OPENAI_MAX_TOKENS", 500)
    timeout = timeout or getattr(settings, "OPENAI_TIMEOUT", 20)

    openai.api_key = api_key

    # <--- hecho por claude code (03-sep-2026): los modelos GPT-5.x / o-series usan otro
    # "dialecto": exigen max_completion_tokens (rechazan max_tokens con error 400) y no
    # aceptan temperature distinta de la default. Los GPT-4.x/3.5 siguen con el estilo viejo.
    # Verificado con gpt-5.6-terra (funciona) y gpt-4o (sigue funcionando).
    _moderno = not (modelo.startswith('gpt-4') or modelo.startswith('gpt-3'))
    kwargs = {'model': modelo, 'messages': mensajes, 'timeout': timeout}
    if _moderno:
        # los 5.x razonan internamente y gastan tokens en eso: darles más margen
        kwargs['max_completion_tokens'] = max(int(max_tokens), 1000)
    else:
        kwargs['max_tokens'] = max_tokens
        kwargs['temperature'] = temperatura

    try:
        respuesta = openai.chat.completions.create(**kwargs)
        # Extraer el texto generado (OpenAI v1 API)
        contenido = respuesta.choices[0].message.content.strip()
        return contenido
    except Exception as e:
        print(f"[Error IA] {e}")
        return None

