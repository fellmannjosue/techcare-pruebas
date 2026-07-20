# core/version.py
# <--- hecho por claude code: versión del sistema + novedades (changelog generado desde git)
"""Fuente de verdad de la versión y las novedades.

El archivo `changelog.json` lo genera el comando `manage.py gen_changelog`
(invocado por el hook de git `post-commit`), porque el proceso de Apache
corre como www-data y NO puede ejecutar git sobre este repo.
"""
import json
import os

# Versión inicial si aún no existe changelog.json
VERSION_INICIAL = '6.0.1.2'

CHANGELOG_PATH = os.path.join(os.path.dirname(__file__), 'changelog.json')


def _data():
    try:
        with open(CHANGELOG_PATH, encoding='utf-8') as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, ValueError, OSError):
        return {}


def version_actual():
    """Versión actual del sistema (ej. '6.0.1.2')."""
    return _data().get('version') or VERSION_INICIAL


def novedades(limite=10):
    """Entradas del changelog, de la más reciente a la más antigua."""
    ent = _data().get('entradas') or []
    return ent[:limite] if isinstance(ent, list) else []
