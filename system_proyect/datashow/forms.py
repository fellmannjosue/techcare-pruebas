# datashow/forms.py
# <--- hecho por claude code (02-nov-2026): formulario de solicitud de reserva.
from django import forms
from django.utils import timezone

from .models import ReservaDataShow
from .services import reservas_en_conflicto, datashows_para_seleccionar


class ReservaForm(forms.ModelForm):
    class Meta:
        model = ReservaDataShow
        fields = ['datashow', 'fecha', 'hora_inicio', 'hora_fin', 'lugar', 'motivo']
        widgets = {
            'datashow':    forms.Select(attrs={'class': 'form-select'}),
            'fecha':       forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora_inicio': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'hora_fin':    forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'lugar':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Aula 3, Auditorio, Sala de maestros…'}),
            'motivo':      forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Para qué se usará'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['datashow'].queryset = datashows_para_seleccionar()
        self.fields['datashow'].label_from_instance = (
            lambda o: f'{o.asset_id} — {o.nombre or o.modelo}'.strip(' —')
        )
        self.fields['motivo'].required = False

    def clean(self):
        cleaned = super().clean()
        fecha = cleaned.get('fecha')
        hi = cleaned.get('hora_inicio')
        hf = cleaned.get('hora_fin')
        datashow = cleaned.get('datashow')

        if fecha and fecha < timezone.now().date():
            self.add_error('fecha', 'No se puede reservar en una fecha que ya pasó.')

        if hi and hf and hf <= hi:
            self.add_error('hora_fin', 'La hora de fin debe ser mayor que la de inicio.')

        if datashow and fecha and hi and hf and hf > hi:
            conflicto = reservas_en_conflicto(
                datashow.id, fecha, hi, hf,
                excluir_id=self.instance.pk if self.instance.pk else None
            ).first()
            if conflicto:
                self.add_error('datashow', (
                    f'Ese DataShow ya está reservado el {fecha:%d/%m/%Y} de '
                    f'{conflicto.rango_horario} ({conflicto.get_estado_display()}). '
                    'Elige otro equipo u otra franja.'
                ))
        return cleaned
