# red/crypto.py
# <--- hecho por claude code (16-sep-2026): cifrado simétrico de credenciales de equipos de red
"""Contraseñas de equipos (switches, UPS, PBX…) guardadas CIFRADAS en la BD (Fernet).

La clave sale de la variable de entorno RED_CRED_KEY si existe; si no, se deriva de
SECRET_KEY. OJO: si se cambia esa clave, las contraseñas guardadas dejan de poder leerse.
"""
import base64
import hashlib
import os

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken


def _fernet():
    semilla = os.getenv('RED_CRED_KEY') or settings.SECRET_KEY
    clave = base64.urlsafe_b64encode(hashlib.sha256(semilla.encode('utf-8')).digest())
    return Fernet(clave)


def cifrar(texto):
    texto = (texto or '').strip()
    if not texto:
        return ''
    return _fernet().encrypt(texto.encode('utf-8')).decode('ascii')


def descifrar(token):
    if not token:
        return ''
    try:
        return _fernet().decrypt(token.encode('ascii')).decode('utf-8')
    except (InvalidToken, ValueError):
        return ''
