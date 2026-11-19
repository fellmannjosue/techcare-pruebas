# <--- hecho por claude code (10-nov-2026): pruebas del rol Auditoría (core/auditoria.py)
import json

from django.contrib.auth.models import Group, User
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from core import auditoria


@override_settings(ALLOWED_HOSTS=['*'])
class AuditoriaTests(TestCase):
    def setUp(self):
        self.aud = User.objects.create_user('aud@ana-hn.org', 'aud@ana-hn.org', 'Clave-Prueba-123')
        self.aud.groups.add(Group.objects.create(name=auditoria.GRUPO))
        self.su = User.objects.create_superuser('su@ana-hn.org', 'su@ana-hn.org', 'Clave-Prueba-123')
        self.rf = RequestFactory()

    def _mw(self, request, fn):
        return auditoria.AuditoriaMiddleware(fn)(request)

    def _req(self, method, path, user):
        r = getattr(self.rf, method)(path)
        r.user = User.objects.get(pk=user.pk)
        from django.contrib.sessions.backends.db import SessionStore
        r.session = SessionStore()
        return r

    def test_get_ve_como_superusuario_y_revierte_escrituras(self):
        visto = {}
        def vista(req):
            visto['su'] = req.user.is_superuser
            Group.objects.create(name='creado-en-get')
            return HttpResponse('ok')
        resp = self._mw(self._req('get', '/reloj/', self.aud), vista)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(visto['su'])
        self.assertFalse(Group.objects.filter(name='creado-en-get').exists())

    def test_post_bloqueado_por_defecto(self):
        def vista(req):
            Group.objects.create(name='creado-en-post')
            return HttpResponse('ok')
        resp = self._mw(self._req('post', '/reloj/algo/', self.aud), vista)
        self.assertEqual(resp.status_code, 403)
        self.assertFalse(Group.objects.filter(name='creado-en-post').exists())

    def test_post_permitido_en_programa_habilitado(self):
        from constance import config
        config.AUDITORIA_EDITAR = json.dumps(['reloj'])
        try:
            resp = self._mw(self._req('post', '/reloj/algo/', self.aud), lambda r: HttpResponse('ok'))
            self.assertEqual(resp.status_code, 200)
            resp = self._mw(self._req('post', '/sponsors/algo/', self.aud), lambda r: HttpResponse('ok'))
            self.assertEqual(resp.status_code, 403)
        finally:
            config.AUDITORIA_EDITAR = ''

    def test_zonas_prohibidas_aunque_sea_get(self):
        for ruta in ('/admin/', '/accounts/iniciar-como/5/', '/accounts/settings/auditoria-rol/'):
            resp = self._mw(self._req('get', ruta, self.aud), lambda r: HttpResponse('ok'))
            self.assertEqual(resp.status_code, 403, ruta)

    def test_la_elevacion_nunca_se_guarda(self):
        def vista(req):
            req.user.first_name = 'Cambio'
            req.user.save()
            return HttpResponse('ok')
        from constance import config
        config.AUDITORIA_EDITAR = json.dumps(['reloj'])
        try:
            self._mw(self._req('post', '/reloj/x/', self.aud), vista)
        finally:
            config.AUDITORIA_EDITAR = ''
        u = User.objects.get(pk=self.aud.pk)
        self.assertFalse(u.is_superuser)
        self.assertFalse(u.is_staff)

    def test_superusuario_real_no_se_toca(self):
        resp = self._mw(self._req('post', '/sponsors/x/', self.su), lambda r: HttpResponse('ok'))
        self.assertEqual(resp.status_code, 200)

    def test_login_y_pantalla_de_superusuario(self):
        c = self.client
        r = c.post('/accounts/login/', {'username': 'aud@ana-hn.org', 'password': 'Clave-Prueba-123'},
                   SERVER_NAME='servicios.ana-hn.org')
        self.assertEqual(r.status_code, 302, getattr(r, 'content', b'')[:300])
        r = c.get('/accounts/settings/canales/', SERVER_NAME='servicios.ana-hn.org')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Modo auditoría')
        r = c.post('/accounts/settings/canales/toggle/', {'canal': 'web', 'programa': 'reloj', 'visible': '0'},
                   SERVER_NAME='servicios.ana-hn.org', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 403)
        self.assertFalse(User.objects.get(pk=self.aud.pk).is_superuser)
