# <--- hecho por claude code: Formularios Salidas Baño
from django import forms
from django.contrib.auth import get_user_model
from .models import MaestroClase

User = get_user_model()


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

    def __init__(self, *args, grado_choices=None, area_choices=None, **kwargs):
        """
        grado_choices: dict agrupado {'Colegio': ['1ero','2do','3ero'], 'Bachillerato': ['1ero','2do']}
        area_choices:  limita el desplegable de Área a las del ámbito actual
        """
        instance = kwargs.get('instance')
        super().__init__(*args, **kwargs)

        # <--- hecho por claude code: el coordinador de un ámbito solo elige SUS áreas
        if area_choices:
            self.fields['area'].choices = area_choices

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
