# red/crypto.py
# <--- hecho por claude code (16-sep-2026): cifrado simétrico de credenciales de equipos de red
"""Contraseñas de equipos (switches, UPS, PBX…) guardadas CIFRADAS en la BD (Fernet).

La clave sale de la variable de entorno RED_CRED_KEY si existe; si no, se deriva de
SECRET_KEY. OJO: si se cambia esa clave, las contraseñas guardadas dejan de poder leerse.
"""
import base64
import hashlib
import logging
import os

from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken

_log = logging.getLogger(__name__)
_AVISO_SECRET_KEY = []   # <--- hecho por claude code (seguridad 05-nov-2026): el aviso sale UNA vez por proceso


def _fernet():
    # <--- hecho por claude code (seguridad 05-nov-2026): MISMA clave que antes (RED_CRED_KEY o, si falta, SECRET_KEY); solo se avisa en el log cuando se usa el SECRET_KEY. Cambiar la clave o recifrar es decisión del usuario.
    semilla = os.getenv('RED_CRED_KEY')
    if not semilla:
        semilla = settings.SECRET_KEY
        if not _AVISO_SECRET_KEY:
            _AVISO_SECRET_KEY.append(1)
            _log.warning('red.crypto: RED_CRED_KEY no esta definida; las contrasenas de equipos de red se cifran '
                         'con una clave derivada del SECRET_KEY (si el SECRET_KEY se filtra o se rota, se leen o se pierden). '
                         'Pendiente: clave propia en el .env + recifrado con un comando.')
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
