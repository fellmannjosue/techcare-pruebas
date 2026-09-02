# <--- hecho por claude code: formularios del módulo de desarrollo (FASE 2).
from django import forms

from .models import (RequerimientoDesarrollo, ProyectoDesarrollo,
                     ComentarioRequerimiento, AdjuntoRequerimiento, SolicitanteCatalogo,
                     OpcionCatalogo)
from .utils import validar_adjunto


_SELECT = {'class': 'form-select'}
_INPUT  = {'class': 'form-control'}
_AREA   = {'class': 'form-control', 'rows': 3}


class RequerimientoNuevoForm(forms.ModelForm):
    """Registrar un requerimiento nuevo (secciones: general, requerimiento, clasificación)."""
    class Meta:
        model = RequerimientoDesarrollo
        fields = [
            'solicitante_cat', 'area', 'modulo', 'proyecto',
            'titulo', 'tipo', 'descripcion', 'problema_actual', 'resultado_esperado',
            'prioridad', 'impacto', 'urgencia', 'usuarios_afectados', 'clasificacion',
        ]
        widgets = {
            'solicitante_cat': forms.Select(attrs={**_SELECT, 'id': 'id_solicitante_cat'}),
            'area':   forms.TextInput(attrs=_INPUT),
            'modulo': forms.TextInput(attrs=_INPUT),
            'proyecto': forms.Select(attrs=_SELECT),
            'titulo': forms.TextInput(attrs=_INPUT),
            'tipo':   forms.Select(attrs=_SELECT),
            'descripcion':       forms.Textarea(attrs=_AREA),
            'problema_actual':   forms.Textarea(attrs=_AREA),
            'resultado_esperado': forms.Textarea(attrs=_AREA),
            'prioridad': forms.Select(attrs=_SELECT),
            'impacto':   forms.Select(attrs=_SELECT),
            'urgencia':  forms.Select(attrs=_SELECT),
            'usuarios_afectados': forms.TextInput(attrs=_INPUT),
            'clasificacion': forms.Select(attrs=_SELECT),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proyecto'].queryset = ProyectoDesarrollo.objects.order_by('nombre')
        self.fields['proyecto'].required = False
        self.fields['proyecto'].empty_label = '— Sin proyecto (por ahora) —'
        self.fields['solicitante_cat'].queryset = SolicitanteCatalogo.objects.filter(activo=True)
        self.fields['solicitante_cat'].required = False
        self.fields['solicitante_cat'].empty_label = '— Seleccionar —'
        if not self.initial.get('solicitante_cat'):
            dflt = SolicitanteCatalogo.objects.filter(activo=True, nombre__iexact='Soporte Técnico').first()
            if dflt:
                self.initial['solicitante_cat'] = dflt.pk

        # Área y Módulo: Select agregable desde el catálogo (guardan texto).
        for campo, grupo, fid in (('area', 'area', 'id_area'), ('modulo', 'modulo', 'id_modulo')):
            opciones = [('', '— Seleccionar —')] + [
                (o.valor, o.valor)
                for o in OpcionCatalogo.objects.filter(grupo=grupo, activo=True)]
            self.fields[campo].required = False
            self.fields[campo].widget = forms.Select(attrs={**_SELECT, 'id': fid}, choices=opciones)


class RequerimientoEditForm(forms.ModelForm):
    """Seguimiento: actualizar estado/avance/responsable y datos de desarrollo.
    El historial de estado/responsable/avance lo maneja la vista con registrar_cambio()."""
    class Meta:
        model = RequerimientoDesarrollo
        fields = [
            'estado', 'responsable', 'prioridad', 'impacto', 'urgencia',
            'proyecto', 'fecha_inicio', 'fecha_estimada', 'fecha_finalizacion',
            'porcentaje_avance', 'version_implementada', 'observaciones',
        ]
        widgets = {
            'estado':      forms.Select(attrs=_SELECT),
            'responsable': forms.Select(attrs=_SELECT),
            'prioridad':   forms.Select(attrs=_SELECT),
            'impacto':     forms.Select(attrs=_SELECT),
            'urgencia':    forms.Select(attrs=_SELECT),
            'proyecto':    forms.Select(attrs=_SELECT),
            'fecha_inicio':      forms.DateInput(attrs={**_INPUT, 'type': 'date'}),
            'fecha_estimada':    forms.DateInput(attrs={**_INPUT, 'type': 'date'}),
            'fecha_finalizacion': forms.DateInput(attrs={**_INPUT, 'type': 'date'}),
            'porcentaje_avance': forms.NumberInput(attrs={**_INPUT, 'min': 0, 'max': 100}),
            'version_implementada': forms.TextInput(attrs=_INPUT),
            'observaciones': forms.Textarea(attrs=_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields['proyecto'].queryset = ProyectoDesarrollo.objects.order_by('nombre')
        self.fields['proyecto'].required = False
        self.fields['responsable'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'username')
        self.fields['responsable'].required = False


class ProyectoForm(forms.ModelForm):
    """Alta / edición de un proyecto de desarrollo (FASE 3)."""
    # <--- hecho por claude code: Usuarios beneficiados = multi-select de todos los usuarios.
    usuarios_beneficiados = forms.MultipleChoiceField(
        required=False, label="Usuarios beneficiados",
        widget=forms.SelectMultiple(attrs={'class': 'form-select', 'size': '6'}))

    class Meta:
        model = ProyectoDesarrollo
        fields = [
            'nombre', 'modulo', 'area', 'subarea',
            'descripcion', 'problema_que_resuelve',
            'responsable', 'estado', 'prioridad',
            'fecha_inicio', 'fecha_implementacion',
            'version_inicial', 'version_actual',
            'tecnologia_principal', 'base_datos', 'app_django', 'ruta', 'url',
            'en_produccion',
            'proxima_mejora', 'observaciones',
        ]
        widgets = {
            'nombre':  forms.TextInput(attrs=_INPUT),
            'modulo':  forms.TextInput(attrs=_INPUT),
            'area':    forms.TextInput(attrs=_INPUT),
            'subarea': forms.TextInput(attrs=_INPUT),
            'descripcion':           forms.Textarea(attrs=_AREA),
            'problema_que_resuelve': forms.Textarea(attrs=_AREA),
            'responsable': forms.Select(attrs=_SELECT),
            'estado':      forms.Select(attrs=_SELECT),
            'prioridad':   forms.Select(attrs=_SELECT),
            'fecha_inicio':         forms.DateInput(attrs={**_INPUT, 'type': 'date'}),
            'fecha_implementacion': forms.DateInput(attrs={**_INPUT, 'type': 'date'}),
            'version_inicial': forms.TextInput(attrs=_INPUT),
            'version_actual':  forms.TextInput(attrs=_INPUT),
            'tecnologia_principal': forms.TextInput(attrs={**_INPUT, 'readonly': True}),
            'base_datos': forms.Select(attrs=_SELECT, choices=[
                ('sponsors', 'sponsors (MySQL principal)'),
                ('sqlserver', 'sqlserver (SQL Server)'),
            ]),
            'app_django': forms.TextInput(attrs=_INPUT),
            'ruta':       forms.TextInput(attrs={**_INPUT, 'placeholder': 'ej. system_proyect/desarrollo'}),
            'url':        forms.TextInput(attrs={**_INPUT, 'placeholder': 'ej. /desarrollo/'}),
            'en_produccion': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'proxima_mejora': forms.TextInput(attrs=_INPUT),
            'observaciones':  forms.Textarea(attrs=_AREA),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from django.contrib.auth.models import User
        self.fields['responsable'].queryset = User.objects.filter(is_active=True).order_by('first_name', 'username')
        self.fields['responsable'].required = False
        # <--- hecho por claude code: Tecnología principal fija en Python; BD por defecto sponsors.
        if not (self.initial.get('tecnologia_principal') or getattr(self.instance, 'tecnologia_principal', '')):
            self.initial['tecnologia_principal'] = 'Python'
        if not (self.initial.get('base_datos') or getattr(self.instance, 'base_datos', '')):
            self.initial['base_datos'] = 'sponsors'
        # Usuarios beneficiados: opciones = todos los usuarios activos; valor = username
        usuarios = User.objects.filter(is_active=True).order_by('first_name', 'username')
        self.fields['usuarios_beneficiados'].choices = [
            (u.username, (u.get_full_name() or u.username)) for u in usuarios]
        actuales = (getattr(self.instance, 'usuarios_beneficiados', '') or '')
        if actuales and not self.initial.get('usuarios_beneficiados'):
            self.initial['usuarios_beneficiados'] = [x.strip() for x in actuales.split(',') if x.strip()]

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.usuarios_beneficiados = ', '.join(self.cleaned_data.get('usuarios_beneficiados', []))[:200]
        if commit:
            obj.save()
        return obj


class ConvertirProyectoForm(forms.Form):
    """Convertir un requerimiento en proyecto: datos base (se precargan desde el req)."""
    nombre = forms.CharField(max_length=160, widget=forms.TextInput(attrs=_INPUT))
    modulo = forms.CharField(max_length=120, required=False, widget=forms.TextInput(attrs=_INPUT))
    area   = forms.CharField(max_length=60, required=False, widget=forms.TextInput(attrs=_INPUT))
    descripcion = forms.CharField(required=False, widget=forms.Textarea(attrs=_AREA))


class ComentarioForm(forms.ModelForm):
    class Meta:
        model = ComentarioRequerimiento
        fields = ['comentario']
        widgets = {'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 2,
                                                       'placeholder': 'Escribe una nota de bitácora…'})}


class AdjuntoForm(forms.ModelForm):
    class Meta:
        model = AdjuntoRequerimiento
        fields = ['archivo', 'descripcion']
        widgets = {
            'archivo': forms.ClearableFileInput(attrs={'class': 'form-control'}),
            'descripcion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Descripción (opcional)'}),
        }

    def clean_archivo(self):
        f = self.cleaned_data.get('archivo')
        if f:
            validar_adjunto(f)
        return f
