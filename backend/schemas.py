"""Esquemas (Pydantic) que definen lo que entra y sale de la API."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LoginIn(BaseModel):
    """Datos que manda el formulario de login."""

    usuario: str
    password: str


class MeOut(BaseModel):
    """Datos públicos del empleado autenticado."""

    nombre: str
    rol: str


class ProductoIn(BaseModel):
    """Datos para crear un producto y su stock inicial."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str = Field(min_length=1, max_length=100)
    codigo_barras: str = Field(min_length=1, max_length=50)
    unidad: Literal["unidad", "kg"]
    precio: Decimal = Field(gt=0)
    proveedor_id: int | None = None
    cantidad_inicial: Decimal = Field(default=Decimal("0"), ge=0)
    activo: bool = True


class ProductoUpdate(BaseModel):
    """Campos que se pueden corregir de un producto ya creado."""

    model_config = ConfigDict(str_strip_whitespace=True)

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    codigo_barras: str | None = Field(default=None, min_length=1, max_length=50)
    unidad: Literal["unidad", "kg"] | None = None
    precio: Decimal | None = Field(default=None, gt=0)
    activo: bool | None = None


class ProductoOut(BaseModel):
    """Producto con los datos que necesita el mostrador, incluido su stock."""

    id: int
    nombre: str
    codigo_barras: str
    unidad: str
    precio: float
    proveedor_id: int | None
    activo: bool
    cantidad_disponible: float


class StockIn(BaseModel):
    """Nueva cantidad disponible para un producto."""

    cantidad_disponible: Decimal = Field(ge=0)


class StockOut(BaseModel):
    """Fila de stock con los datos del producto al que pertenece."""

    producto_id: int
    nombre: str
    codigo_barras: str
    unidad: str
    activo: bool
    cantidad_disponible: float


class ItemIn(BaseModel):
    """Un renglón del carrito: producto y cantidad."""

    producto_id: int = Field(gt=0)
    cantidad: Decimal = Field(gt=0)


class VentaIn(BaseModel):
    """Datos para registrar una venta. El total no se acepta: lo calcula el backend."""

    forma_pago: Literal["efectivo", "billetera_virtual", "tarjeta"]
    items: list[ItemIn] = Field(min_length=1)


class DetalleOut(BaseModel):
    """Renglón de una venta ya registrada."""

    producto_id: int
    nombre: str
    cantidad: float
    precio_unitario: float
    subtotal: float


class VentaOut(BaseModel):
    """Venta completa con sus renglones."""

    id: int
    fecha_hora: datetime
    forma_pago: str
    total: float
    items: list[DetalleOut]
