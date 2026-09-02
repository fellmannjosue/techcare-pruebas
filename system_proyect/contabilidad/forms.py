# <--- hecho por claude code: formularios del módulo Contabilidad (FASE 2 + 2.1).
from django import forms

from .models import (ProductoUniforme, AreaUniforme, TipoUniforme, ClaseMovimiento,
                     TipoSalida, Proveedor, CompraProveedor, TipoImpuesto, RegaliaProveedor)

_INPUT  = {'class': 'form-control'}
_SELECT = {'class': 'form-select'}


class ProductoUniformeForm(forms.ModelForm):
    class Meta:
        model = ProductoUniforme
        fields = ['nombre', 'area', 'tipo', 'talla', 'color', 'codigo',
                  'unidad', 'stock_minimo', 'precio_venta', 'tipo_impuesto_venta', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs=_INPUT),
            'area':   forms.Select(attrs=_SELECT),
            'tipo':   forms.Select(attrs=_SELECT),
            'talla':  forms.TextInput(attrs={**_INPUT, 'placeholder': 'ej. S, M, L, 8, 10…'}),
            'color':  forms.TextInput(attrs=_INPUT),
            'codigo': forms.TextInput(attrs={**_INPUT, 'placeholder': 'opcional'}),
            'unidad': forms.TextInput(attrs={**_INPUT, 'placeholder': 'ej. Unidad, Pieza'}),
            'stock_minimo': forms.NumberInput(attrs={**_INPUT, 'min': 0}),
            'precio_venta': forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'min': 0, 'placeholder': 'opcional'}),
            'tipo_impuesto_venta': forms.Select(attrs=_SELECT),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['area'].queryset = AreaUniforme.objects.filter(activo=True)
        self.fields['tipo'].queryset = TipoUniforme.objects.filter(activo=True)
        self.fields['tipo_impuesto_venta'].queryset = TipoImpuesto.objects.filter(activo=True)
        self.fields['tipo_impuesto_venta'].required = False


class MovimientoUniformeForm(forms.Form):
    """Formulario simple para registrar UN movimiento. El cálculo (importe, existencia,
    promedio) lo hace services.registrar_movimiento; aquí solo se capturan los datos."""
    producto = forms.ModelChoiceField(
        queryset=ProductoUniforme.objects.none(), widget=forms.Select(attrs={**_SELECT, 'id': 'id_producto'}))
    fecha = forms.DateField(widget=forms.DateInput(attrs={**_INPUT, 'type': 'date'}))
    clase = forms.ChoiceField(choices=ClaseMovimiento.choices,
                              widget=forms.Select(attrs={**_SELECT, 'id': 'id_clase'}))
    cantidad = forms.IntegerField(min_value=1, widget=forms.NumberInput(attrs={**_INPUT, 'min': 1}))
    costo_unitario = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=4,
        widget=forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'id': 'id_costo_unitario'}))
    # <--- FASE 2.1: motivo de salida (solo VENTA pide precio y genera ingreso)
    tipo_salida = forms.ChoiceField(
        required=False, choices=[('', '— Motivo de salida —')] + list(TipoSalida.choices),
        widget=forms.Select(attrs={**_SELECT, 'id': 'id_tipo_salida'}))
    precio_unitario = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=4,
        widget=forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'id': 'id_precio_unitario'}))
    concepto = forms.CharField(required=False, max_length=160, widget=forms.TextInput(attrs=_INPUT))
    motivo = forms.CharField(required=False, max_length=160, widget=forms.TextInput(attrs=_INPUT))
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={**_INPUT, 'rows': 2}))

    def __init__(self, *args, producto_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = (
            producto_qs if producto_qs is not None else ProductoUniforme.objects.filter(activo=True))

    def clean(self):
        cd = super().clean()
        clase = cd.get('clase')
        costo = cd.get('costo_unitario')
        if clase in (ClaseMovimiento.SALDO_INICIAL, ClaseMovimiento.ENTRADA) and costo is None:
            self.add_error('costo_unitario', 'Obligatorio en entradas y saldo inicial.')
        if clase == ClaseMovimiento.SALIDA and not cd.get('tipo_salida'):
            self.add_error('tipo_salida', 'Indica el motivo de la salida.')
        return cd


# <--- hecho por claude code: form dedicado de PRECIOS — precio POR PROVEEDOR (select) + precio de venta; ISV 15% auto
class PrecioVentaForm(forms.Form):
    proveedor = forms.ModelChoiceField(
        queryset=Proveedor.objects.filter(activo=True),
        widget=forms.Select(attrs={**_SELECT, 'id': 'id_proveedor'}),
        label='Proveedor')
    precio_proveedor = forms.DecimalField(
        min_value=0, max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'min': 0, 'id': 'id_precio_proveedor', 'placeholder': '0.00'}),
        label='Precio que puso el proveedor')
    precio_venta = forms.DecimalField(
        min_value=0, max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'min': 0, 'id': 'id_precio_venta', 'placeholder': '0.00'}),
        label='Precio de venta')


# <--- hecho por claude code: form de VENTA de uniformes (salida tipo VENTA: descuenta stock y genera ingreso)
class VentaForm(forms.Form):
    """Venta de uniformes. El descuento de stock y el ingreso los calcula
    services.registrar_movimiento (clase=SALIDA, tipo_salida=VENTA)."""
    producto = forms.ModelChoiceField(
        queryset=ProductoUniforme.objects.none(),
        widget=forms.Select(attrs={**_SELECT, 'id': 'id_producto'}))
    fecha = forms.DateField(widget=forms.DateInput(attrs={**_INPUT, 'type': 'date'}))
    cantidad = forms.IntegerField(min_value=1,
        widget=forms.NumberInput(attrs={**_INPUT, 'min': 1, 'id': 'id_cantidad'}))
    precio_unitario = forms.DecimalField(
        required=False, min_value=0, max_digits=12, decimal_places=2,
        help_text='Si lo dejas vacío, se usa el precio de venta del producto.',
        widget=forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'id': 'id_precio_unitario'}))
    cliente = forms.CharField(required=False, max_length=160,
        widget=forms.TextInput(attrs={**_INPUT, 'placeholder': 'opcional'}))
    observaciones = forms.CharField(required=False,
        widget=forms.Textarea(attrs={**_INPUT, 'rows': 2}))

    def __init__(self, *args, producto_qs=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = (
            producto_qs if producto_qs is not None
            else ProductoUniforme.objects.filter(activo=True))


class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['nombre', 'nombre_comercial', 'rtn', 'contacto', 'telefono', 'correo',
                  'direccion', 'color', 'activo', 'observaciones']
        widgets = {
            'nombre': forms.TextInput(attrs=_INPUT),
            'nombre_comercial': forms.TextInput(attrs=_INPUT),
            'rtn': forms.TextInput(attrs=_INPUT),
            'contacto': forms.TextInput(attrs=_INPUT),
            'telefono': forms.TextInput(attrs=_INPUT),
            'correo': forms.EmailInput(attrs=_INPUT),
            'direccion': forms.TextInput(attrs=_INPUT),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'activo': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'observaciones': forms.Textarea(attrs={**_INPUT, 'rows': 2}),
        }


# <--- hecho por claude code: form de REGALÍAS (informe aparte, no se contabiliza)
class RegaliaForm(forms.ModelForm):
    class Meta:
        model = RegaliaProveedor
        fields = ['proveedor', 'fecha', 'descripcion', 'cantidad', 'valor_estimado', 'documento', 'observaciones']
        widgets = {
            'proveedor':   forms.Select(attrs=_SELECT),
            'fecha':       forms.DateInput(attrs={**_INPUT, 'type': 'date'}),
            'descripcion': forms.TextInput(attrs={**_INPUT, 'placeholder': 'ej. 10 polos de regalo, material POP…'}),
            'cantidad':    forms.NumberInput(attrs={**_INPUT, 'min': 1}),
            'valor_estimado': forms.NumberInput(attrs={**_INPUT, 'step': '0.01', 'min': 0, 'placeholder': 'opcional'}),
            'documento':   forms.TextInput(attrs={**_INPUT, 'placeholder': 'opcional'}),
            'observaciones': forms.Textarea(attrs={**_INPUT, 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['proveedor'].queryset = Proveedor.objects.filter(activo=True)


class CompraHeaderForm(forms.Form):
    """Encabezado de la compra; las líneas se envían como arrays y se procesan en la vista."""
    proveedor = forms.ModelChoiceField(queryset=Proveedor.objects.filter(activo=True),
                                        widget=forms.Select(attrs=_SELECT))
    fecha = forms.DateField(widget=forms.DateInput(attrs={**_INPUT, 'type': 'date'}))
    documento = forms.CharField(required=False, max_length=60, widget=forms.TextInput(attrs=_INPUT))
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={**_INPUT, 'rows': 2}))
