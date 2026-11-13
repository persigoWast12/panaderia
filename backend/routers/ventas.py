"""Endpoints para registrar y consultar ventas."""

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import DetalleVenta, Empleado, Producto, Stock, Venta
from schemas import TOTAL_MAX, VentaIn, VentaOut
from security import require_rol

router = APIRouter(tags=["Ventas"])

CENTAVOS = Decimal("0.01")


def _subtotal(cantidad: Decimal, precio_unitario: Decimal) -> Decimal:
    """Calcula un subtotal redondeado a dos decimales.

    Se usa la misma función al guardar el total de la venta y al reconstruir
    la respuesta, para que el total coincida siempre con la suma de renglones.
    """
    return (cantidad * precio_unitario).quantize(
        CENTAVOS, rounding=ROUND_HALF_UP
    )


def _venta_out(venta: Venta) -> dict:
    """Arma la respuesta de una venta con sus renglones y subtotales.

    El subtotal no es una columna: se recalcula con `_subtotal`, y el total se
    obtiene sumando esos subtotales.
    """
    items = []
    total = Decimal("0")
    for detalle in venta.detalles:
        subtotal = _subtotal(detalle.cantidad, detalle.precio_unitario)
        total += subtotal
        items.append(
            {
                "producto_id": detalle.producto_id,
                "nombre": detalle.nombre_producto,
                "unidad": detalle.producto.unidad,
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
    """Registra una venta, calcula el total y descuenta el stock.

    Todo ocurre en una sola transacción:
    1. agrupa renglones repetidos;
    2. valida productos, estado y cantidades;
    3. bloquea las filas de stock en orden de id;
    4. verifica stock, crea la venta y descuenta;
    5. hace commit; ante cualquier error hace rollback y no deja nada a medias.
    """
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
        # el mismo último stock y para evitar deadlocks entre ventas. El orden
        # de los ids es importante: todas las transacciones piden las filas en
        # el mismo orden.
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

        # Calcular el total antes de escribir nada.
        total = Decimal("0")
        for producto_id in ids:
            producto = productos_por_id[producto_id]
            cantidad = cantidades[producto_id]
            total += _subtotal(cantidad, producto.precio)

        if total > TOTAL_MAX:
            raise HTTPException(
                status_code=400,
                detail="El total de la venta supera el máximo permitido.",
            )

        venta = Venta(
            empleado_id=empleado.id,
            fecha_hora=datetime.now(),
            forma_pago=datos.forma_pago,
            total=total,
        )

        # Se copia el precio actual a cada renglón: si mañana cambia el
        # precio del producto, la venta vieja conserva el valor original.
        for producto_id in ids:
            producto = productos_por_id[producto_id]
            cantidad = cantidades[producto_id]
            venta.detalles.append(
                DetalleVenta(
                    producto_id=producto_id,
                    nombre_producto=producto.nombre,
                    cantidad=cantidad,
                    precio_unitario=producto.precio,
                )
            )
            stocks_por_id[producto_id].cantidad_disponible -= cantidad

        db.add(venta)
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail="No se pudo registrar la venta."
        ) from None
    except Exception:
        db.rollback()
        raise

    db.refresh(venta)
    return _venta_out(venta)


@router.get("/ventas", response_model=list[VentaOut])
def listar_ventas(
    fecha: date | None = None,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(
        require_rol("cajero", "encargado", "contador", "dueno")
    ),
):
    """Lista las ventas de un día (hoy por defecto), más recientes primero.

    Se usa `func.date` para comparar solo la fecha. Para el volumen de una
    panadería alcanza; si algún día crece, conviene filtrar por rango para
    aprovechar el índice de `fecha_hora`.
    """
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
