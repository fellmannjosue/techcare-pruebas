# <--- hecho por claude code (14-oct-2026): cliente mínimo de los Servicios Web REST de Moodle.
import base64
import json
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


def publicar(conexion, curso_id, nombre_archivo, contenido, alt):
    return ws(conexion, 'local_techcareagenda_publicar', courseid=int(curso_id), filename=nombre_archivo,
              filecontent=base64.b64encode(contenido).decode(), alttext=alt or 'Agenda semanal')
