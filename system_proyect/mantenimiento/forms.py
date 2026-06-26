from django import forms
from .models import MaintenanceRecord, TipoFalla


class MaintenanceRecordForm(forms.ModelForm):
    class Meta:
        model  = MaintenanceRecord
        fields = ['computadora', 'model', 'serie', 'teacher_name', 'grade',
                  'tipo_falla', 'date', 'status', 'solucion', 'observaciones']
        widgets = {
            'computadora':  forms.Select(attrs={'class': 'form-select'}),
            'model':        forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'serie':        forms.TextInput(attrs={'class': 'form-control bg-light text-muted', 'readonly': 'readonly'}),
            'teacher_name': forms.Select(attrs={'class': 'form-select'}),
            'grade':        forms.Select(attrs={'class': 'form-select'}),
            'tipo_falla':   forms.Select(attrs={'class': 'form-select'}),
            'date':         forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status':       forms.Select(attrs={'class': 'form-select'}),
            'solucion':     forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'observaciones':forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import MaestroMantenimiento, GradoMantenimiento
        from inventario.models import Computadora

        # Solo computadoras de general (excluye laboratorios: IDANALAB*, IDCFPLAB*)
        self.fields['computadora'].queryset = (
            Computadora.objects.exclude(asset_id__icontains='LAB').order_by('asset_id'))
        self.fields['computadora'].empty_label = '— Seleccionar computadora —'
        # Mostrar también el nombre del asignado para identificar mejor
        self.fields['computadora'].label_from_instance = (
            lambda o: f"{o.asset_id} – {o.modelo}" + (f" · {o.asignado_a}" if o.asignado_a else ""))

        self.fields['serie'].required        = False
        self.fields['model'].required        = False
        self.fields['teacher_name'].required = False
        self.fields['teacher_name'].widget   = forms.HiddenInput()
        self.fields['grade'].required        = False
        self.fields['grade'].widget          = forms.HiddenInput()


class FirmaMaestroForm(forms.Form):
    """Formulario público (sin login) para que el maestro firme por link."""
    firma_data = forms.CharField(widget=forms.HiddenInput, required=True)

    def clean_firma_data(self):
        data = (self.cleaned_data.get('firma_data') or '').strip()
        if not data or not data.startswith('data:image'):
            raise forms.ValidationError("Debes firmar antes de enviar.")
        return data
