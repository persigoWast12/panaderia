"""Esquemas (Pydantic) que definen lo que entra y sale de la API.

Las entradas validan tipos, límites y roles. En las salidas, el dinero y las
cantidades se exponen como `float` para que el JSON sea simple de consumir en
el frontend; internamente la base y los cálculos usan `Decimal`.
"""

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

    id: int
    nombre: str
    usuario: str
    rol: str


class EmpleadoIn(BaseModel):
    """Datos para dar de alta a un empleado."""

    nombre: str = Field(min_length=1, max_length=100)
    usuario: str = Field(min_length=3, max_length=50)
    rol: Literal["cajero", "encargado", "contador", "dueno"]
    password: str = Field(min_length=8, max_length=72)
    activo: bool = True


class EmpleadoUpdate(BaseModel):
    """Campos que el dueño puede corregir de un empleado."""

    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    usuario: str | None = Field(default=None, min_length=3, max_length=50)
    rol: Literal["cajero", "encargado", "contador", "dueno"] | None = None
    activo: bool | None = None


class EmpleadoOut(BaseModel):
    """Datos de un empleado, sin el hash de la contraseña.

    Es la única forma en que el hash puede salir de la base: nunca se incluye
    en una respuesta de la API.
    """

    id: int
    nombre: str
    usuario: str
    rol: str
    activo: bool


class PasswordIn(BaseModel):
    """Nueva contraseña que asigna el dueño."""

    password: str = Field(min_length=8, max_length=72)


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
    precio: float  # precio actual, para mostrarlo en la tabla de productos
    activo: bool
    cantidad_disponible: float
    # El frontend lo usa para bloquear el cambio de unidad si ya hay ventas.
    tiene_ventas: bool


class ItemIn(BaseModel):
    """Un renglón del carrito: producto y cantidad."""

    producto_id: int = Field(gt=0)
    cantidad: Decimal = Field(gt=0)


class VentaIn(BaseModel):
    """Datos para registrar una venta.

    El total no se acepta: lo calcula el backend a partir de los precios de la
    base. Si el cliente lo manda igual, Pydantic lo ignora.
    """

    forma_pago: Literal["efectivo", "billetera_virtual", "tarjeta"]
    items: list[ItemIn] = Field(min_length=1)


class DetalleOut(BaseModel):
    """Renglón de una venta ya registrada.

    `subtotal` no se guarda en la base: se recalcula al responder con la misma
    fórmula que usa el total de la venta.
    """

    producto_id: int
    nombre: str
    unidad: str
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
