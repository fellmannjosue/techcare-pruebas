# core/forms.py
# <--- hecho por claude code: mixin global para dar el estilo del portal a los widgets
# de CUALQUIER formulario. Generaliza sponsors.forms.EstiloBootstrapMixin. Solo asigna
# clases CSS a los widgets; no cambia campos, validaciones ni lógica.
from django import forms


class EstiloPortalMixin:
    """Aplica form-control / form-select / form-check-input a todos los campos.

    Se heredan ANTES de forms.ModelForm/forms.Form:
        class MiForm(EstiloPortalMixin, forms.ModelForm): ...
    portal.css re-estiliza esas clases al diseño del portal, así todos los
    formularios del sistema se ven idénticos.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            w = campo.widget
            if isinstance(w, (forms.CheckboxInput, forms.CheckboxSelectMultiple)):
                clase = 'form-check-input'
            elif isinstance(w, (forms.Select, forms.SelectMultiple)):
                clase = 'form-select'
            else:
                clase = 'form-control'
            existentes = w.attrs.get('class', '')
            clases = [c for c in existentes.split() if c not in ('form-control', 'form-select')]
            if clase not in clases:
                clases.append(clase)
            w.attrs['class'] = ' '.join(clases).strip()
