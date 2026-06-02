# <--- hecho por claude code: Formularios Salidas Baño
from django import forms
from django.contrib.auth import get_user_model
from .models import PeriodoEscolar, MaestroClase

User = get_user_model()


class PeriodoEscolarForm(forms.ModelForm):
    class Meta:
        model  = PeriodoEscolar
        fields = ['nombre', 'parcial', 'anio', 'area', 'fecha_inicio', 'fecha_fin', 'activo']
        widgets = {
            'nombre':       forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Parcial 1 2026'}),
            'parcial':      forms.Select(choices=[(i, f'Parcial {i}') for i in range(1, 5)],
                                         attrs={'class': 'form-select'}),
            'anio':         forms.NumberInput(attrs={'class': 'form-control', 'min': 2020, 'max': 2099}),
            'area':         forms.Select(attrs={'class': 'form-select'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin':    forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'activo':       forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MaestroClaseForm(forms.ModelForm):
    # Declarado a nivel de clase para ser MultipleChoiceField (no CharField)
    grado = forms.MultipleChoiceField(
        choices=[],
        widget=forms.SelectMultiple(attrs={
            'class': 'form-select',
            'size':  '6',
            'title': 'Mantén Ctrl (o Cmd) para seleccionar varios',
        }),
        required=True,
        label='Grado',
    )

    class Meta:
        model  = MaestroClase
        fields = ['maestro', 'clase', 'grado', 'area']
        widgets = {
            'maestro': forms.Select(attrs={'class': 'form-select'}),
            'clase':   forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Matemáticas'}),
            'area':    forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, grado_choices=None, **kwargs):
        """
        grado_choices: dict agrupado {'Colegio': ['1ero','2do','3ero'], 'Bachillerato': ['1ero','2do']}
        """
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        # Solo usuarios activos, ordenados por nombre
        self.fields['maestro'].queryset = (
            User.objects.filter(is_active=True)
            .order_by('first_name', 'last_name', 'username')
        )
        self.fields['maestro'].label_from_instance = lambda u: (
            u.get_full_name() or u.username
        )

        # Construir opciones: "Todos" primero, luego optgroups por área
        # grados_list puede ser lista de strings o de tuplas (value, label)
        choices = [('todos', 'Todos los grados')]
        if isinstance(grado_choices, dict):
            for area_label, grados_list in grado_choices.items():
                opts = [(g[0], g[1]) if isinstance(g, tuple) else (g, g)
                        for g in grados_list]
                choices.append((area_label, opts))
        elif grado_choices:
            choices += [(g[0], g[1]) if isinstance(g, tuple) else (g, g)
                        for g in grado_choices]
        self.fields['grado'].choices = choices

        # Pre-poblar para edición: "1ero,2do" → ["1ero", "2do"]
        if instance and instance.pk and instance.grado and not args:
            self.initial['grado'] = [g.strip() for g in instance.grado.split(',')]

    def clean_grado(self):
        """Convierte lista seleccionada → string separado por comas para el CharField."""
        values = self.cleaned_data.get('grado', [])
        return ','.join(values)
