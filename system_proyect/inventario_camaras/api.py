# inventario_camaras/api.py
# <--- hecho por claude code: API JSON para el frontend Next (build estático).
# Usa la MISMA sesión de Django (mismo dominio), así que no hay CORS ni JWT:
# si el usuario no inició sesión, la API responde 403.
from django.db.models import Count, Q
from rest_framework import serializers, viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response

from .models import (Servidor, NVR, Componente, Gabinete, Camara,
                     TipoFallaCamara, MantenimientoCamara)


class NormalizaVaciosMixin:
    """<--- hecho por claude code: el formulario manda "" cuando el campo queda vacío,
    pero los campos no textuales (IP, número de canales…) esperan null. Sin esto,
    dejar la IP en blanco devolvía 400 "Este campo no puede estar en blanco."."""
    def to_internal_value(self, data):
        if isinstance(data, dict):
            limpio = {}
            for clave, valor in data.items():
                campo = self.fields.get(clave)
                # Ojo: IPAddressField de DRF hereda de CharField, así que no sirve
                # mirar el tipo. El criterio correcto es: acepta nulo pero no vacío.
                if (valor == '' and campo is not None
                        and campo.allow_null and not getattr(campo, 'allow_blank', False)):
                    valor = None
                limpio[clave] = valor
            data = limpio
        return super().to_internal_value(data)


class SoloStaff(permissions.BasePermission):
    """Mismo criterio que el resto del módulo: staff autenticado."""
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and (u.is_staff or u.is_superuser))


# ── Serializers ────────────────────────────────────────────────────────────
class ComponenteSerializer(NormalizaVaciosMixin, serializers.ModelSerializer):
    etiqueta = serializers.SerializerMethodField()

    class Meta:
        model = Componente
        fields = ['id', 'comp_id', 'detalle', 'sub_detalle', 'etiqueta']
        read_only_fields = ['comp_id']

    def get_etiqueta(self, o):
        return f"{o.detalle} / {o.sub_detalle}" if o.sub_detalle else o.detalle


class CamaraSerializer(NormalizaVaciosMixin, serializers.ModelSerializer):
    gabinete_nombre = serializers.CharField(source='gabinete.nombre', read_only=True, default='')

    class Meta:
        model = Camara
        fields = ['id', 'camara_id', 'modelo', 'serie', 'ubicacion', 'gabinete',
                  'gabinete_nombre', 'grupo', 'estado', 'version_actualizada', 'observaciones']
        read_only_fields = ['camara_id']


class GabineteSerializer(NormalizaVaciosMixin, serializers.ModelSerializer):
    nvr_nombre = serializers.CharField(source='nvr.nombre', read_only=True, default='')
    n_camaras = serializers.IntegerField(read_only=True)

    class Meta:
        model = Gabinete
        fields = ['id', 'gabinete_id', 'nombre', 'ubicacion', 'nvr', 'nvr_nombre',
                  'componentes', 'observaciones', 'n_camaras']
        read_only_fields = ['gabinete_id']


class NVRSerializer(NormalizaVaciosMixin, serializers.ModelSerializer):
    servidor_nombre = serializers.CharField(source='servidor.nombre', read_only=True, default='')
    n_gabinetes = serializers.IntegerField(read_only=True)

    class Meta:
        model = NVR
        fields = ['id', 'nvr_id', 'nombre', 'modelo', 'serie', 'ip', 'canales',
                  'servidor', 'servidor_nombre', 'observaciones', 'n_gabinetes']
        read_only_fields = ['nvr_id']


class ServidorSerializer(NormalizaVaciosMixin, serializers.ModelSerializer):
    n_nvrs = serializers.IntegerField(read_only=True)

    class Meta:
        model = Servidor
        fields = ['id', 'server_id', 'nombre', 'ubicacion', 'ip', 'observaciones', 'n_nvrs']
        read_only_fields = ['server_id']


class TipoFallaSerializer(NormalizaVaciosMixin, serializers.ModelSerializer):
    class Meta:
        model = TipoFallaCamara
        fields = ['id', 'nombre']


class MantenimientoSerializer(NormalizaVaciosMixin, serializers.ModelSerializer):
    tipo_falla_nombre = serializers.CharField(source='tipo_falla.nombre', read_only=True, default='')

    class Meta:
        model = MantenimientoCamara
        fields = ['id', 'record_id', 'grupo', 'camara', 'modelo', 'serie', 'ubicacion',
                  'tipo_falla', 'tipo_falla_nombre', 'solucion', 'date', 'status',
                  'observaciones', 'responsable_nombre', 'tecnico_nombre', 'firma_solicitada']
        read_only_fields = ['record_id']


# ── ViewSets ───────────────────────────────────────────────────────────────
class BaseVS(viewsets.ModelViewSet):
    permission_classes = [SoloStaff]


class ServidorVS(BaseVS):
    serializer_class = ServidorSerializer
    queryset = Servidor.objects.annotate(n_nvrs=Count('nvrs')).order_by('server_id')


class NVRVS(BaseVS):
    serializer_class = NVRSerializer

    def get_queryset(self):
        qs = NVR.objects.select_related('servidor').annotate(n_gabinetes=Count('gabinetes'))
        srv = self.request.query_params.get('servidor')
        return (qs.filter(servidor_id=srv) if srv else qs).order_by('nvr_id')


class GabineteVS(BaseVS):
    serializer_class = GabineteSerializer

    def get_queryset(self):
        qs = Gabinete.objects.select_related('nvr').annotate(n_camaras=Count('camaras'))
        nvr = self.request.query_params.get('nvr')
        return (qs.filter(nvr_id=nvr) if nvr else qs).order_by('gabinete_id')


class CamaraVS(BaseVS):
    serializer_class = CamaraSerializer

    def get_queryset(self):
        qs = Camara.objects.select_related('gabinete')
        gab = self.request.query_params.get('gabinete')
        q = self.request.query_params.get('q')
        if gab:
            qs = qs.filter(gabinete_id=gab)
        if q:
            qs = qs.filter(Q(camara_id__icontains=q) | Q(modelo__icontains=q) |
                           Q(serie__icontains=q) | Q(ubicacion__icontains=q))
        return qs.order_by('camara_id')


class ComponenteVS(BaseVS):
    serializer_class = ComponenteSerializer
    queryset = Componente.objects.all()


class TipoFallaVS(BaseVS):
    serializer_class = TipoFallaSerializer
    queryset = TipoFallaCamara.objects.all().order_by('nombre')


class MantenimientoVS(BaseVS):
    serializer_class = MantenimientoSerializer

    def get_queryset(self):
        qs = MantenimientoCamara.objects.select_related('tipo_falla')
        est = self.request.query_params.get('status')
        return (qs.filter(status=est) if est else qs).order_by('-date', '-id')


# ── Resumen para el árbol y las tarjetas ──────────────────────────────────
@api_view(['GET'])
@permission_classes([SoloStaff])
def resumen(request):
    """Conteos + árbol Servidor → NVR → Gabinete → Cámara en una sola llamada."""
    arbol = []
    for s in Servidor.objects.prefetch_related('nvrs__gabinetes__camaras').order_by('server_id'):
        arbol.append({
            'id': s.id, 'codigo': s.server_id, 'nombre': s.nombre, 'ubicacion': s.ubicacion,
            'nvrs': [{
                'id': n.id, 'codigo': n.nvr_id, 'nombre': n.nombre, 'ip': n.ip,
                'gabinetes': [{
                    'id': g.id, 'codigo': g.gabinete_id, 'nombre': g.nombre,
                    'camaras': [{'id': c.id, 'codigo': c.camara_id, 'modelo': c.modelo,
                                 'ubicacion': c.ubicacion, 'estado': c.estado}
                                for c in g.camaras.all()],
                } for g in n.gabinetes.all()],
            } for n in s.nvrs.all()],
        })
    mant = MantenimientoCamara.objects.values('status').annotate(n=Count('id'))
    return Response({
        'conteos': {
            'servidores': Servidor.objects.count(),
            'nvrs': NVR.objects.count(),
            'gabinetes': Gabinete.objects.count(),
            'camaras': Camara.objects.count(),
            'componentes': Componente.objects.count(),
            'mantenimientos': MantenimientoCamara.objects.count(),
        },
        'mantenimiento_por_estado': {m['status']: m['n'] for m in mant},
        'arbol': arbol,
        'usuario': {'nombre': request.user.get_full_name() or request.user.username,
                    'es_superusuario': request.user.is_superuser},
    })
