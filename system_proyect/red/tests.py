# <--- hecho por claude code: ANA Network Manager — pruebas Fase 1
from django.test import TestCase
from django.core.exceptions import ValidationError

from .models import VLAN, IPAddress
from . import services


def _vlan(**kw):
    base = dict(vlan_id=99, nombre='TEST', subred='192.168.99.0/24', gateway='192.168.99.1',
                ip_inicial_asignable='192.168.99.2', ip_final_asignable='192.168.99.11',  # 10 IPs
                porcentaje_alerta=20)
    base.update(kw)
    return VLAN.objects.create(**base)


class ValidacionVLANTests(TestCase):
    def test_cidr_invalido(self):
        v = VLAN(vlan_id=10, nombre='x', subred='no-cidr')
        self.assertTrue(any('CIDR' in e or 'subred' in e for e in services.validar_vlan(v)))

    def test_vlan_id_fuera_rango(self):
        v = VLAN(vlan_id=5000, nombre='x', subred='192.168.1.0/24')
        self.assertTrue(any('1 y 4094' in e for e in services.validar_vlan(v)))

    def test_gateway_fuera_de_subred(self):
        v = VLAN(vlan_id=10, nombre='x', subred='192.168.1.0/24', gateway='10.0.0.1')
        self.assertTrue(any('Gateway' in e for e in services.validar_vlan(v)))

    def test_gateway_no_broadcast(self):
        v = VLAN(vlan_id=10, nombre='x', subred='192.168.1.0/24', gateway='192.168.1.255')
        self.assertTrue(any('broadcast' in e for e in services.validar_vlan(v)))

    def test_reservado_dhcp_solapados(self):
        v = VLAN(vlan_id=10, nombre='x', subred='192.168.1.0/24',
                 ip_inicio_reservado='192.168.1.2', ip_fin_reservado='192.168.1.50',
                 ip_inicio_dhcp='192.168.1.40', ip_fin_dhcp='192.168.1.100')
        self.assertTrue(any('superpon' in e for e in services.validar_vlan(v)))

    def test_solape_subredes(self):
        _vlan(vlan_id=1, nombre='a', subred='192.168.99.0/24')
        self.assertTrue(services.subredes_solapadas('192.168.99.0/25'))


class CapacidadTests(TestCase):
    def test_capacidad_usa_rango_no_254(self):
        v = _vlan()  # rango .2-.11 = 10 IP
        cap = services.capacidad_vlan(v)
        self.assertEqual(cap['capacidad'], 10)   # NO 254

    def test_estados_alerta(self):
        v = _vlan()  # 10 IP
        services.generar_ips_vlan(v)
        # asignar 8 → quedan 2 → 20% libre → advertencia o menos
        for ip in IPAddress.objects.filter(vlan=v).order_by('direccion_int')[:8]:
            ip.estado = 'asignada'; ip.save()
        cap = services.capacidad_vlan(v)
        self.assertEqual(cap['libres'], 2)
        self.assertIn(cap['estado'], ('advertencia', 'critico'))
        # asignar 1 más → 1 libre (10%) → critico
        ip9 = IPAddress.objects.filter(vlan=v, estado='libre').first()
        ip9.estado = 'asignada'; ip9.save()
        self.assertEqual(services.capacidad_vlan(v)['estado'], 'critico')
        # asignar la última → agotado
        ip10 = IPAddress.objects.filter(vlan=v, estado='libre').first()
        ip10.estado = 'asignada'; ip10.save()
        self.assertEqual(services.capacidad_vlan(v)['estado'], 'agotado')


class IPAMTests(TestCase):
    def test_generar_ips_idempotente(self):
        v = _vlan()
        n1 = services.generar_ips_vlan(v)
        n2 = services.generar_ips_vlan(v)
        self.assertEqual(n1, 10)
        self.assertEqual(n2, 0)   # no duplica

    def test_fuera_de_rango(self):
        v = _vlan()
        self.assertFalse(services.dentro_rango_asignable(v, '192.168.99.200'))
        self.assertTrue(services.dentro_rango_asignable(v, '192.168.99.5'))

    def test_asignar_fuera_de_rango_falla(self):
        v = _vlan()
        ip = IPAddress.objects.create(vlan=v, direccion='192.168.99.200', estado='libre')
        with self.assertRaises(ValidationError):
            services.asignar_ip(ip, hostname='pc')

    def test_ip_duplicada(self):
        v = _vlan()
        IPAddress.objects.create(vlan=v, direccion='192.168.99.5', estado='asignada')
        self.assertTrue(services.ip_duplicada(v, '192.168.99.5'))

    def test_mac_duplicada(self):
        v = _vlan()
        IPAddress.objects.create(vlan=v, direccion='192.168.99.5', estado='asignada', mac='AA:BB:CC:DD:EE:FF')
        self.assertTrue(services.mac_duplicada('AA:BB:CC:DD:EE:FF'))

    def test_liberar_conserva_registro(self):
        v = _vlan()
        ip = IPAddress.objects.create(vlan=v, direccion='192.168.99.5', estado='asignada', hostname='pc')
        services.liberar_ip(ip)
        ip.refresh_from_db()
        self.assertEqual(ip.estado, 'libre')
        self.assertEqual(ip.hostname, '')
        self.assertTrue(IPAddress.objects.filter(pk=ip.pk).exists())  # NO se borró


# ── Fase 2: switches / puertos / enlaces ──
from .models import Switch, SwitchPort, NetworkLink, Device


class PuertoTests(TestCase):
    def test_access_con_tagged_falla(self):
        p = SwitchPort(modo_vlan='access', vlans_tagged='30,45')
        self.assertTrue(any('Access' in e for e in services.validar_puerto(p)))

    def test_poe_incoherente(self):
        p = SwitchPort(poe_habilitado=True, poe_disponible=False)
        self.assertTrue(any('PoE' in e for e in services.validar_puerto(p)))


class EnlaceTests(TestCase):
    def _sw(self, admin=True):
        d = Device.objects.create(nombre='sw-dev', tipo='switch_adm')
        s = Switch.objects.create(nombre='SW', administrable=admin, device=d)
        return d, s

    def test_puerto_consigo_mismo(self):
        d, s = self._sw()
        p = SwitchPort.objects.create(switch=s, numero=1)
        l = NetworkLink(nombre='x', dispositivo_origen=d, dispositivo_destino=d,
                        puerto_origen=p, puerto_destino=p)
        errores, _ = services.validar_link(l)
        self.assertTrue(any('consigo mismo' in e for e in errores))

    def test_trunk_no_administrable_avisa(self):
        d, s = self._sw(admin=False)
        d2 = Device.objects.create(nombre='core', tipo='switch_adm')
        l = NetworkLink(nombre='x', tipo='rj45', modo='trunk',
                        dispositivo_origen=d2, dispositivo_destino=d)
        _, avisos = services.validar_link(l)
        self.assertTrue(any('NO administrable' in a for a in avisos))

    def test_deteccion_ciclo(self):
        a = Device.objects.create(nombre='A', tipo='switch_adm')
        b = Device.objects.create(nombre='B', tipo='switch_adm')
        c = Device.objects.create(nombre='C', tipo='switch_adm')
        NetworkLink.objects.create(nombre='ab', dispositivo_origen=a, dispositivo_destino=b)
        NetworkLink.objects.create(nombre='bc', dispositivo_origen=b, dispositivo_destino=c)
        NetworkLink.objects.create(nombre='ca', dispositivo_origen=c, dispositivo_destino=a)
        self.assertTrue(len(services.detectar_ciclos()) > 0)
