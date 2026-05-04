# inventario/forms.py

from django import forms
from .models import (
    InventoryItem,
    Computadora,
    Televisor,
    Impresora,
    Router,
    DataShow,
    Monitor,
    ModeloTelevisor,
    GradoTelevisor,
    AreaTelevisor,
    ModeloComputadora,
    SerieComputadora,
    AsignadoAComputadora,
    AreaComputadora,
    GradoComputadora,
)

# Form para crear o actualizar un ítem de inventario genérico
class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = ['category', 'details']
        widgets = {
            # Selección de categoría (Medicamento, Equipo, etc.)
            'category': forms.Select(attrs={'class': 'form-select'}),
            # Detalles o descripción del ítem
            'details':  forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


# Formulario para computadoras
# asset_id e ip se asignan automáticamente en la vista al crear.
# ip es editable manualmente en el modal de edición (campo manual fuera del form).
class ComputadoraForm(forms.ModelForm):
    modelo     = forms.ChoiceField(label="Modelo",      choices=[], widget=forms.Select(attrs={'class': 'form-select'}))
    asignado_a = forms.ChoiceField(label="Asignado a",  choices=[], widget=forms.Select(attrs={'class': 'form-select'}))
    area       = forms.ChoiceField(label="Área",        choices=[], widget=forms.Select(attrs={'class': 'form-select'}))
    grado      = forms.ChoiceField(label="Grado",       choices=[], widget=forms.Select(attrs={'class': 'form-select'}))
    category   = forms.ChoiceField(label="Categoría",   choices=[], required=False, widget=forms.Select(attrs={'class': 'form-select'}))

    class Meta:
        model  = Computadora
        fields = ['modelo', 'asignado_a', 'area', 'grado', 'fecha_instalado', 'observaciones', 'category']
        widgets = {
            'fecha_instalado': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'observaciones':   forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modelo'].choices     = [('', '— Modelo —')]     + [(m.nombre, m.nombre) for m in ModeloComputadora.objects.all()]
        self.fields['asignado_a'].choices = [('', '— Asignado a —')] + [(a.nombre, a.nombre) for a in AsignadoAComputadora.objects.all()]
        self.fields['area'].choices       = [('', '— Área —')]       + [(a.nombre, a.nombre) for a in AreaComputadora.objects.all()]
        self.fields['grado'].choices      = [('', '— Grado —')]      + [(g.nombre, g.nombre) for g in GradoComputadora.objects.all()]
        self.fields['category'].choices   = [('', '— Categoría —')]  + list(InventoryItem.CATEGORY_CHOICES)
        if self.instance and self.instance.pk:
            self.fields['modelo'].initial     = self.instance.modelo
            self.fields['asignado_a'].initial = self.instance.asignado_a
            self.fields['area'].initial       = self.instance.area
            self.fields['grado'].initial      = self.instance.grado
            self.fields['category'].initial   = self.instance.category


# Formulario para televisores
# asset_id, serie e ip se generan/fijan automáticamente en la vista.
class TelevisorForm(forms.ModelForm):
    modelo = forms.ChoiceField(
        label="Modelo",
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    grado = forms.ChoiceField(
        label="Grado",
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    area = forms.ChoiceField(
        label="Área",
        choices=[],
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model  = Televisor
        fields = ['modelo', 'grado', 'area', 'observaciones']
        widgets = {
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['modelo'].choices = [('', '— Seleccione modelo —')] + [
            (m.nombre, m.nombre) for m in ModeloTelevisor.objects.all()
        ]
        self.fields['grado'].choices = [('', '— Seleccione grado —')] + [
            (g.nombre, g.nombre) for g in GradoTelevisor.objects.all()
        ]
        self.fields['area'].choices = [('', '— Seleccione área —')] + [
            (a.nombre, a.nombre) for a in AreaTelevisor.objects.all()
        ]
        # Si es instancia existente, preseleccionar el valor actual
        if self.instance and self.instance.pk:
            self.fields['modelo'].initial = self.instance.modelo
            self.fields['grado'].initial  = self.instance.grado
            self.fields['area'].initial   = self.instance.area


# Formulario para impresoras
class ImpresoraForm(forms.ModelForm):
    class Meta:
        model = Impresora
        fields = [
            'asset_id',           # ID de la impresora
            'nombre',             # Nombre descriptivo
            'modelo',             # Modelo de impresora
            'serie',              # Serie del dispositivo
            'asignado_a',         # Responsable o ubicación
            'nivel_tinta',        # Nivel de tinta/restante
            'ultima_vez_llenado', # Fecha del último rellenado de tinta
            'cantidad_impresiones',# Total de impresiones realizadas
            'a_color',            # Booleano: imprime a color
            'observaciones',      # Observaciones varias
        ]
        widgets = {
            'asset_id':            forms.TextInput(attrs={'class': 'form-control'}),
            'nombre':              forms.TextInput(attrs={'class': 'form-control'}),
            'modelo':              forms.TextInput(attrs={'class': 'form-control'}),
            'serie':               forms.TextInput(attrs={'class': 'form-control'}),
            'asignado_a':          forms.TextInput(attrs={'class': 'form-control'}),
            'nivel_tinta':         forms.TextInput(attrs={'class': 'form-control'}),
            'ultima_vez_llenado':  forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'cantidad_impresiones':forms.NumberInput(attrs={'class': 'form-control'}),
            'a_color':             forms.CheckboxInput(),
            'observaciones':       forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# Formulario para routers
class RouterForm(forms.ModelForm):
    class Meta:
        model = Router
        fields = [
            'asset_id',     # ID del router
            'modelo',       # Modelo
            'serie',        # Serie
            'nombre_router',# Nombre de red (SSID)
            'clave_router', # Contraseña
            'ip_asignada',  # IP WAN
            'ip_uso',       # IP LAN
            'ubicado',      # Ubicación física
            'observaciones',# Observaciones
        ]
        widgets = {
            'asset_id':      forms.TextInput(attrs={'class': 'form-control'}),
            'modelo':        forms.TextInput(attrs={'class': 'form-control'}),
            'serie':         forms.TextInput(attrs={'class': 'form-control'}),
            'nombre_router': forms.TextInput(attrs={'class': 'form-control'}),
            'clave_router':  forms.TextInput(attrs={'class': 'form-control'}),
            'ip_asignada':   forms.TextInput(attrs={'class': 'form-control'}),
            'ip_uso':        forms.TextInput(attrs={'class': 'form-control'}),
            'ubicado':       forms.TextInput(attrs={'class': 'form-control'}),
            'observaciones': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# Formulario para DataShows
class DataShowForm(forms.ModelForm):
    class Meta:
        model = DataShow
        fields = [
            'asset_id',        # ID único
            'nombre',          # Nombre descriptivo
            'modelo',          # Modelo
            'serie',           # Serie
            'estado',          # Estado de funcionamiento
            'cable_corriente', # Incluye cable de corriente
            'hdmi',            # Incluye cable HDMI
            'vga',             # Incluye cable VGA
            'extension',       # Incluye alargador
            'observaciones',   # Observaciones adicionales
        ]
        widgets = {
            'asset_id':        forms.TextInput(attrs={'class': 'form-control'}),
            'nombre':          forms.TextInput(attrs={'class': 'form-control'}),
            'modelo':          forms.TextInput(attrs={'class': 'form-control'}),
            'serie':           forms.TextInput(attrs={'class': 'form-control'}),
            'estado':          forms.TextInput(attrs={'class': 'form-control'}),
            'cable_corriente': forms.CheckboxInput(),
            'hdmi':            forms.CheckboxInput(),
            'vga':             forms.CheckboxInput(),
            'extension':       forms.CheckboxInput(),
            'observaciones':   forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


# Form para actualizar categoría desde el panel de lista
class CategoryUpdateForm(forms.Form):
    item_type = forms.ChoiceField(
        choices=[
            ('Computadora', 'Computadora'),
            ('Televisor',   'Televisor'),
            ('Impresora',   'Impresora'),
            ('Router',      'Router'),
            ('DataShow',    'DataShow'),
        ],
        widget=forms.HiddenInput  # Se envía en oculto, no se muestra al usuario
    )
    item_id = forms.IntegerField(widget=forms.HiddenInput)  # ID del objeto a actualizar
    categoria = forms.ChoiceField(
        label='Categoría',
        choices=InventoryItem.CATEGORY_CHOICES,  # Categorías definidas en el modelo
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'})
    )

    def save(self):
        """
        Guarda la nueva categoría en el objeto correspondiente.
        """
        tipo = self.cleaned_data['item_type']
        pk   = self.cleaned_data['item_id']
        cat  = self.cleaned_data['categoria']
        modelo_map = {
            'Computadora': Computadora,
            'Televisor':   Televisor,
            'Impresora':   Impresora,
            'Router':      Router,
            'DataShow':    DataShow,
        }
        obj = modelo_map[tipo].objects.get(pk=pk)
        obj.category = cat
        obj.save()


# -------------------------------------------------------------------
# Formulario de filtrado para la lista de Computadoras
# -------------------------------------------------------------------
class ComputadoraFilterForm(forms.Form):
    asset_id = forms.CharField(
        required=False,
        label='Asset ID',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por Asset ID...'
        })
    )
    modelo = forms.CharField(
        required=False,
        label='Modelo',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por modelo...'
        })
    )
    serie = forms.CharField(
        required=False,
        label='Serie',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por serie...'
        })
    )
    ip = forms.CharField(
        required=False,
        label='IP',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por IP...'
        })
    )
    asignado_a = forms.CharField(
        required=False,
        label='Asignado a',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por usuario...'
        })
    )
    area = forms.CharField(
        required=False,
        label='Área',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por área...'
        })
    )
    grado = forms.CharField(
        required=False,
        label='Grado',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filtrar por grado...'
        })
    )
    fecha_instalado = forms.DateField(
        required=False,
        label='Fecha instalación',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

class MonitorForm(forms.ModelForm):
    class Meta:
        model = Monitor
        fields = [
            "asset_id", "modelo", "serie",
            "ubicacion_tipo",  # dropdown nuevo
            "laboratorio", "asignado_a",
            "observaciones", "category"
        ]

        widgets = {
            "asset_id": forms.TextInput(attrs={"class": "form-control"}),
            "modelo": forms.TextInput(attrs={"class": "form-control"}),
            "serie": forms.TextInput(attrs={"class": "form-control"}),

            "ubicacion_tipo": forms.Select(attrs={"class": "form-select"}),

            "laboratorio": forms.TextInput(attrs={"class": "form-control"}),
            "asignado_a": forms.TextInput(attrs={"class": "form-control"}),

            "observaciones": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "category": forms.Select(attrs={"class": "form-select"}),
        }
