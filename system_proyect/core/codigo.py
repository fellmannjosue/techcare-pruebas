# <--- hecho por claude code (16-oct-2026): estadística del código por app (Configuración → Código del sistema).
# Cuenta las líneas de views / models / forms / admin / otros .py / HTML / CSS / JS de cada app propia y su peso en
# disco. Se recalcula sola cuando cambia algún archivo: la llave del caché es la "firma" (cantidad + fecha de
# modificación más reciente + tamaño total) que se obtiene recorriendo el árbol sin leer los archivos.
import hashlib
import os

from django.apps import apps
from django.conf import settings
from django.core.cache import cache

CATEGORIAS = [   # (clave, etiqueta, color)
    ('views', 'Views', '#2563eb'), ('models', 'Models', '#7c3aed'), ('forms', 'Forms', '#0891b2'),
    ('admin', 'Admin', '#d97706'), ('py', 'Otros .py', '#64748b'), ('html', 'HTML', '#e8590c'),
    ('css', 'CSS', '#0ca678'), ('js', 'JS', '#f59f00'),
]
_EXCLUIR_DIRS = {'__pycache__', 'migrations', 'node_modules', 'vendor', 'vendors', 'lib', 'libs', '.git'}
_EXT = {'.py', '.html', '.css', '.js'}


def _categoria(ruta_rel, nombre, ext):
    if ext == '.py':
        if nombre.startswith('views') or '/views/' in f'/{ruta_rel}/':
            return 'views'
        if nombre.startswith('models') or '/models/' in f'/{ruta_rel}/':
            return 'models'
        if nombre.startswith('forms'):
            return 'forms'
        if nombre == 'admin.py' or nombre.startswith('admin_'):
            return 'admin'
        return 'py'
    return ext[1:]


def _lineas(ruta):
    try:
        with open(ruta, 'rb') as f:
            return sum(1 for _ in f)
    except OSError:
        return 0


def _recorrer(raiz, leer=True, saltar=()):
    """(firma, {categoria: líneas}, archivos, bytes, última modificación) de una carpeta."""
    lineas = {c: 0 for c, _, _ in CATEGORIAS}
    n = tam = 0
    ultima = 0.0
    for actual, dirs, archivos in os.walk(raiz):
        dirs[:] = [d for d in dirs if d not in _EXCLUIR_DIRS and not d.startswith('.')
                   and os.path.join(actual, d) not in saltar]
        rel = os.path.relpath(actual, raiz)
        for nombre in archivos:
            ruta = os.path.join(actual, nombre)
            try:
                st = os.stat(ruta)
            except OSError:
                continue
            tam += st.st_size   # el peso cuenta TODO (imágenes, fuentes…) salvo cachés y migraciones
            ext = os.path.splitext(nombre)[1].lower()
            if ext not in _EXT or '.min.' in nombre:
                continue
            n += 1
            ultima = max(ultima, st.st_mtime)
            if leer:
                lineas[_categoria(rel, nombre, ext)] += _lineas(ruta)
    return (n, round(ultima), tam), lineas, n, tam, ultima


def _carpetas():
    """[(nombre, ruta, saltar)] — apps propias + plantillas y estáticos globales."""
    base = str(settings.BASE_DIR)
    out = [(a.label, a.path, ()) for a in apps.get_app_configs() if a.path.startswith(base) and a.path != base]
    globales = [('templates (global)', d) for t in settings.TEMPLATES for d in t.get('DIRS', [])]
    globales += [('static (global)', str(d)) for d in getattr(settings, 'STATICFILES_DIRS', [])]
    for nombre, ruta in globales:
        if os.path.isdir(ruta) and str(ruta).startswith(base):
            out.append((nombre, str(ruta), ()))
    return out


def estadisticas():
    """Lista de apps ordenada de la más grande a la más pequeña (por líneas totales) + totales."""
    filas = []
    for nombre, ruta, saltar in _carpetas():
        firma = _recorrer(ruta, leer=False, saltar=saltar)[0]
        clave = 'tc_codigo_' + hashlib.md5(f'{ruta}|{firma}'.encode()).hexdigest()
        dato = cache.get(clave)
        if dato is None:
            _, lineas, n, tam, ultima = _recorrer(ruta, saltar=saltar)
            dato = {'lineas': lineas, 'archivos': n, 'bytes': tam, 'ultima': ultima}
            cache.set(clave, dato, 60 * 60 * 24 * 7)
        total = sum(dato['lineas'].values())
        filas.append({'app': nombre, 'total': total, **dato})
    filas.sort(key=lambda f: (-f['total'], f['app']))
    tot = {c: sum(f['lineas'][c] for f in filas) for c, _, _ in CATEGORIAS}
    totales = {'lineas': tot, 'total': sum(tot.values()), 'archivos': sum(f['archivos'] for f in filas),
               'bytes': sum(f['bytes'] for f in filas)}
    maximo = max([f['total'] for f in filas] or [1]) or 1
    for f in filas:
        f['pct'] = round(f['total'] * 100 / maximo, 1)
        f['partes'] = [(c, etq, color, f['lineas'][c], round(f['lineas'][c] * 100 / f['total'], 2) if f['total'] else 0)
                       for c, etq, color in CATEGORIAS]
    return filas, totales


def peso(n):
    for unidad in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unidad == 'GB':
            return f'{n:.0f} {unidad}' if unidad == 'B' else f'{n:.1f} {unidad}'
        n /= 1024
