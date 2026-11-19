# core/tests_seguridad.py
# <--- hecho por claude code (09-nov-2026, revisión ISO 27001/COBIT): pruebas de seguridad con DATOS SINTÉTICOS.
"""Pruebas de seguridad de TechCare.

Corren contra una base SQLite en memoria (system_proyect/settings_test.py): nunca tocan MySQL, SQL Server
ni correo real. Todos los usuarios, alumnos e imágenes son inventados.

    cd system_proyect
    DJANGO_SECRET_KEY=solo-pruebas ../venv/bin/python manage.py test core.tests_seguridad \
        --settings=system_proyect.settings_test
"""
import io
import json
import shutil
import tempfile

from django.contrib.auth.models import Group, User
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

HOST = 'servicios.ana-hn.org'
_MEDIA = tempfile.mkdtemp(prefix='tc_test_media_')


def _png():
    from PIL import Image
    buf = io.BytesIO()
    Image.new('RGB', (2, 2), (200, 30, 30)).save(buf, 'PNG')
    return buf.getvalue()


class _Base(TestCase):
    def setUp(self):
        cache.clear()

    def cliente(self, user=None, ip='192.168.10.50'):
        c = self.client_class(SERVER_NAME=HOST, REMOTE_ADDR=ip, secure=True)
        if user:
            c.force_login(user)
        return c


# ── 1. Acceso sin sesión ───────────────────────────────────────────────────
class AccesoSinSesionTests(_Base):
    RUTAS = [
        '/enfermeria/atencion/', '/conducta/evidencia/1/ver/', '/accounts/settings/canales/',
        '/tickets/mis-tickets/', '/reloj/', '/salidas-bano/', '/ingresos-notas/', '/red/', '/inventario/',
        '/notas-parcial/', '/desarrollo/', '/accounts/seguridad/',
    ]

    def test_toda_ruta_privada_pide_sesion(self):
        c = self.cliente()
        for ruta in self.RUTAS:
            r = c.get(ruta)
            self.assertEqual(r.status_code, 302, ruta)
            self.assertIn('/accounts/login/', r['Location'], ruta)

    def test_login_es_publico(self):
        self.assertEqual(self.cliente().get('/accounts/login/').status_code, 200)


# ── 2. Evidencias de Conducta (fotos de menores) ───────────────────────────
@override_settings(MEDIA_ROOT=_MEDIA)
class EvidenciaConductaTests(_Base):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(_MEDIA, ignore_errors=True)

    def setUp(self):
        super().setUp()
        from conducta.models import EvidenciaReporte, ReporteInformativo
        g_mbl, _ = Group.objects.get_or_create(name='maestros_bilingue')
        g_cbl, _ = Group.objects.get_or_create(name='coordinador_bilingue')
        g_ccol, _ = Group.objects.get_or_create(name='coordinador_colegio')
        self.autor = User.objects.create_user('maestra_sintetica', password='x-Prueba-123')
        self.autor.groups.add(g_mbl)
        self.otro_maestro = User.objects.create_user('maestro_ajeno', password='x-Prueba-123')
        self.otro_maestro.groups.add(g_mbl)
        self.coord_bl = User.objects.create_user('coord_bl_sint', password='x-Prueba-123', is_staff=True)
        self.coord_bl.groups.add(g_cbl)
        self.coord_col = User.objects.create_user('coord_col_sint', password='x-Prueba-123', is_staff=True)
        self.coord_col.groups.add(g_ccol)
        rep = ReporteInformativo.objects.create(
            usuario=self.autor, area='bilingue', alumno_id='SINT-001', alumno_nombre='Alumno Ficticio',
            grado='3', materia='Math', docente='Docente Ficticio')
        self.ev = EvidenciaReporte.objects.create(
            tipo='informativo', reporte_informativo=rep,
            imagen=SimpleUploadedFile('WhatsApp Image 2026-11-09 at 10.00.00.png', _png(), 'image/png'))

    def url(self):
        return '/conducta/evidencia/%d/ver/' % self.ev.pk

    def test_nombre_de_archivo_no_adivinable(self):
        nombre = self.ev.imagen.name.rsplit('/', 1)[-1]
        self.assertNotIn('WhatsApp', nombre)
        self.assertRegex(nombre, r'^[0-9a-f]{32}\.png$')
        self.assertTrue(self.ev.imagen.name.startswith('evidencias/bilingue/informativo/'))

    def test_sin_sesion_redirige(self):
        r = self.cliente().get(self.url())
        self.assertEqual(r.status_code, 302)

    def test_otro_maestro_no_puede(self):
        self.assertEqual(self.cliente(self.otro_maestro).get(self.url()).status_code, 403)

    def test_coordinador_de_otra_area_no_puede(self):
        self.assertEqual(self.cliente(self.coord_col).get(self.url()).status_code, 403)

    def test_autor_y_coordinador_del_area_si(self):
        for u in (self.autor, self.coord_bl):
            r = self.cliente(u).get(self.url())
            self.assertEqual(r.status_code, 200, u.username)
            self.assertEqual(r['Content-Type'], 'image/png')
            self.assertEqual(r['X-Content-Type-Options'], 'nosniff')
            self.assertIn('no-store', r['Cache-Control'])
            b''.join(r.streaming_content)

    def test_id_inexistente_da_404_al_autorizado(self):
        r = self.cliente(self.coord_bl).get('/conducta/evidencia/999999/ver/')
        self.assertEqual(r.status_code, 404)

    def test_validacion_rechaza_archivo_que_no_es_imagen(self):
        from conducta.views import _evidencia_imagen_valida
        falso = SimpleUploadedFile('foto.jpg', b'<?php echo 1; ?>', 'image/jpeg')
        self.assertFalse(_evidencia_imagen_valida(falso))
        self.assertTrue(_evidencia_imagen_valida(SimpleUploadedFile('ok.png', _png(), 'image/png')))


# ── 3. Login: límites de intentos ──────────────────────────────────────────
class LoginLimitesTests(_Base):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser('super_sintetico', 'super@example.invalid', 'Correcta-123!')

    def _post(self, c, usuario, clave):
        return c.post('/accounts/login/', {'username': usuario, 'password': clave})

    def test_ip_publica_queda_en_espera_tras_20_fallos(self):
        c = self.cliente(ip='1.2.3.4')   # IP pública sintética (los rangos de documentación Python los trata como privados)
        for i in range(20):
            self._post(c, 'nadie%d' % i, 'mala')
        r = self._post(c, 'nadie_mas', 'mala')
        self.assertTrue(r.context.get('bloqueo_temp'))

    def test_ip_privada_no_bloquea_a_toda_la_red(self):
        c = self.cliente(ip='192.168.10.1')   # el gateway: casi toda la escuela llega por aquí
        for i in range(25):
            self._post(c, 'nadie%d' % i, 'mala')
        r = self._post(c, 'otro_usuario', 'mala')
        self.assertFalse(r.context.get('bloqueo_temp'))

    def test_superusuario_tiene_bloqueo_temporal_pero_nunca_total(self):
        c = self.cliente()
        for _ in range(3):
            self._post(c, 'super_sintetico', 'mala')
        r = self._post(c, 'super_sintetico', 'Correcta-123!')   # aun con la clave correcta, espera
        self.assertTrue(r.context.get('bloqueo_temp'))
        self.assertNotIn('_auth_user_id', c.session)
        self.admin.refresh_from_db()
        perfil = getattr(self.admin, 'perfil', None)
        self.assertFalse(bool(perfil and perfil.login_bloqueado))
        cache.clear()   # pasa el minuto
        r = self._post(c, 'super_sintetico', 'Correcta-123!')
        self.assertEqual(r.status_code, 302)

    def test_un_solo_registro_de_acceso_por_login(self):
        from accounts.models import RegistroAcceso
        self._post(self.cliente(), 'super_sintetico', 'Correcta-123!')
        self.assertEqual(RegistroAcceso.objects.filter(username='super_sintetico').count(), 1)


# ── 4. Bitácora de seguridad ───────────────────────────────────────────────
class BitacoraSeguridadTests(_Base):
    def test_login_fallido_queda_registrado_sin_la_clave(self):
        User.objects.create_user('u_sint', password='Correcta-123!')
        with self.assertLogs('techcare.seguridad', level='INFO') as cm:
            self.cliente().post('/accounts/login/', {'username': 'u_sint', 'password': 'ClaveSecretaMala99'})
        texto = '\n'.join(cm.output)
        self.assertIn('login_fallido', texto)
        self.assertNotIn('ClaveSecretaMala99', texto)

    def test_cambios_de_privilegio_grupo_y_contrasena(self):
        u = User.objects.create_user('u_priv', password='Correcta-123!')
        g = Group.objects.create(name='enfermeria')
        with self.assertLogs('techcare.seguridad', level='INFO') as cm:
            u.is_superuser = True
            u.save()
            u.groups.add(g)
            u.set_password('Otra-Clave-456!')
            u.save()
        texto = '\n'.join(cm.output)
        self.assertIn('usuario_privilegios', texto)
        self.assertIn('grupos_add', texto)
        self.assertIn('contrasena_cambiada', texto)
        self.assertNotIn('Otra-Clave-456!', texto)
        self.assertNotIn(u.password, texto)   # ni el hash

    def test_detalle_con_claves_sensibles_se_descarta(self):
        from core.seguridad_eventos import evento
        with self.assertLogs('techcare.seguridad', level='INFO') as cm:
            evento('prueba', None, password='NO-DEBE-SALIR', token='NO-DEBE-SALIR', diagnostico='NO', otro='si')
        texto = '\n'.join(cm.output)
        self.assertNotIn('NO-DEBE-SALIR', texto)
        self.assertNotIn('diagnostico', texto)
        self.assertIn('"otro": "si"', texto)

    def test_ip_ignora_x_forwarded_for(self):
        from core.seguridad_eventos import ip_cliente
        req = RequestFactory().get('/', REMOTE_ADDR='192.168.10.9', HTTP_X_FORWARDED_FOR='8.8.8.8')
        self.assertEqual(ip_cliente(req), '192.168.10.9')


# ── 5. Recuperación de contraseña ──────────────────────────────────────────
class RecuperacionTests(_Base):
    def test_limite_por_correo_y_misma_respuesta(self):
        User.objects.create_user('u_reset', email='reset@example.invalid', password='Correcta-123!')
        c = self.cliente()
        respuestas = [c.post('/accounts/password_reset/', {'email': 'reset@example.invalid'}) for _ in range(6)]
        self.assertTrue(all(r.status_code == 302 for r in respuestas))
        self.assertEqual(len({r['Location'] for r in respuestas}), 1)
        self.assertEqual(len(mail.outbox), 3)

    def test_correo_inexistente_responde_igual(self):
        r = self.cliente().post('/accounts/password_reset/', {'email': 'noexiste@example.invalid'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(len(mail.outbox), 0)


# ── 6. Descargas sin caché ─────────────────────────────────────────────────
class DescargasPrivadasTests(TestCase):
    def _mw(self, resp):
        from core.middleware import DescargasPrivadasMiddleware
        return DescargasPrivadasMiddleware(lambda req: resp)(RequestFactory().get('/x/'))

    def test_pdf_excel_y_adjuntos_sin_cache(self):
        for tipo in ('application/pdf',
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     'application/zip'):
            self.assertEqual(self._mw(HttpResponse(b'x', content_type=tipo))['Cache-Control'], 'private, no-store')
        r = HttpResponse(b'x', content_type='image/png')
        r['Content-Disposition'] = 'attachment; filename="a.png"'
        self.assertEqual(self._mw(r)['Cache-Control'], 'private, no-store')

    def test_paginas_html_y_cache_propia_no_se_tocan(self):
        self.assertFalse(self._mw(HttpResponse('<p>hola</p>')).has_header('Cache-Control'))
        r = HttpResponse(b'x', content_type='application/pdf')
        r['Cache-Control'] = 'max-age=60'
        self.assertEqual(self._mw(r)['Cache-Control'], 'max-age=60')


# ── 7. Configuración ───────────────────────────────────────────────────────
class ConfiguracionTests(TestCase):
    def test_ajustes_de_seguridad_de_produccion(self):
        import importlib
        prod = importlib.import_module('system_proyect.settings')   # la configuración REAL (no la de pruebas)
        self.assertTrue(prod.SESSION_COOKIE_SECURE and prod.CSRF_COOKIE_SECURE and prod.SESSION_COOKIE_HTTPONLY)
        self.assertEqual(prod.PASSWORD_RESET_TIMEOUT, 86400)
        self.assertFalse(prod.TECHCARE_CONFIAR_XFF)
        self.assertIn('core.middleware.TechCareLoginRequiredMiddleware', prod.MIDDLEWARE)
        self.assertIn('core.middleware.DescargasPrivadasMiddleware', prod.MIDDLEWARE)
        self.assertIn('techcare.seguridad', prod.LOGGING['loggers'])
        self.assertTrue(prod.SECURE_CONTENT_TYPE_NOSNIFF)


# ── 8. Configuración → Documentación ───────────────────────────────────────
class DocumentacionTests(_Base):
    def setUp(self):
        super().setUp()
        self.su = User.objects.create_superuser('su_doc', 'su@example.invalid', 'Correcta-123!')
        self.staff = User.objects.create_user('staff_doc', password='Correcta-123!', is_staff=True)

    def test_solo_superusuario(self):
        self.assertEqual(self.cliente().get('/accounts/settings/documentacion/').status_code, 302)
        r = self.cliente(self.staff).get('/accounts/settings/documentacion/')
        self.assertEqual(r.status_code, 302)
        self.assertNotIn('Matriz de riesgos', r.content.decode())

    def test_muestra_las_guias_y_enlaza_entre_ellas(self):
        r = self.cliente(self.su).get('/accounts/settings/documentacion/')
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn('Matriz de riesgos', html)
        self.assertIn('?doc=seguridad%2F02_matriz_riesgos.md', html)   # enlace relativo convertido
        r = self.cliente(self.su).get('/accounts/settings/documentacion/?doc=seguridad/politicas/politica_contrasenas.md')
        self.assertEqual(r.status_code, 200)
        self.assertIn('<table>', r.content.decode())

    def test_descarga_pdf(self):   # <--- hecho por claude code (10-nov-2026)
        url = '/accounts/settings/documentacion/pdf/'
        self.assertEqual(self.cliente(self.staff).get(url + '?doc=seguridad/README.md').status_code, 302)
        r = self.cliente(self.su).get(url + '?doc=seguridad/README.md')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r.content.startswith(b'%PDF'))
        self.assertIn('no-store', r['Cache-Control'])
        self.assertEqual(self.cliente(self.su).get(url + '?doc=../../.env').status_code, 404)
        r = self.cliente(self.su).get(url + '?carpeta=seguridad')
        self.assertEqual(r.status_code, 200)

    def test_no_abre_rutas_fuera_de_docs(self):
        for doc in ('../system_proyect/.env', '/etc/passwd', 'seguridad/../../README.md', 'no-existe.md'):
            r = self.cliente(self.su).get('/accounts/settings/documentacion/', {'doc': doc})
            self.assertEqual(r.status_code, 404, doc)

    def test_html_crudo_del_markdown_no_se_ejecuta(self):
        from accounts import views_documentacion as vd
        import tempfile as _tf
        from pathlib import Path
        with _tf.TemporaryDirectory() as d:
            p = Path(d) / 'x.md'
            p.write_text('# T\n\n<script>alert(1)</script>\n\n[x](javascript:alert(1))\n', encoding='utf-8')
            html = vd._render('x.md', p, {'x.md': p})
        self.assertNotIn('<script>', html)
        self.assertNotIn('href="javascript', html)   # sale como texto, nunca como enlace

    def test_todos_los_documentos_se_renderizan_y_sus_enlaces_internos_funcionan(self):
        import re
        from accounts import views_documentacion as vd
        docs = vd._listar()
        self.assertGreaterEqual(len(docs), 15)
        for rel, p in docs.items():
            html = vd._render(rel, p, docs)
            self.assertTrue(html.strip(), rel)
            sueltos = [h for h in re.findall(r'href="([^"]+)"', html)
                       if (h.endswith('.md') or h.endswith('/')) and not h.startswith(('/accounts/settings/documentacion/', 'http'))]
            self.assertEqual(sueltos, [], rel)   # todo enlace a otra guía apunta al visor
