# <--- hecho por claude code (14-oct-2026): cliente mínimo de los Servicios Web REST de Moodle.
import base64
import json
import re
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 60


class MoodleError(Exception):
    pass


def ws(conexion, funcion, **params):
    """Llama a una función del servicio web de Moodle y devuelve el JSON. Lanza MoodleError con un mensaje claro."""
    if not conexion.token:
        raise MoodleError('Falta el token de Moodle (guárdalo en "Conexión").')
    url = conexion.url.rstrip('/') + '/webservice/rest/server.php'
    datos = dict(params, wstoken=conexion.token, wsfunction=funcion, moodlewsrestformat='json')
    try:
        with urllib.request.urlopen(url, data=urllib.parse.urlencode(datos).encode(), timeout=TIMEOUT) as r:
            cuerpo = r.read()
    except urllib.error.URLError as e:
        raise MoodleError(f'No se pudo conectar con Moodle ({conexion.url}): {getattr(e, "reason", e)}')
    except TimeoutError:
        raise MoodleError(f'Moodle no respondió en {TIMEOUT} s.')
    try:
        res = json.loads(cuerpo)
    except ValueError:
        raise MoodleError('Moodle respondió algo que no es JSON (¿la dirección es correcta?).')
    if isinstance(res, dict) and res.get('exception'):
        raise MoodleError(f"Moodle: {res.get('message') or res.get('errorcode')} [{res.get('errorcode')}]")
    return res


def info(conexion):
    return ws(conexion, 'core_webservice_get_site_info')


def cursos(conexion):
    """Todos los cursos que ve el usuario del token (sin el sitio, id 1), ordenados por nombre."""
    res = ws(conexion, 'core_course_get_courses_by_field')
    lista = [c for c in res.get('courses', []) if c.get('id') != 1]
    return sorted(lista, key=lambda c: (c.get('fullname') or '').lower())


def publicar(conexion, curso_id, nombre_archivo, contenido, alt, target_cmid=0):
    # <--- hecho por claude code (15-oct-2026): el plugin v0.2 pone su propio nombre y rechaza nombres/textos con
    # caracteres especiales → se manda un nombre neutro y el texto alternativo sin < > " ni saltos de línea.
    # <--- 28-oct-2026: target_cmid>0 reemplaza una imagen que ya está en General (plugin v0.3) y la adopta como agenda.
    ext = 'jpg' if str(nombre_archivo).lower().endswith(('.jpg', '.jpeg')) else 'png'
    alt = re.sub(r'[<>"\\\s]+', ' ', alt or '').strip()[:200] or 'Agenda semanal'
    extra = {}
    # Solo se manda si se eligió reemplazar: el plugin v0.2 rechaza parámetros que no conoce, así que
    # las publicaciones normales siguen funcionando aunque todavía no se haya actualizado a v0.3.
    if int(target_cmid or 0) > 0:
        extra['targetcmid'] = int(target_cmid)
    return ws(conexion, 'local_techcareagenda_publicar', courseid=int(curso_id), filename=f'agenda.{ext}',
              filecontent=base64.b64encode(contenido).decode(), alttext=alt, **extra)


def listar_general(conexion, curso_id):
    """Imágenes que YA hay en la sección General del curso (plugin v0.3), para elegir cuál reemplazar.
    [{cmid, nombre, modname, archivo, miniatura, reemplazable, esagenda}]. Lista vacía si el plugin es viejo."""
    try:
        res = ws(conexion, 'local_techcareagenda_listar', courseid=int(curso_id))
    except MoodleError:
        # Plugin anterior a v0.3 (sin la función): no hay nada que listar, se publica normal.
        return []
    return res.get('items', []) if isinstance(res, dict) else []


# ── Agrupar por grado-sección (hecho por claude code, 15-oct-2026) ──────────────────────────────────────
# Los cursos del Moodle de ANA se llaman  AAAA-Área-Clase-Grado-Sección  (ej. 2026-PrimBl-Mathematics-1ero-1).
# La clase puede traer guiones; grado y sección son siempre los dos últimos trozos.
AREAS_MOODLE = [('PrepaBl', 'Prepa Bilingüe'), ('KindBl', 'Kínder Bilingüe'), ('PrimBl', 'Primaria Bilingüe'),
                ('ColBl', 'Colegio Bilingüe'), ('Col', 'Colegio'), ('Bach', 'Bachillerato')]
_ORDEN_AREA = {a: i for i, (a, _) in enumerate(AREAS_MOODLE)}
_NOMBRE_AREA = dict(AREAS_MOODLE)
_RX_CURSO = re.compile(r'^(\d{4})-([^-]+)-(.+)-([^-]+)-([^-]+)$')


def _num(grado):
    m = re.match(r'\d+', grado or '')
    return int(m.group()) if m else 99


def agrupar(cursos):
    """[{key, anio, area, area_nombre, grado, seccion, etiqueta, cursos:[{id, clase, nombre}]}] + 'Otros cursos' al final."""
    grupos, otros = {}, []
    for c in cursos:
        nombre = c.get('nombre') or ''
        m = _RX_CURSO.match(nombre.strip())
        if not m:
            otros.append({'id': c['id'], 'clase': nombre, 'nombre': nombre})
            continue
        anio, area, clase, grado, seccion = m.groups()
        key = f'{anio}|{area}|{grado}|{seccion}'
        g = grupos.setdefault(key, {'key': key, 'anio': anio, 'area': area, 'area_nombre': _NOMBRE_AREA.get(area, area),
                                    'grado': grado, 'seccion': seccion, 'etiqueta': f'{grado}-{seccion}', 'cursos': []})
        g['cursos'].append({'id': c['id'], 'clase': clase.strip(), 'nombre': nombre})
    lista = sorted(grupos.values(), key=lambda g: (-int(g['anio']), _ORDEN_AREA.get(g['area'], 50), g['area'],
                                                     _num(g['grado']), g['grado'], g['seccion']))
    for g in lista:
        g['cursos'].sort(key=lambda x: x['clase'].lower())
    if otros:
        lista.append({'key': 'otros', 'anio': '', 'area': 'otros', 'area_nombre': 'Otros cursos', 'grado': '',
                      'seccion': '', 'etiqueta': 'Otros cursos', 'cursos': sorted(otros, key=lambda x: x['clase'].lower())})
    return lista


# ── Acceso de coordinadores a la pantalla de Moodle (hecho por claude code, 28-oct-2026) ───────────────
# Pedido del usuario: habilitar la pantalla /moodle-upload/ (solo Publicar + Historial, SIN la pestaña
# Conexión, que administra el token) a druiz y cvarela, y que cada uno vea SOLO sus cursos (áreas bilingües):
#   cvarela → kínder, prepa y primaria 1ro-3ro ;  druiz → primaria 4to-6to y colegio bilingüe (hasta 9no).
_AREAS_BL = {'PrepaBl', 'KindBl', 'PrimBl', 'ColBl'}
COORD_CURSOS = {   # username (= correo) -> regla(area, nº de grado) que decide si un grupo de agrupar() es suyo
    'cvarela@ana-hn.org': lambda area, n: area in ('KindBl', 'PrepaBl') or (area == 'PrimBl' and n <= 3),
    'druiz@ana-hn.org':   lambda area, n: (area == 'PrimBl' and n >= 4) or area == 'ColBl',
}


def puede_ver_pantalla(user):
    """¿Puede abrir la pantalla de Moodle? Superusuario siempre; druiz y cvarela también (Publicar + Historial)."""
    return bool(getattr(user, 'is_authenticated', False)
                and (getattr(user, 'is_superuser', False) or user.get_username() in COORD_CURSOS))


def filtrar_para(grupos, user):
    """Grupos de agrupar() visibles para el usuario. Superusuario: todos. Coordinador: solo sus cursos BL."""
    if getattr(user, 'is_superuser', False):
        return grupos
    regla = COORD_CURSOS.get(user.get_username())
    if not regla:
        return []
    return [g for g in grupos if g.get('area') in _AREAS_BL and regla(g['area'], _num(g.get('grado')))]


def cursos_permitidos_ids(grupos, user):
    """Conjunto de curso_id (str) que el usuario puede publicar — candado del servidor en 'publicar'."""
    return {str(c['id']) for g in filtrar_para(grupos, user) for c in g['cursos']}


# Grado de Agendas → grupo de Moodle. Colegio: 7mo-9no = Col 1ero-3ero; 10mo-11vo = Bach 1ero-2do.
_COLEGIO_A_MOODLE = {'7mo': ('Col', '1ero'), '8vo': ('Col', '2do'), '9no': ('Col', '3ero'),
                     '10mo': ('Bach', '1ero'), '11vo': ('Bach', '2do')}


def grupo_sugerido(grupos, area_agenda, nombre_grado):
    """key del grupo que corresponde al grado de la agenda (el año más reciente), o ''."""
    partes = (nombre_grado or '').lower().split()
    if not partes:
        return ''
    grado = {'3ro': '3ero', '1ro': '1ero'}.get(partes[0], partes[0])
    seccion = partes[1] if len(partes) > 1 else ''
    if area_agenda == 'primaria':
        area, seccion = 'PrimBl', seccion or '1'
    elif area_agenda == 'colegio_bl':
        area, seccion = 'ColBl', seccion or '1'
    elif area_agenda == 'colegio' and grado in _COLEGIO_A_MOODLE:
        area, grado = _COLEGIO_A_MOODLE[grado]
    else:
        return ''
    for g in grupos:   # ya vienen del año más reciente primero
        if g['area'] == area and g['grado'].lower() == grado and g['seccion'].lower() == seccion.lower():
            return g['key']
    return ''
