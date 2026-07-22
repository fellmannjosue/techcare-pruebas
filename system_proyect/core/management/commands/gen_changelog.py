# core/management/commands/gen_changelog.py
# <--- hecho por claude code: genera changelog.json desde los mensajes de git y sube el build
"""Lee los commits nuevos desde la última entrada registrada y agrega una
entrada al changelog, subiendo el último segmento de la versión (build).

Uso:
    manage.py gen_changelog                 # build +1 con los commits nuevos
    manage.py gen_changelog --version 6.1.0.0   # fija la versión
    manage.py gen_changelog --quiet         # sin salida (para el hook de git)

Lo invoca el hook `.git/hooks/post-commit`, que corre como el usuario dueño
del repo (Apache/www-data no puede ejecutar git aquí).
"""
import json
import os
import re
import subprocess
from datetime import date

from django.core.management.base import BaseCommand

from core.version import CHANGELOG_PATH, VERSION_INICIAL

# Commits que no aportan nada al usuario final
_IGNORAR = re.compile(r'^(merge |wip\b|fixup!|squash!|bump|\.{3})', re.I)
MAX_COMMITS = 40


def _raiz():
    return os.path.abspath(os.path.join(os.path.dirname(CHANGELOG_PATH), '..', '..'))


def _git(*args):
    """Corre git en la raíz del repo y devuelve stdout (o '' si falla)."""
    try:
        out = subprocess.run(['git', '-C', _raiz()] + list(args),
                             capture_output=True, text=True, timeout=20)
        return out.stdout.strip() if out.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def _valido(h):
    """True si el hash resuelve a un commit existente."""
    return bool(h) and bool(_git('rev-parse', '--verify', '--quiet', h + '^{commit}'))


# Marcador local (en .git, NO se commitea) del último commit incluido en el
# changelog. Sobrevive a `git commit --amend`, a diferencia de guardar el hash
# dentro del propio changelog.json.
def _base_path():
    return os.path.join(_raiz(), '.git', 'changelog_base')


def _leer_base():
    try:
        with open(_base_path(), encoding='utf-8') as fh:
            return fh.read().strip()
    except OSError:
        return ''


def _escribir_base(h):
    try:
        with open(_base_path(), 'w', encoding='utf-8') as fh:
            fh.write(h)
    except OSError:
        pass


def _subir_build(version):
    """'6.0.1.2' → '6.0.1.3'. Si venía en menor ('6.0.1.3.001'), sube el build y limpia
    el 5º segmento. Si el formato es raro, deja la versión igual."""
    partes = version.split('.')
    if len(partes) == 5:            # 6.0.1.3.001 -> 6.0.1.4
        partes = partes[:4]
    if not partes or not partes[-1].isdigit():
        return version
    partes[-1] = str(int(partes[-1]) + 1)
    return '.'.join(partes)


def _subir_menor(version):
    """<--- hecho por claude code: release chico (< 50 archivos).
    '6.0.1.3' → '6.0.1.3.001' · '6.0.1.3.001' → '6.0.1.3.002'."""
    partes = version.split('.')
    if len(partes) == 5 and partes[-1].isdigit():
        return '.'.join(partes[:4]) + '.%03d' % (int(partes[-1]) + 1)
    return version + '.001' 


class Command(BaseCommand):
    help = 'Genera changelog.json a partir de los commits nuevos y sube el build.'

    def add_arguments(self, parser):
        parser.add_argument('--set-version', dest='set_version', default=None,
                            help='Fija la versión en lugar de subir el build.')
        parser.add_argument('--quiet', action='store_true', help='Sin salida.')
        parser.add_argument('--menor', action='store_true',
                            help='Release chico (<50 archivos): sube el 5º segmento y '
                                 'las novedades solo se muestran al superusuario.')

    def handle(self, *args, **opts):
        quiet = opts['quiet']
        def say(msg):
            if not quiet:
                self.stdout.write(msg)

        try:
            with open(CHANGELOG_PATH, encoding='utf-8') as fh:
                data = json.load(fh)
        except (FileNotFoundError, ValueError, OSError):
            data = {}
        if not isinstance(data, dict):
            data = {}
        entradas = data.get('entradas') if isinstance(data.get('entradas'), list) else []
        version_prev = data.get('version') or VERSION_INICIAL

        head = _git('rev-parse', '--short', 'HEAD')
        if not head:
            say('No se pudo leer git (¿repo no disponible?). Sin cambios.')
            return

        # Base del rango: marcador local (sobrevive amends) → hash del changelog → últimos N
        base = _leer_base()
        if not _valido(base):
            base = entradas[0].get('commit') if entradas else ''
        rango = f'{base}..HEAD' if _valido(base) else f'-{MAX_COMMITS}'
        crudo = _git('log', rango, '--no-merges', '--format=%s')
        mensajes = [m.strip() for m in crudo.splitlines() if m.strip()]
        mensajes = [m for m in mensajes if not _IGNORAR.match(m)][:MAX_COMMITS]

        if not mensajes:
            say('Sin commits nuevos; changelog sin cambios.')
            return

        if opts['set_version']:
            nueva = opts['set_version']
        elif opts['menor']:
            nueva = _subir_menor(version_prev)
        else:
            nueva = _subir_build(version_prev)
        entradas.insert(0, {
            'version': nueva,
            'fecha': date.today().isoformat(),
            'commit': head,
            'cambios': mensajes,
            'menor': bool(opts['menor']),   # <--- hecho por claude code: solo la ve el superusuario
        })
        data['version'] = nueva
        data['entradas'] = entradas[:50]   # conserva las últimas 50 versiones

        with open(CHANGELOG_PATH, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        _escribir_base(_git('rev-parse', 'HEAD'))   # marca este commit como incluido
        say(f'Versión {nueva} · {len(mensajes)} cambio(s) registrados.')
