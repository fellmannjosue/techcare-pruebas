"""<--- hecho por claude code (06-nov-2026): Configuración → Variables del sistema (.env). SOLO superusuario.

Lee el `.env` (o las variables del proceso cuando el servidor no tiene archivo, como Coolify), las agrupa
y las clasifica en secreto / conexión / ajuste. Los valores NUNCA van en el HTML: se piden uno a uno por
POST tras confirmar la contraseña. Editar escribe el archivo EN SU LUGAR (conserva dueño y permisos 640),
con respaldo previo y verificación; si no hay archivo o no se puede escribir/respaldar, NO se guarda nada.
Los cambios se aplican al reiniciar el servidor (el proceso ya cargó las variables al arrancar).
"""
import datetime
import os
import re
import shutil
from pathlib import Path

from django.conf import settings
from dotenv import dotenv_values

PREFIJO_OFF = '# [deshabilitada] '          # así se marca una variable deshabilitada (línea comentada)
CLAVE_RE = re.compile(r'^[A-Z][A-Z0-9_]{1,63}$')
NO_EDITABLES = {'DJANGO_SECRET_KEY'}         # decisión del usuario: NUNCA rotarla (las contraseñas de Red dependen de ella)

# Booleanos: unas se comparan con 'True' y otras con 'true' en settings.py → se respeta cada forma.
BOOL_MAYUS = re.compile(r'_USE_(TLS|SSL)$')
BOOL_MINUS = {'DJANGO_DEBUG', 'EMAILS_REALES', 'USE_SQLSERVER', 'USE_WHITENOISE', 'COOKIES_SECURE', 'INV_TEST2_MOSTRAR_TARJETA'}

GRUPOS = [
    ('django',  'Django',                       'ti-brand-django', '#0c8599'),
    ('mysql',   'MySQL (base principal)',       'ti-database',     '#2563eb'),
    ('test2',   'SQL Server · sistema académico', 'ti-school',     '#7048e8'),
    ('zkbio',   'SQL Server · reloj marcador',  'ti-clock',        '#e8590c'),
    ('inv',     'SQL Server · inventario (Test2)', 'ti-packages',  '#ae3ec9'),
    ('correo',  'Correo principal',             'ti-mail',         '#d63939'),
    ('enf',     'Correo de Enfermería',         'ti-heartbeat',    '#d6336c'),
    ('cbl',     'Correo Coordinación Bilingüe', 'ti-mail-star',    '#f59f00'),
    ('ccol',    'Correo Coordinación Colegio',  'ti-mail-star',    '#74b816'),
    ('notas',   'Notas mitad de parcial',       'ti-notes',        '#0ca678'),
    ('ia',      'Asistente IA',                 'ti-robot',        '#495057'),
    ('otros',   'Otras',                        'ti-dots',         '#868e96'),
]

_ETIQUETAS = {
    'DJANGO_SECRET_KEY': 'Clave maestra de Django. Firma sesiones y cifra las contraseñas de Red: NUNCA se cambia.',
    'DJANGO_DEBUG': 'Modo depuración. En producción SIEMPRE false (si no, los errores muestran el código).',
    'DB_NAME': 'Nombre de la base MySQL', 'DB_USER': 'Usuario MySQL', 'DB_PASSWORD': 'Contraseña MySQL',
    'DB_HOST': 'Servidor MySQL', 'DB_PORT': 'Puerto MySQL',
    'MSSQL_ODBC_DRIVER': 'Driver ODBC para SQL Server',
    'MSSQL_REAL_DB_NAME': 'Base académica REAL (AdmonANASQL)',
    'NOTAS_PARCIAL_DB': 'Base que usa Notas mitad de parcial (padres_sqlserver = Test2 · academico_real = AdmonANASQL)',
    'NOTAS_PARCIAL_AREAS_REAL': 'Áreas que ya leen de la base real, separadas por coma',
    'GOOGLE_FORMS_SHARED_TOKEN': 'Llave del formulario de Google del compensatorio (Reloj). Sin ella el enlace responde 403.',
    'TICKET_IMAGE_PATH': 'Ruta de imágenes de tickets (antigua)',
    'EMAILS_REALES': 'Enviar correos de verdad (true) o solo a la consola (false)',
    'RED_CRED_KEY': 'Clave propia para cifrar contraseñas de Red (si falta, se deriva de la clave maestra)',
    'INV_TEST2_MOSTRAR_TARJETA': 'Mostrar la tarjeta de Inventario SQL en el hub de Contabilidad',
    'USE_SQLSERVER': 'Conectar a SQL Server (true/false)', 'USE_WHITENOISE': 'Servir estáticos con WhiteNoise (pruebas)',
}
_SUFIJOS = [('_PASSWORD', 'Contraseña'), ('_USER', 'Usuario'), ('_HOST', 'Servidor'), ('_PORT', 'Puerto'),
            ('_NAME', 'Base de datos'), ('_USE_TLS', 'Usa TLS'), ('_USE_SSL', 'Usa SSL')]


def es_secreto(k):
    return any(x in k for x in ('PASSWORD', 'SECRET', 'TOKEN', '_KEY'))


def grupo_de(k):
    if k.startswith('DJANGO_') or k in ('USE_WHITENOISE', 'COOKIES_SECURE', 'EMAILS_REALES'): return 'django'
    if k.startswith('DB_'): return 'mysql'
    if k.startswith('MSSQL_ZKBIO'): return 'zkbio'
    if k.startswith('MSSQL_') or k == 'USE_SQLSERVER': return 'test2'
    if k.startswith('INV_TEST2'): return 'inv'
    if k.startswith('EMAIL_ENF'): return 'enf'
    if k.startswith('EMAIL_COORD_BL'): return 'cbl'
    if k.startswith('EMAIL_COORD_COL'): return 'ccol'
    if k.startswith('EMAIL_'): return 'correo'
    if k.startswith('NOTAS_PARCIAL'): return 'notas'
    if k.startswith(('ANTHROPIC', 'OPENAI', 'ASISTENTE')): return 'ia'
    return 'otros'


def tipo_de(k):
    if es_secreto(k): return 'secreto'
    if k.startswith('NOTAS_PARCIAL') or k in BOOL_MINUS or k in ('ASISTENTE_MODELO',): return 'ajuste'
    return 'conexion'


def etiqueta(k):
    if k in _ETIQUETAS: return _ETIQUETAS[k]
    for suf, txt in _SUFIJOS:
        if k.endswith(suf): return txt
    return ''


def ruta_archivo():
    return Path(getattr(settings, 'TECHCARE_ENV_FILE', '') or (Path(settings.BASE_DIR) / '.env'))


def dir_respaldos():
    return Path(getattr(settings, 'TECHCARE_ENV_BACKUP_DIR', '') or (Path(settings.BASE_DIR) / '.env_respaldos'))


def estado_archivo():
    p, b = ruta_archivo(), dir_respaldos()
    existe = p.is_file()
    return {
        'ruta': str(p), 'existe': existe,
        'escribible': existe and os.access(p, os.W_OK),
        'respaldo_ok': b.is_dir() and os.access(b, os.W_OK),
        'respaldos': str(b),
    }


_USO = None


def usadas_en_codigo():
    """Nombres que el código lee con os.getenv / os.environ (se calcula una vez por proceso)."""
    global _USO
    if _USO is None:
        pat = re.compile(r"""os\.(?:getenv|environ\.get|environ\[)\(?\s*['"]([A-Z][A-Z0-9_]+)""")
        usadas = set()
        for raiz, dirs, files in os.walk(settings.BASE_DIR):
            dirs[:] = [d for d in dirs if d not in ('migrations', '__pycache__', 'staticfiles', 'media', 'node_modules', 'venv') and not d.startswith('.')]
            for f in files:
                if f.endswith('.py'):
                    try:
                        usadas.update(pat.findall(open(os.path.join(raiz, f), encoding='utf-8', errors='ignore').read()))
                    except OSError:
                        pass
        _USO = usadas
    return _USO


def _lineas():
    p = ruta_archivo()
    return p.read_text(encoding='utf-8').splitlines() if p.is_file() else []


def _parse_linea(l):
    """→ (clave, activa) o None."""
    s = l.strip()
    activa = True
    if s.startswith(PREFIJO_OFF.strip()):
        s, activa = s[len(PREFIJO_OFF.strip()):].strip(), False
    elif s.startswith('#'):
        return None
    if s.startswith('export '):
        s = s[7:].lstrip()
    m = re.match(r'([A-Za-z_][A-Za-z0-9_]*)\s*=', s)
    return (m.group(1), activa) if m else None


def valores_archivo():
    """Valores del archivo (activos y deshabilitados) parseados igual que python-dotenv."""
    act, off = {}, {}
    lineas = _lineas()
    if not lineas:
        return act, off
    act = {k: v for k, v in dotenv_values(ruta_archivo()).items()}
    offs = [l.strip()[len(PREFIJO_OFF.strip()):].strip() for l in lineas if l.strip().startswith(PREFIJO_OFF.strip())]
    if offs:
        import io
        off = dict(dotenv_values(stream=io.StringIO('\n'.join(offs))))
    return act, off


def listar():
    """Filas por grupo, SIN valores."""
    estado = estado_archivo()
    act, off = valores_archivo()
    usadas = usadas_en_codigo()
    claves = set(act) | set(off) | usadas
    if not estado['existe']:
        claves |= {k for k in usadas if k in os.environ}
    filas = []
    for k in sorted(claves):
        en_proceso = os.environ.get(k)
        if estado['existe']:
            definida = k in act
            pendiente = definida and (act.get(k) or '') != (en_proceso or '')
            pendiente = pendiente or (not definida and en_proceso is not None and k in off)
        else:
            definida, pendiente = en_proceso is not None, False
        filas.append({
            'k': k, 'grupo': grupo_de(k), 'tipo': tipo_de(k), 'etiqueta': etiqueta(k),
            'definida': definida, 'deshabilitada': k in off and k not in act,
            'vacia': definida and not ((act.get(k) if estado['existe'] else en_proceso) or ''),
            'en_uso': k in usadas, 'pendiente': pendiente,
            'editable': k not in NO_EDITABLES,
            'bool': 'mayus' if BOOL_MAYUS.search(k) else ('minus' if k in BOOL_MINUS else ''),
        })
    grupos = []
    for g, nombre, icono, color in GRUPOS:
        fs = [f for f in filas if f['grupo'] == g]
        if fs:
            grupos.append({'g': g, 'nombre': nombre, 'icono': icono, 'color': color, 'filas': fs})
    return grupos, filas


def valor(k):
    act, off = valores_archivo()
    return {'actual': os.environ.get(k), 'archivo': act.get(k, off.get(k)) if ruta_archivo().is_file() else None}


def validar(k, v):
    if not CLAVE_RE.match(k or ''):
        return 'El nombre debe ir en MAYÚSCULAS, con letras, números y _ (ej. MI_VARIABLE).'
    if k in NO_EDITABLES:
        return 'Esta variable no se puede cambiar desde aquí.'
    if v is None:
        return None
    if '\n' in v or '\r' in v or '\x00' in v:
        return 'El valor no puede tener saltos de línea.'
    if len(v) > 2000:
        return 'El valor es demasiado largo.'
    if k.endswith('_PORT') and v and not v.isdecimal():
        return 'El puerto debe ser un número.'
    if BOOL_MAYUS.search(k) and v not in ('True', 'False'):
        return 'Debe ser True o False.'
    if k in BOOL_MINUS and v not in ('true', 'false'):
        return 'Debe ser true o false.'
    if k == 'NOTAS_PARCIAL_DB' and v not in settings.DATABASES:
        return 'Base desconocida. Opciones: ' + ', '.join(settings.DATABASES)
    if k == 'NOTAS_PARCIAL_AREAS_REAL' and v and not re.fullmatch(r'[a-z_]+(,[a-z_]+)*', v.replace(' ', '')):
        return 'Áreas separadas por coma, en minúsculas (ej. primaria_bl,colegio_bl).'
    return None


def _formatear(v):
    if re.fullmatch(r'[A-Za-z0-9_./:@,+=%\-]*', v):
        return v
    if "'" not in v:
        return "'" + v + "'"
    return '"' + v.replace('\\', '\\\\').replace('"', '\\"') + '"'


def guardar(k, accion, v=None):
    """accion: editar | agregar | deshabilitar | habilitar. Devuelve (ok, mensaje)."""
    est = estado_archivo()
    if not est['existe']:
        return False, 'Este servidor no tiene archivo .env: aquí las variables se editan en Coolify (Environment Variables) y luego Redeploy.'
    if not est['escribible']:
        return False, 'El servidor no tiene permiso para escribir el .env. No se cambió nada.'
    if not est['respaldo_ok']:
        return False, f'No se puede crear el respaldo en {est["respaldos"]}. Sin respaldo no se guarda nada.'
    err = validar(k, v if accion in ('editar', 'agregar') else None)
    if err:
        return False, err
    p = ruta_archivo()
    original = p.read_text(encoding='utf-8')
    lineas = original.splitlines()
    idx = [i for i, l in enumerate(lineas) if (_parse_linea(l) or ('',))[0] == k]
    activos = [i for i in idx if _parse_linea(lineas[i])[1]]
    if accion == 'agregar':
        if idx:
            return False, f'{k} ya existe.'
        lineas.append(f'{k}={_formatear(v)}')
    elif accion == 'editar':
        if not activos:
            return False, f'{k} no está activa en el archivo (habilítala o agrégala).'
        for i in activos[:-1]:
            lineas[i] = None          # duplicadas: manda la última, como python-dotenv
        lineas[activos[-1]] = f'{k}={_formatear(v)}'
        lineas = [l for l in lineas if l is not None]
    elif accion == 'deshabilitar':
        if not activos:
            return False, f'{k} no está activa.'
        for i in activos:
            lineas[i] = PREFIJO_OFF + lineas[i].strip()
    elif accion == 'habilitar':
        if activos:
            return False, f'{k} ya está activa.'
        offs = [i for i in idx if not _parse_linea(lineas[i])[1]]
        if not offs:
            return False, f'{k} no existe.'
        for i in offs[:-1]:
            lineas[i] = None
        lineas[offs[-1]] = lineas[offs[-1]].strip()[len(PREFIJO_OFF):]
        lineas = [l for l in lineas if l is not None]
    else:
        return False, 'Acción desconocida.'
    sello = datetime.datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    resp = dir_respaldos() / f'env_{sello}.bak'
    shutil.copyfile(p, resp)
    os.chmod(resp, 0o600)
    nuevo = '\n'.join(lineas) + '\n'
    with open(p, 'w', encoding='utf-8') as fh:   # en su lugar: conserva dueño, grupo y permisos (640 www-data)
        fh.write(nuevo)
    # verificación: lo escrito debe leerse igual; si no, se restaura el respaldo
    act, off = valores_archivo()
    ok = {'editar': act.get(k) == v, 'agregar': act.get(k) == v,
          'deshabilitar': k not in act and k in off, 'habilitar': k in act}[accion]
    if not ok:
        with open(p, 'w', encoding='utf-8') as fh:
            fh.write(original)
        return False, 'La verificación falló y se restauró el archivo original. No se cambió nada.'
    return True, 'Guardado. Se aplica al reiniciar el servidor.'


# ── Probar conexiones (no revela valores) ──
PRUEBAS = {
    'default': ('db', 'MySQL'), 'padres_sqlserver': ('db', 'SQL Server Test2'),
    'academico_real': ('db', 'SQL Server AdmonANASQL'), 'zkbio_sqlserver': ('db', 'SQL Server reloj'),
    'inventario_test2': ('db', 'SQL Server inventario'),
    'correo': ('smtp', 'EMAIL_'), 'enf': ('smtp', 'EMAIL_ENF_'), 'cbl': ('smtp', 'EMAIL_COORD_BL_'), 'ccol': ('smtp', 'EMAIL_COORD_COL_'),
}
PRUEBA_DE_GRUPO = {'mysql': 'default', 'test2': 'padres_sqlserver', 'zkbio': 'zkbio_sqlserver', 'inv': 'inventario_test2',
                   'correo': 'correo', 'enf': 'enf', 'cbl': 'cbl', 'ccol': 'ccol'}


def probar(destino):
    if destino not in PRUEBAS:
        return False, 'Prueba desconocida.'
    tipo, ref = PRUEBAS[destino]
    if tipo == 'db':
        from django.db import connections
        if destino not in settings.DATABASES:
            return False, 'Esa conexión no está activa en este servidor.'
        try:
            with connections[destino].cursor() as c:
                c.execute('SELECT 1')
                c.fetchone()
            return True, 'Conexión correcta.'
        except Exception as e:  # noqa: BLE001
            return False, 'No conecta: ' + type(e).__name__ + ' — ' + str(e)[:180]
    import smtplib, ssl
    g = lambda s, d='': os.environ.get(ref + s, d)  # noqa: E731
    pre = ref
    host = g('HOST'); port = int(g('PORT', '587') or 587)
    user = os.environ.get('EMAIL_HOST_USER') if pre == 'EMAIL_' else g('USER')
    pwd = os.environ.get('EMAIL_HOST_PASSWORD') if pre == 'EMAIL_' else g('PASSWORD')
    if not host:
        return False, 'No tiene servidor configurado.'
    try:
        if g('USE_SSL', 'False') == 'True':
            s = smtplib.SMTP_SSL(host, port, timeout=8, context=ssl.create_default_context())
        else:
            s = smtplib.SMTP(host, port, timeout=8)
            if g('USE_TLS', 'True') == 'True':
                s.starttls(context=ssl.create_default_context())
        if user:
            s.login(user, pwd or '')
        s.quit()
        return True, 'El servidor de correo aceptó el usuario y la contraseña.'
    except smtplib.SMTPAuthenticationError:
        return False, 'El servidor rechazó el usuario o la contraseña.'
    except Exception as e:  # noqa: BLE001
        return False, 'No conecta: ' + type(e).__name__ + ' — ' + str(e)[:180]
