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

        self.fields['computadora'].queryset = Computadora.objects.all().order_by('asset_id')
        self.fields['computadora'].empty_label = '— Seleccionar computadora —'

        maestros = list(MaestroMantenimiento.objects.values_list('nombre', flat=True))
        self.fields['teacher_name'].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[('', '— Seleccionar maestro —')] + [(n, n) for n in maestros]
        )
        grados = list(GradoMantenimiento.objects.values_list('nombre', flat=True))
        self.fields['grade'].widget = forms.Select(
            attrs={'class': 'form-select'},
            choices=[('', '— Seleccionar grado —')] + [(n, n) for n in grados]
        )
        self.fields['serie'].required = False
        self.fields['model'].required = False
