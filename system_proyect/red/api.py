# <--- hecho por claude code: API REST de SOLO LECTURA del módulo Red (Fase 5 completa).
# Para integraciones (monitoreo, scripts, otros sistemas). Autenticación:
#   - sesión de Django (mismo dominio), o
#   - token DRF (header "Authorization: Token <clave>") para scripts/externos.
# Permiso: `red.ver_red` (o superuser). Nunca escribe: solo ReadOnlyModelViewSet.
from rest_framework import serializers, viewsets, permissions, filters
from rest_framework.authentication import SessionAuthentication, TokenAuthentication

from .models import VLAN, IPAddress, Device, Switch, SwitchPort, NetworkLink, Ubicacion, Gabinete


class PuedeVerRed(permissions.BasePermission):
    message = 'Se requiere el permiso red.ver_red.'

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_superuser or u.has_perm('red.ver_red')))


class _Base(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [PuedeVerRed]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]


# ── Serializers ──
class VLANSer(serializers.ModelSerializer):
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)

    class Meta:
        model = VLAN
        fields = ['id', 'vlan_id', 'nombre', 'descripcion', 'subred', 'gateway', 'mascara',
                  'ip_inicial_asignable', 'ip_final_asignable', 'ip_inicio_reservado', 'ip_fin_reservado',
                  'ip_inicio_dhcp', 'ip_fin_dhcp', 'limite_dispositivos', 'porcentaje_alerta',
                  'cantidad_ip_disponibles', 'estado_capacidad', 'color', 'estado', 'estado_display',
                  'permite_internet', 'permite_comunicacion_interna']


class IPSer(serializers.ModelSerializer):
    vlan_numero = serializers.IntegerField(source='vlan.vlan_id', read_only=True)
    dispositivo_nombre = serializers.CharField(source='dispositivo.nombre', read_only=True, default=None)

    class Meta:
        model = IPAddress
        fields = ['id', 'vlan', 'vlan_numero', 'direccion', 'estado', 'tipo', 'dispositivo',
                  'dispositivo_nombre', 'mac', 'hostname', 'descripcion', 'fecha_asignacion', 'activo']


class DeviceSer(serializers.ModelSerializer):
    tipo_display = serializers.CharField(source='get_tipo_display', read_only=True)
    ubicacion_nombre = serializers.CharField(source='ubicacion.nombre', read_only=True, default=None)
    vlan_numero = serializers.IntegerField(source='vlan.vlan_id', read_only=True, default=None)

    class Meta:
        model = Device
        fields = ['id', 'codigo_interno', 'nombre', 'hostname', 'tipo', 'tipo_display', 'fabricante',
                  'modelo', 'numero_serie', 'mac_principal', 'ubicacion', 'ubicacion_nombre', 'gabinete',
                  'vlan', 'vlan_numero', 'ip', 'metodo_direccionamiento', 'estado', 'criticidad',
                  'conectividad', 'latencia_ms', 'probado_en']


class SwitchPortSer(serializers.ModelSerializer):
    class Meta:
        model = SwitchPort
        fields = ['id', 'numero', 'nombre', 'tipo', 'velocidad', 'poe_habilitado', 'estado_fisico',
                  'modo_vlan', 'vlan_access', 'vlan_nativa', 'vlans_tagged', 'dispositivo_conectado',
                  'etiqueta_fisica']


class SwitchSer(serializers.ModelSerializer):
    puertos = SwitchPortSer(many=True, read_only=True)

    class Meta:
        model = Switch
        fields = ['id', 'nombre', 'fabricante', 'modelo', 'ip_admin', 'mac_admin', 'ubicacion', 'gabinete',
                  'administrable', 'poe', 'cantidad_puertos', 'cantidad_puertos_sfp', 'firmware', 'estado',
                  'conectividad', 'latencia_ms', 'probado_en', 'puertos']


class LinkSer(serializers.ModelSerializer):
    origen_nombre = serializers.CharField(source='dispositivo_origen.nombre', read_only=True, default=None)
    destino_nombre = serializers.CharField(source='dispositivo_destino.nombre', read_only=True, default=None)

    class Meta:
        model = NetworkLink
        fields = ['id', 'nombre', 'tipo', 'dispositivo_origen', 'origen_nombre', 'puerto_origen',
                  'dispositivo_destino', 'destino_nombre', 'puerto_destino', 'modo', 'vlan_nativa',
                  'vlans_permitidas', 'velocidad', 'estado', 'es_respaldo']


class UbicacionSer(serializers.ModelSerializer):
    edificio_nombre = serializers.CharField(source='edificio.nombre', read_only=True, default=None)

    class Meta:
        model = Ubicacion
        fields = ['id', 'nombre', 'edificio', 'edificio_nombre']


class GabineteSer(serializers.ModelSerializer):
    class Meta:
        model = Gabinete
        fields = ['id', 'codigo', 'nombre', 'ubicacion', 'unidades_rack', 'activo']


# ── ViewSets (solo lectura) ──
class VLANVS(_Base):
    queryset = VLAN.objects.all().order_by('vlan_id'); serializer_class = VLANSer
    search_fields = ['nombre', 'subred']; ordering_fields = ['vlan_id', 'nombre']


class IPVS(_Base):
    queryset = IPAddress.objects.select_related('vlan', 'dispositivo').order_by('direccion_int')
    serializer_class = IPSer
    search_fields = ['direccion', 'mac', 'hostname']; ordering_fields = ['direccion_int', 'estado']

    def get_queryset(self):
        qs = super().get_queryset()
        vlan = self.request.query_params.get('vlan')      # ?vlan=<vlan_id>
        estado = self.request.query_params.get('estado')  # ?estado=asignada
        if vlan:
            qs = qs.filter(vlan__vlan_id=vlan)
        if estado:
            qs = qs.filter(estado=estado)
        return qs


class DeviceVS(_Base):
    queryset = Device.objects.select_related('ubicacion', 'vlan').order_by('nombre'); serializer_class = DeviceSer
    search_fields = ['nombre', 'hostname', 'ip', 'mac_principal', 'codigo_interno']
    ordering_fields = ['nombre', 'tipo', 'conectividad']


class SwitchVS(_Base):
    queryset = Switch.objects.prefetch_related('puertos').order_by('nombre'); serializer_class = SwitchSer
    search_fields = ['nombre', 'ip_admin', 'modelo']


class LinkVS(_Base):
    queryset = NetworkLink.objects.select_related('dispositivo_origen', 'dispositivo_destino').order_by('id')
    serializer_class = LinkSer


class UbicacionVS(_Base):
    queryset = Ubicacion.objects.select_related('edificio').order_by('nombre'); serializer_class = UbicacionSer


class GabineteVS(_Base):
    queryset = Gabinete.objects.order_by('nombre'); serializer_class = GabineteSer
