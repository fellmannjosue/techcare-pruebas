from django import forms

from .models import (
    Servidor, NVR, Componente, Gabinete, Camara,
    TipoFallaCamara, MantenimientoCamara,
)

_TXT    = {'class': 'form-control'}
_SEL    = {'class': 'form-select'}
_AREA   = {'class': 'form-control', 'rows': 2}


class ServidorForm(forms.ModelForm):
    class Meta:
        model  = Servidor
        fields = ['nombre', 'ubicacion', 'ip', 'observaciones']
        widgets = {
            'nombre':        forms.TextInput(attrs=_TXT),
            'ubicacion':     forms.TextInput(attrs=_TXT),
            'ip':            forms.TextInput(attrs={**_TXT, 'placeholder': '192.168.x.x'}),
            'observaciones': forms.Textarea(attrs=_AREA),
        }


class NVRForm(forms.ModelForm):
    class Meta:
        model  = NVR
        fields = ['nombre', 'modelo', 'serie', 'ip', 'canales', 'servidor', 'observaciones']
        widgets = {
            'nombre':        forms.TextInput(attrs=_TXT),
            'modelo':        forms.TextInput(attrs=_TXT),
            'serie':         forms.TextInput(attrs=_TXT),
            'ip':            forms.TextInput(attrs={**_TXT, 'placeholder': '192.168.x.x'}),
            'canales':       forms.NumberInput(attrs=_TXT),
            'servidor':      forms.Select(attrs=_SEL),
            'observaciones': forms.Textarea(attrs=_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['servidor'].queryset = Servidor.objects.all().order_by('server_id')
        self.fields['servidor'].empty_label = '— Sin servidor —'


class ComponenteForm(forms.ModelForm):
    class Meta:
        model  = Componente
        fields = ['detalle', 'sub_detalle']
        widgets = {
            'detalle':     forms.TextInput(attrs=_TXT),
            'sub_detalle': forms.TextInput(attrs=_TXT),
        }


class GabineteForm(forms.ModelForm):
    class Meta:
        model  = Gabinete
        fields = ['nombre', 'ubicacion', 'nvr', 'componentes', 'observaciones']
        widgets = {
            'nombre':        forms.TextInput(attrs=_TXT),
            'ubicacion':     forms.TextInput(attrs=_TXT),
            'nvr':           forms.Select(attrs=_SEL),
            'componentes':   forms.SelectMultiple(attrs={'class': 'form-select', 'size': 8}),
            'observaciones': forms.Textarea(attrs=_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nvr'].queryset = NVR.objects.all().order_by('nvr_id')
        self.fields['nvr'].empty_label = '— Sin NVR —'
        self.fields['componentes'].queryset = Componente.objects.all().order_by('detalle', 'sub_detalle')
        self.fields['componentes'].required = False


class CamaraForm(forms.ModelForm):
    class Meta:
        model  = Camara
        fields = ['modelo', 'serie', 'ubicacion', 'gabinete', 'grupo',
                  'estado', 'version_actualizada', 'observaciones']
        widgets = {
            'modelo':              forms.TextInput(attrs=_TXT),
            'serie':               forms.TextInput(attrs=_TXT),
            'ubicacion':           forms.TextInput(attrs=_TXT),
            'gabinete':            forms.Select(attrs=_SEL),
            'grupo':               forms.TextInput(attrs={**_TXT, 'placeholder': 'Ej: Edificio A, Bloque 1'}),
            'estado':              forms.TextInput(attrs={**_TXT, 'placeholder': 'Ej: Activa, Dañada, En mantenimiento'}),
            'version_actualizada': forms.TextInput(attrs={**_TXT, 'placeholder': 'Ej: v1.2.3 / Sí / No'}),
            'observaciones':       forms.Textarea(attrs=_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['gabinete'].queryset = Gabinete.objects.all().order_by('gabinete_id')
        self.fields['gabinete'].empty_label = '— Sin gabinete —'


class MantenimientoCamaraForm(forms.ModelForm):
    class Meta:
        model  = MantenimientoCamara
        fields = ['grupo', 'tipo_falla', 'date', 'status', 'solucion', 'observaciones',
                  'responsable_nombre']
        widgets = {
            'grupo':             forms.Select(attrs=_SEL),
            'tipo_falla':        forms.Select(attrs=_SEL),
            'date':              forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status':            forms.Select(attrs=_SEL),
            'solucion':          forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones':     forms.Textarea(attrs=_AREA),
            'responsable_nombre':forms.TextInput(attrs=_TXT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # grupo: opciones = grupos distintos existentes en las cámaras
        grupos = (Camara.objects.exclude(grupo='').order_by('grupo')
                  .values_list('grupo', flat=True).distinct())
        self.fields['grupo'] = forms.ChoiceField(
            label='Grupo', required=True,
            choices=[('', '— Seleccionar grupo —')] + [(g, g) for g in grupos],
            widget=forms.Select(attrs=_SEL),
        )
        self.fields['tipo_falla'].queryset = TipoFallaCamara.objects.all().order_by('nombre')
        self.fields['tipo_falla'].empty_label = '— Tipo de falla —'
        for f in ('solucion', 'observaciones', 'responsable_nombre'):
            self.fields[f].required = False


class FirmaTecnicoForm(forms.Form):
    """Formulario público (sin login) para que el técnico firme por link."""
    tecnico_nombre = forms.CharField(
        label="Tu nombre completo", max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-lg',
                                       'placeholder': 'Nombre del técnico'})
    )
    firma_data = forms.CharField(widget=forms.HiddenInput, required=True)

    def clean_firma_data(self):
        data = self.cleaned_data.get('firma_data', '').strip()
        if not data or not data.startswith('data:image'):
            raise forms.ValidationError("Debes firmar antes de enviar.")
        return data
