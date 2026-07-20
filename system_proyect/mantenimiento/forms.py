from django import forms
from .models import MaintenanceRecord, TipoFalla


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model  = MaintenanceRecord
        # <--- hecho por claude code: + campos de impresora (variante en el mismo formulario)
        fields = ['tipo_equipo', 'computadora', 'impresora', 'model', 'serie',
                  'teacher_name', 'grade', 'area', 'tipo_falla',
                  'tipo_mant_impresora', 'estado_tinta',
                  'tinta_negra', 'tinta_magenta', 'tinta_amarillo', 'tinta_cyan', 'tipo_tinta',
                  'date', 'status', 'solucion', 'observaciones']
        widgets = {
            'tipo_equipo':  forms.HiddenInput(),
            'computadora':  forms.Select(attrs={'class': 'form-select'}),
            'impresora':    forms.Select(attrs={'class': 'form-select'}),
            'model':        forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'serie':        forms.TextInput(attrs={'class': 'form-control bg-light text-muted', 'readonly': 'readonly'}),
            'teacher_name': forms.Select(attrs={'class': 'form-select'}),
            'grade':        forms.Select(attrs={'class': 'form-select'}),
            'area':         forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_falla':   forms.Select(attrs={'class': 'form-select'}),
            'tipo_mant_impresora': forms.Select(attrs={'class': 'form-select'}),
            'estado_tinta': forms.Select(attrs={'class': 'form-select'}),
            'tipo_tinta':   forms.Select(attrs={'class': 'form-select'}),
            'tinta_negra':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tinta_magenta':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tinta_amarillo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'tinta_cyan':     forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'date':         forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status':       forms.Select(attrs={'class': 'form-select'}),
            'solucion':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones':forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import MaestroMantenimiento, GradoMantenimiento
        from inventario.models import Computadora, Impresora

        # Solo computadoras de general (excluye laboratorios: IDANALAB*, IDCFPLAB*)
        self.fields['computadora'].queryset = (
            Computadora.objects.exclude(asset_id__icontains='LAB').order_by('asset_id'))
        self.fields['computadora'].empty_label = '— Seleccionar computadora —'
        # Mostrar también el nombre del asignado para identificar mejor
        self.fields['computadora'].label_from_instance = (
            lambda o: f"{o.asset_id} – {o.modelo}" + (f" · {o.asignado_a}" if o.asignado_a else ""))

        # <--- hecho por claude code: dropdown de impresoras (asset_id — nombre · asignado)
        self.fields['impresora'].queryset = Impresora.objects.order_by('asset_id')
        self.fields['impresora'].empty_label = '— Seleccionar impresora —'
        self.fields['impresora'].label_from_instance = (
            lambda o: f"{o.asset_id} – {o.modelo}" + (f" · {o.asignado_a}" if o.asignado_a else ""))

        # Campos que dependen del tipo de equipo: no obligatorios a nivel de widget;
        # la validación real se hace en clean() según tipo_equipo.
        for f in ('computadora', 'impresora', 'model', 'serie', 'teacher_name',
                  'grade', 'area', 'tipo_falla', 'tipo_mant_impresora',
                  'estado_tinta', 'tipo_tinta'):
            self.fields[f].required = False

        self.fields['teacher_name'].widget = forms.HiddenInput()
        self.fields['grade'].widget        = forms.HiddenInput()

    def clean(self):
        # <--- hecho por claude code: validación condicional por tipo de equipo
        cleaned = super().clean()
        tipo = cleaned.get('tipo_equipo') or 'computadora'
        if tipo == 'impresora':
            if not cleaned.get('impresora'):
                self.add_error('impresora', 'Selecciona una impresora.')
            if not cleaned.get('tipo_mant_impresora'):
                self.add_error('tipo_mant_impresora', 'Selecciona el tipo de mantenimiento.')
            if not cleaned.get('estado_tinta'):
                self.add_error('estado_tinta', 'Indica el estado de la tinta.')
        else:
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona una computadora.')
        return cleaned


class FirmaMaestroForm(forms.Form):
    """Formulario público (sin login) para que el maestro firme por link."""
    firma_data = forms.CharField(widget=forms.HiddenInput, required=True)

    def clean_firma_data(self):
        data = (self.cleaned_data.get('firma_data') or '').strip()
        if not data or not data.startswith('data:image'):
            raise forms.ValidationError("Debes firmar antes de enviar.")
        return data
