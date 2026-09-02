# <--- hecho por claude code: DTO de solo lectura. Conversión estricta de tipos SQL Server
# → Python. NUNCA `float` para cantidades/costos/precios/existencias (siempre Decimal).
import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


def _dec(v):
    if v is None:
        return None
    if isinstance(v, Decimal):
        return v
    # str() preserva la precisión exacta (evita el binario de float).
    return Decimal(str(v))


def _int(v):
    return None if v is None else int(v)


def _bool(v):
    return None if v is None else bool(v)


def _str(v):
    return None if v is None else str(v)


def _bytes(v):
    if v is None:
        return None
    return bytes(v)


def _fecha(v):
    return v if (v is None or isinstance(v, datetime.date)) else v


def _dt(v):
    return v if (v is None or isinstance(v, datetime.datetime)) else v


@dataclass(frozen=True)
class Categoria:
    categoria_id: int
    codigo: str
    nombre: str
    activo: Optional[bool]
    rv: Optional[bytes]

    @classmethod
    def from_dict(cls, d):
        return cls(_int(d.get('CategoriaID')), _str(d.get('Codigo')), _str(d.get('Nombre')),
                   _bool(d.get('Activo')), _bytes(d.get('RV')))


@dataclass(frozen=True)
class Unidad:
    unidad_medida_id: int
    codigo: str
    nombre: str
    decimales_cantidad: Optional[int]
    activo: Optional[bool]
    rv: Optional[bytes]

    @classmethod
    def from_dict(cls, d):
        return cls(_int(d.get('UnidadMedidaID')), _str(d.get('Codigo')), _str(d.get('Nombre')),
                   _int(d.get('DecimalesCantidad')), _bool(d.get('Activo')), _bytes(d.get('RV')))


@dataclass(frozen=True)
class Almacen:
    almacen_id: int
    codigo: str
    nombre: str
    es_predeterminado: Optional[bool]
    activo: Optional[bool]
    rv: Optional[bytes]

    @classmethod
    def from_dict(cls, d):
        return cls(_int(d.get('AlmacenID')), _str(d.get('Codigo')), _str(d.get('Nombre')),
                   _bool(d.get('EsPredeterminado')), _bool(d.get('Activo')), _bytes(d.get('RV')))


@dataclass(frozen=True)
class Articulo:
    articulo_id: int
    codigo: str
    descripcion: str
    categoria_id: Optional[int]
    unidad_medida_id: Optional[int]
    activo: Optional[bool]
    observacion: Optional[str]
    costo_promedio_actual: Optional[Decimal]
    rv: Optional[bytes]

    @classmethod
    def from_dict(cls, d):
        return cls(_int(d.get('ArticuloID')), _str(d.get('Codigo')), _str(d.get('Descripcion')),
                   _int(d.get('CategoriaID')), _int(d.get('UnidadMedidaID')), _bool(d.get('Activo')),
                   _str(d.get('Observacion')), _dec(d.get('CostoPromedioActual')), _bytes(d.get('RV')))


@dataclass(frozen=True)
class ExistenciaArticulo:
    articulo_id: int
    codigo: str
    descripcion: str
    almacen_id: Optional[int]
    codigo_almacen: Optional[str]
    cantidad_actual: Optional[Decimal]
    ultimo_movimiento_id: Optional[int]
    costo_promedio_actual: Optional[Decimal]

    @classmethod
    def from_dict(cls, d):
        return cls(_int(d.get('ArticuloID')), _str(d.get('Codigo')), _str(d.get('Descripcion')),
                   _int(d.get('AlmacenID')), _str(d.get('CodigoAlmacen')), _dec(d.get('CantidadActual')),
                   _int(d.get('UltimoMovimientoID')), _dec(d.get('CostoPromedioActual')))


@dataclass(frozen=True)
class Proveedor:
    proveedor_id: int
    compania: Optional[str]
    persona_contacto: Optional[str]
    rtn: Optional[str]
    telefono: Optional[str]
    email: Optional[str]
    direccion: Optional[str]
    pais: Optional[str]

    @classmethod
    def from_dict(cls, d):
        return cls(_int(d.get('ProveedorID')), _str(d.get('Compania')), _str(d.get('PersonaContacto')),
                   _str(d.get('RTN')), _str(d.get('Telefono')), _str(d.get('EMail')),
                   _str(d.get('Direccion')), _str(d.get('Pais')))


@dataclass(frozen=True)
class MovimientoKardex:
    movimiento_id: int
    tipo_movimiento: Optional[str]
    estado: Optional[str]
    fecha_movimiento: Optional[datetime.date]
    fecha_aplicacion: Optional[datetime.datetime]
    origen_sistema: Optional[str]
    origen_tipo: Optional[str]
    origen_clave: Optional[str]
    clave_idempotencia: Optional[str]
    movimiento_original_id: Optional[int]
    linea_no: Optional[int]
    articulo_id: Optional[int]
    origen_detalle_clave: Optional[str]
    cantidad: Optional[Decimal]
    costo_unitario: Optional[Decimal]
    costo_total: Optional[Decimal]
    existencia_antes: Optional[Decimal]
    existencia_despues: Optional[Decimal]
    cambio_cantidad: Optional[Decimal]
    costo_promedio_antes: Optional[Decimal]
    costo_promedio_despues: Optional[Decimal]

    @classmethod
    def from_dict(cls, d):
        return cls(
            _int(d.get('MovimientoID')), _str(d.get('TipoMovimiento')), _str(d.get('Estado')),
            _fecha(d.get('FechaMovimiento')), _dt(d.get('FechaAplicacion')),
            _str(d.get('OrigenSistema')), _str(d.get('OrigenTipo')), _str(d.get('OrigenClave')),
            _str(d.get('ClaveIdempotencia')), _int(d.get('MovimientoOriginalID')),
            _int(d.get('LineaNo')), _int(d.get('ArticuloID')), _str(d.get('OrigenDetalleClave')),
            _dec(d.get('Cantidad')), _dec(d.get('CostoUnitario')), _dec(d.get('CostoTotal')),
            _dec(d.get('ExistenciaAntes')), _dec(d.get('ExistenciaDespues')),
            _dec(d.get('CambioCantidad')), _dec(d.get('CostoPromedioAntes')),
            _dec(d.get('CostoPromedioDespues')))
