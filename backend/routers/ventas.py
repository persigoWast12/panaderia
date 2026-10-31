"""Endpoints para registrar y consultar ventas."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import DetalleVenta, Empleado, Producto, Stock, Venta
from schemas import VentaIn, VentaOut
from security import require_rol

router = APIRouter(tags=["Ventas"])

CENTAVOS = Decimal("0.01")


def _subtotal(cantidad: Decimal, precio_unitario: Decimal) -> Decimal:
    """Calcula un subtotal redondeado a dos decimales."""
    return (cantidad * precio_unitario).quantize(
        CENTAVOS, rounding=ROUND_HALF_UP
    )


def _venta_out(venta: Venta) -> dict:
    """Arma la respuesta de una venta con sus renglones y subtotales."""
    items = []
    total = Decimal("0")
    for detalle in venta.detalles:
        subtotal = _subtotal(detalle.cantidad, detalle.precio_unitario)
        total += subtotal
        items.append(
            {
                "producto_id": detalle.producto_id,
                "nombre": detalle.producto.nombre,
                "cantidad": detalle.cantidad,
                "precio_unitario": detalle.precio_unitario,
                "subtotal": subtotal,
            }
        )

    return {
        "id": venta.id,
        "fecha_hora": venta.fecha_hora,
        "forma_pago": venta.forma_pago,
        "total": total,
        "items": items,
    }


@router.post("/ventas", response_model=VentaOut, status_code=201)
def crear_venta(
    datos: VentaIn,
    db: Session = Depends(get_db),
    empleado: Empleado = Depends(require_rol("cajero")),
):
    """Registra una venta, calcula el total y descuenta el stock."""
    # Agrupar renglones repetidos del mismo producto.
    cantidades: dict[int, Decimal] = {}
    for item in datos.items:
        cantidades[item.producto_id] = (
            cantidades.get(item.producto_id, Decimal("0")) + item.cantidad
        )

    ids = sorted(cantidades)

    try:
        productos = db.scalars(
            select(Producto).where(Producto.id.in_(ids))
        ).all()
        productos_por_id = {producto.id: producto for producto in productos}

        for producto_id in ids:
            producto = productos_por_id.get(producto_id)
            if producto is None:
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto {producto_id} no existe.",
                )
            if not producto.activo:
                raise HTTPException(
                    status_code=400,
                    detail=f"El producto '{producto.nombre}' está inactivo.",
                )

            cantidad = cantidades[producto_id]
            if (
                producto.unidad == "unidad"
                and cantidad != cantidad.to_integral_value()
            ):
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El producto '{producto.nombre}' se vende por unidad; "
                        "la cantidad debe ser entera."
                    ),
                )

        # Bloquear el stock en orden de producto para que dos cajas no vendan
        # el mismo último stock y para evitar deadlocks entre ventas.
        stocks = db.scalars(
            select(Stock)
            .where(Stock.producto_id.in_(ids))
            .order_by(Stock.producto_id)
            .with_for_update()
        ).all()
        stocks_por_id = {stock.producto_id: stock for stock in stocks}

        for producto_id in ids:
            producto = productos_por_id[producto_id]
            stock = stocks_por_id.get(producto_id)
            if stock is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"El producto '{producto.nombre}' no tiene stock "
                        "registrado."
                    ),
                )
            if stock.cantidad_disponible < cantidades[producto_id]:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No hay stock suficiente de '{producto.nombre}': "
                        f"disponible {stock.cantidad_disponible}, "
                        f"pedido {cantidades[producto_id]}."
                    ),
                )

        venta = Venta(
            empleado_id=empleado.id,
            fecha_hora=datetime.now(),
            forma_pago=datos.forma_pago,
            total=Decimal("0"),
        )

        total = Decimal("0")
        for producto_id in ids:
            producto = productos_por_id[producto_id]
            cantidad = cantidades[producto_id]
            subtotal = _subtotal(cantidad, producto.precio)
            total += subtotal
            venta.detalles.append(
                DetalleVenta(
                    producto_id=producto_id,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                )
            )
            stocks_por_id[producto_id].cantidad_disponible -= cantidad

        venta.total = total
        db.add(venta)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise

    db.refresh(venta)
    return _venta_out(venta)


@router.get("/ventas", response_model=list[VentaOut])
def listar_ventas(
    fecha: date | None = None,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("cajero", "encargado")),
):
    """Lista las ventas de un día (hoy por defecto), más recientes primero."""
    dia = fecha or date.today()
    ventas = db.scalars(
        select(Venta)
        .options(
            selectinload(Venta.detalles).selectinload(DetalleVenta.producto)
        )
        .where(func.date(Venta.fecha_hora) == dia)
        .order_by(Venta.fecha_hora.desc())
    ).all()

    return [_venta_out(venta) for venta in ventas]
