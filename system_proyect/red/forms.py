# <--- hecho por claude code: ANA Network Manager — formularios
from django import forms

from .models import (VLAN, IPAddress, Device, NetworkInterface,
                     Campus, Edificio, Ubicacion, Gabinete)
from . import services

_I = {'class': 'form-control'}
_S = {'class': 'form-select'}


class BootstrapMixin:
    """Aplica clases Bootstrap a todos los campos (para no repetir widgets)."""
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        for f in self.fields.values():
            w = f.widget
            if isinstance(w, forms.CheckboxInput):
                w.attrs.setdefault('class', 'form-check-input')
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                w.attrs.setdefault('class', 'form-select')
            elif isinstance(w, forms.DateInput):
                w.attrs.setdefault('class', 'form-control'); w.attrs.setdefault('type', 'date')
            else:
                w.attrs.setdefault('class', 'form-control')


class VLANForm(forms.ModelForm):
    class Meta:
        model = VLAN
        fields = [
            'vlan_id', 'nombre', 'descripcion', 'subred', 'gateway', 'mascara',
            'servidor_dhcp', 'tipo_dhcp', 'dns_principal', 'dns_secundario',
            'ip_inicial_asignable', 'ip_final_asignable',
            'ip_inicio_reservado', 'ip_fin_reservado',
            'ip_inicio_dhcp', 'ip_fin_dhcp',
            'limite_dispositivos', 'porcentaje_alerta',
            'politica_meraki', 'color', 'estado',
            'permite_internet', 'permite_comunicacion_interna', 'observaciones',
        ]
        widgets = {
            'vlan_id': forms.NumberInput(attrs={**_I, 'min': 1, 'max': 4094}),
            'nombre': forms.TextInput(attrs=_I),
            'descripcion': forms.TextInput(attrs=_I),
            'subred': forms.TextInput(attrs={**_I, 'placeholder': '192.168.60.0/24'}),
            'gateway': forms.TextInput(attrs=_I),
            'mascara': forms.TextInput(attrs={**_I, 'placeholder': '255.255.255.0'}),
            'servidor_dhcp': forms.TextInput(attrs=_I),
            'tipo_dhcp': forms.Select(attrs=_S),
            'dns_principal': forms.TextInput(attrs=_I),
            'dns_secundario': forms.TextInput(attrs=_I),
            'ip_inicial_asignable': forms.TextInput(attrs=_I),
            'ip_final_asignable': forms.TextInput(attrs=_I),
            'ip_inicio_reservado': forms.TextInput(attrs=_I),
            'ip_fin_reservado': forms.TextInput(attrs=_I),
            'ip_inicio_dhcp': forms.TextInput(attrs=_I),
            'ip_fin_dhcp': forms.TextInput(attrs=_I),
            'limite_dispositivos': forms.NumberInput(attrs={**_I, 'min': 0}),
            'porcentaje_alerta': forms.NumberInput(attrs={**_I, 'min': 1, 'max': 100}),
            'politica_meraki': forms.TextInput(attrs=_I),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'estado': forms.Select(attrs=_S),
            'permite_internet': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'permite_comunicacion_interna': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.Textarea(attrs={**_I, 'rows': 2}),
        }

    def clean(self):
        cd = super().clean()
        # validación de negocio (CIDR, gateway/rangos dentro de subred, solapes reservado/DHCP)
        tmp = VLAN(**{k: cd.get(k) for k in self.Meta.fields if k in cd})
        for err in services.validar_vlan(tmp):
            self.add_error(None, err)
        return cd


class IPForm(forms.ModelForm):
    """Formulario de IP estándar (alta/edición de una dirección)."""
    class Meta:
        model = IPAddress
        fields = ['direccion', 'estado', 'tipo', 'dispositivo', 'mac', 'hostname',
                  'responsable', 'descripcion', 'observaciones']
        widgets = {
            'direccion': forms.TextInput(attrs={**_I, 'placeholder': '192.168.60.10'}),
            'estado': forms.Select(attrs=_S),
            'tipo': forms.Select(attrs=_S),
            'dispositivo': forms.Select(attrs=_S),
            'mac': forms.TextInput(attrs=_I),
            'hostname': forms.TextInput(attrs=_I),
            'responsable': forms.TextInput(attrs=_I),
            'descripcion': forms.TextInput(attrs=_I),
            'observaciones': forms.TextInput(attrs=_I),
        }

    def __init__(self, *args, vlan=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.vlan = vlan
        self.fields['dispositivo'].queryset = Device.objects.all().order_by('nombre')
        self.fields['dispositivo'].required = False

    def clean(self):
        cd = super().clean()
        vlan = self.vlan or (self.instance.vlan if self.instance.pk else None)
        direccion = cd.get('direccion')
        if vlan and direccion:
            if not services.dentro_rango_asignable(vlan, direccion):
                self.add_error('direccion', 'La dirección está fuera del rango autorizado de la VLAN.')
            if services.ip_duplicada(vlan, direccion, exclude_pk=self.instance.pk):
                self.add_error('direccion', 'Esa IP ya existe en la VLAN (duplicada).')
        mac = cd.get('mac')
        if mac and services.mac_duplicada(mac, exclude_pk=self.instance.pk):
            self.add_error('mac', 'Esa MAC ya está registrada en otra IP.')
        return cd


# ── Ubicaciones ────────────────────────────────────────────────────────────
class CampusForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Campus
        fields = ['nombre', 'descripcion', 'direccion', 'activo']


class EdificioForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Edificio
        fields = ['campus', 'codigo', 'nombre', 'descripcion', 'color', 'activo']
        widgets = {'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'})}


class UbicacionForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Ubicacion
        fields = ['edificio', 'padre', 'tipo', 'codigo', 'nombre', 'descripcion', 'responsable', 'activo']

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        if self.instance.pk:
            self.fields['padre'].queryset = Ubicacion.objects.exclude(pk=self.instance.pk)


class GabineteForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Gabinete
        fields = ['ubicacion', 'codigo', 'nombre', 'unidades_rack', 'ups', 'observaciones', 'fotografia', 'activo']


# ── Dispositivos ───────────────────────────────────────────────────────────
class DeviceForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Device
        fields = ['codigo_interno', 'nombre', 'hostname', 'tipo', 'fabricante', 'modelo',
                  'numero_serie', 'mac_principal', 'ubicacion', 'gabinete', 'vlan', 'ip',
                  'metodo_direccionamiento', 'sistema_operativo', 'responsable', 'estado',
                  'criticidad', 'fecha_compra', 'garantia', 'fotografia', 'observaciones']
        widgets = {'observaciones': forms.Textarea(attrs={'rows': 2}),
                   'fecha_compra': forms.DateInput(attrs={'type': 'date'})}


class InterfaceForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = NetworkInterface
        fields = ['nombre', 'tipo', 'mac', 'vlan', 'ip', 'dhcp', 'velocidad', 'activa', 'observaciones']


# ── Fase 2: Switches / Puertos / Enlaces ───────────────────────────────────
from .models import Switch, SwitchPort, NetworkLink  # noqa: E402


class SwitchForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Switch
        fields = ['nombre', 'device', 'fabricante', 'modelo', 'ip_admin', 'mac_admin',
                  'ubicacion', 'gabinete', 'administrable', 'poe', 'cantidad_puertos',
                  'cantidad_puertos_sfp', 'firmware', 'usuario_responsable', 'url_admin',
                  'estado', 'fecha_ultimo_respaldo', 'observaciones']
        labels = {'device': 'Dispositivo vinculado (opcional)'}
        widgets = {'observaciones': forms.Textarea(attrs={'rows': 2}),
                   'fecha_ultimo_respaldo': forms.DateInput(attrs={'type': 'date'})}


class SwitchPortForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = SwitchPort
        fields = ['numero', 'nombre', 'tipo', 'velocidad', 'poe_disponible', 'poe_habilitado',
                  'estado_fisico', 'modo_vlan', 'vlan_access', 'vlan_nativa', 'vlans_tagged',
                  'dispositivo_conectado', 'puerto_remoto', 'descripcion', 'ubicacion_destino',
                  'cable_identificado', 'etiqueta_fisica', 'fecha_ultima_validacion',
                  'validado_por', 'observaciones']
        widgets = {'observaciones': forms.Textarea(attrs={'rows': 2}),
                   'fecha_ultima_validacion': forms.DateInput(attrs={'type': 'date'})}

    def clean(self):
        cd = super().clean()
        tmp = SwitchPort(**{k: cd.get(k) for k in self.Meta.fields if k in cd})
        for e in services.validar_puerto(tmp):
            self.add_error(None, e)
        return cd


class NetworkLinkForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = NetworkLink
        fields = ['nombre', 'tipo', 'dispositivo_origen', 'puerto_origen', 'dispositivo_destino',
                  'puerto_destino', 'modo', 'vlan_nativa', 'vlans_permitidas', 'velocidad',
                  'estado', 'es_respaldo', 'longitud_m', 'etiqueta_cable', 'fecha_validacion',
                  'observaciones']
        widgets = {'observaciones': forms.Textarea(attrs={'rows': 2}),
                   'fecha_validacion': forms.DateInput(attrs={'type': 'date'})}

    def clean(self):
        cd = super().clean()
        tmp = NetworkLink(**{k: cd.get(k) for k in self.Meta.fields if k in cd})
        errores, _ = services.validar_link(tmp)
        for e in errores:
            self.add_error(None, e)
        return cd


# ── Fase 3: mapa de campus ─────────────────────────────────────────────────
from .models import Plano, Marcador  # noqa: E402


class PlanoForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Plano
        fields = ['nombre', 'edificio', 'imagen', 'descripcion', 'orden', 'activo']
