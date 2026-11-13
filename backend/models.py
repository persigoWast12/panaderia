"""Modelos (tablas) del sistema de la panadería."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Empleado(Base):
    """Persona que usa el sistema: cajero, encargado, contador o dueño."""

    __tablename__ = "empleado"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    # 'cajero', 'encargado', 'contador' o 'dueno'. Se usa String + CHECK para no
    # crear un ENUM nativo.
    rol: Mapped[str] = mapped_column(String(20))
    # Se guarda siempre en minúsculas (se normaliza en el login y en el seed).
    usuario: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    ventas: Mapped[list[Venta]] = relationship(back_populates="empleado")
    sesiones: Mapped[list[Sesion]] = relationship(back_populates="empleado")

    __table_args__ = (
        CheckConstraint(
            "rol IN ('cajero', 'encargado', 'contador', 'dueno')",
            name="ck_empleado_rol",
        ),
    )


class Proveedor(Base):
    """Proveedor de productos. Un producto puede no tener proveedor."""

    __tablename__ = "proveedor"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    contacto: Mapped[str | None] = mapped_column(String(100), nullable=True)

    productos: Mapped[list[Producto]] = relationship(back_populates="proveedor")


class Producto(Base):
    """Producto vendible. Se desactiva en vez de borrarse para conservar ventas."""

    __tablename__ = "producto"

    id: Mapped[int] = mapped_column(primary_key=True)
    proveedor_id: Mapped[int | None] = mapped_column(
        ForeignKey("proveedor.id"), nullable=True
    )
    nombre: Mapped[str] = mapped_column(String(100))
    codigo_barras: Mapped[str] = mapped_column(String(50), unique=True)
    # 'unidad' (se vende de a uno) o 'kg' (se pesa).
    unidad: Mapped[str] = mapped_column(String(10))
    precio: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)

    proveedor: Mapped[Proveedor | None] = relationship(back_populates="productos")
    # Relación uno a uno: cada producto tiene exactamente un registro de stock.
    stock: Mapped[Stock] = relationship(
        back_populates="producto", uselist=False, cascade="all, delete-orphan"
    )
    detalles: Mapped[list[DetalleVenta]] = relationship(back_populates="producto")

    __table_args__ = (
        CheckConstraint("unidad IN ('unidad', 'kg')", name="ck_producto_unidad"),
        CheckConstraint("precio > 0", name="ck_producto_precio"),
        CheckConstraint(
            "precio <= 1000000.00", name="ck_producto_precio_max"
        ),
    )


class Stock(Base):
    """Cantidad disponible de un producto (relación uno a uno con Producto)."""

    __tablename__ = "stock"

    id: Mapped[int] = mapped_column(primary_key=True)
    producto_id: Mapped[int] = mapped_column(
        ForeignKey("producto.id"), unique=True
    )
    cantidad_disponible: Mapped[Decimal] = mapped_column(Numeric(10, 3))

    producto: Mapped[Producto] = relationship(back_populates="stock")

    __table_args__ = (
        CheckConstraint(
            "cantidad_disponible >= 0", name="ck_stock_cantidad"
        ),
        CheckConstraint(
            "cantidad_disponible <= 100000.000",
            name="ck_stock_cantidad_max",
        ),
    )


class Venta(Base):
    """Cabecera de una venta: empleado, fecha, forma de pago y total."""

    __tablename__ = "venta"

    id: Mapped[int] = mapped_column(primary_key=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    # Hora local del servidor, sin zona horaria. Simplifica "ventas del día".
    fecha_hora: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    forma_pago: Mapped[str] = mapped_column(String(20))
    total: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    empleado: Mapped[Empleado] = relationship(back_populates="ventas")
    detalles: Mapped[list[DetalleVenta]] = relationship(
        back_populates="venta", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "forma_pago IN ('efectivo', 'billetera_virtual', 'tarjeta')",
            name="ck_venta_forma_pago",
        ),
        CheckConstraint("total >= 0", name="ck_venta_total"),
        CheckConstraint("total <= 10000000.00", name="ck_venta_total_max"),
        Index("ix_venta_fecha_hora", "fecha_hora"),
    )


class DetalleVenta(Base):
    """Renglón de una venta; guarda la cantidad y el precio del momento."""

    __tablename__ = "detalle_venta"

    id: Mapped[int] = mapped_column(primary_key=True)
    venta_id: Mapped[int] = mapped_column(ForeignKey("venta.id"))
    producto_id: Mapped[int] = mapped_column(ForeignKey("producto.id"))
    cantidad: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    # Copia del precio del producto al momento de la venta.
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    venta: Mapped[Venta] = relationship(back_populates="detalles")
    producto: Mapped[Producto] = relationship(back_populates="detalles")

    __table_args__ = (
        CheckConstraint("cantidad > 0", name="ck_detalle_cantidad"),
        CheckConstraint(
            "cantidad <= 10000.000", name="ck_detalle_cantidad_max"
        ),
        Index("ix_detalle_venta_venta_id", "venta_id"),
    )


class Sesion(Base):
    """Sesión abierta de un empleado. Guarda solo el hash del token."""

    __tablename__ = "sesion"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Hash SHA-256 del token; el token en claro nunca se guarda.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    empleado_id: Mapped[int] = mapped_column(ForeignKey("empleado.id"))
    creada: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    vence: Mapped[datetime] = mapped_column(DateTime)

    empleado: Mapped[Empleado] = relationship(back_populates="sesiones")

    __table_args__ = (Index("ix_sesion_vence", "vence"),)

