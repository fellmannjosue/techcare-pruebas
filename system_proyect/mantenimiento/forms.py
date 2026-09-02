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
                  # <--- hecho por claude code: campos del Control de equipo
                  'eval_trabajo', 'eval_fallas', 'eval_fallas_detalle', 'obs_auditora', 'obs_tecnico', 'estado_equipo',
                  'insp_limpio', 'insp_ordenado', 'insp_cables', 'insp_alimentos',
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
            'eval_trabajo':        forms.Select(attrs={'class': 'form-select'}),
            'eval_fallas':         forms.Select(attrs={'class': 'form-select'}),
            'eval_fallas_detalle': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Describe las fallas que ha presentado…'}),
            'obs_auditora':        forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'obs_tecnico':         forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
            'estado_equipo':       forms.Select(attrs={'class': 'form-select'}),
            'insp_limpio':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'insp_ordenado':  forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'insp_cables':    forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'insp_alimentos': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
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
                  'estado_tinta', 'tipo_tinta',
                  'eval_trabajo', 'eval_fallas', 'eval_fallas_detalle', 'obs_auditora', 'obs_tecnico',
                  'estado_equipo', 'status'):
            self.fields[f].required = False
        self.fields['estado_equipo'].choices = [('', '— Seleccionar —')] + list(MaintenanceRecord.ESTADO_EQUIPO_CHOICES)
        # Los selects de evaluación arrancan sin opción elegida
        self.fields['eval_trabajo'].choices = [('', '— Seleccionar —')] + list(MaintenanceRecord.EVAL_TRABAJO_CHOICES)
        self.fields['eval_fallas'].choices  = [('', '— Seleccionar —')] + list(MaintenanceRecord.EVAL_FALLAS_CHOICES)

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
        elif tipo == 'control':
            # <--- hecho por claude code: el control se hace sobre la computadora del maestro
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona la computadora del maestro.')
            if not cleaned.get('eval_trabajo'):
                self.add_error('eval_trabajo', 'Responde cómo ha trabajado el equipo.')
            if not cleaned.get('eval_fallas'):
                self.add_error('eval_fallas', 'Indica si el equipo ha presentado fallas.')
            if not cleaned.get('estado_equipo'):
                self.add_error('estado_equipo', 'Indica el estado del equipo.')
            # El control queda registrado como trámite completado (el "estado" real es el del equipo)
            cleaned['status'] = 'Completado'
        elif tipo == 'inspeccion':
            # <--- hecho por claude code: la inspección es del equipo del maestro; queda completada al registrarse
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona la computadora del maestro.')
            cleaned['status'] = 'Completado'
        else:
            if not cleaned.get('computadora'):
                self.add_error('computadora', 'Selecciona una computadora.')
            if not cleaned.get('status'):
                self.add_error('status', 'Selecciona el estado.')
        return cleaned


class FirmaMaestroForm(forms.Form):
    """Formulario público (sin login) para que el maestro firme por link."""
    firma_data = forms.CharField(widget=forms.HiddenInput, required=True)

    def clean_firma_data(self):
        data = (self.cleaned_data.get('firma_data') or '').strip()
        if not data or not data.startswith('data:image'):
            raise forms.ValidationError("Debes firmar antes de enviar.")
        return data
