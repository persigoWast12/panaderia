"""Endpoints de consulta y ajuste de stock."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import DetalleVenta, Empleado, Producto, Stock
from schemas import StockIn, StockOut
from security import require_rol

router = APIRouter(tags=["Stock"])


def _tiene_ventas(producto_id):
    """Devuelve una subconsulta EXISTS que indica si el producto tiene ventas.

    Se puede usar con un id concreto (en la respuesta de un PUT) o con la
    columna `Producto.id` (en el listado), donde queda correlacionada.
    """
    return (
        select(DetalleVenta.id)
        .where(DetalleVenta.producto_id == producto_id)
        .exists()
    )


def _stock_out(producto: Producto, cantidad, tiene_ventas: bool) -> dict:
    """Arma la fila de stock con los datos del producto."""
    return {
        "producto_id": producto.id,
        "nombre": producto.nombre,
        "codigo_barras": producto.codigo_barras,
        "unidad": producto.unidad,
        "precio": producto.precio,
        "activo": producto.activo,
        "cantidad_disponible": cantidad,
        "tiene_ventas": tiene_ventas,
    }


@router.get("/stock", response_model=list[StockOut])
def listar_stock(
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("cajero", "encargado", "dueno")),
):
    """Lista el stock de todos los productos, incluidos los inactivos.

    Es la fuente de datos de la pantalla de productos del encargado y del
    dueño: incluye precio y si el producto ya tiene ventas.
    """
    filas = db.execute(
        select(Producto, Stock.cantidad_disponible, _tiene_ventas(Producto.id))
        .join(Stock)
        .order_by(Producto.nombre)
    ).all()

    return [
        _stock_out(producto, cantidad, bool(ventas))
        for producto, cantidad, ventas in filas
    ]


@router.put("/stock/{producto_id}", response_model=StockOut)
def actualizar_stock(
    producto_id: int,
    datos: StockIn,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("encargado", "dueno")),
):
    """Fija la cantidad disponible de un producto.

    El ajuste es absoluto ("hay 30"), no un incremento. Se bloquea la fila de
    stock para que una venta simultánea no termine pisada por este ajuste.
    """
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    # El bloqueo evita que un ajuste pise el descuento de una venta simultánea.
    stock = db.scalar(
        select(Stock)
        .where(Stock.producto_id == producto_id)
        .with_for_update()
    )
    if stock is None:
        raise HTTPException(
            status_code=404, detail="El producto no tiene stock registrado."
        )

    # Se calcula antes del commit para no dejar una escritura hecha si la
    # consulta posterior fallara.
    tiene_ventas = bool(db.scalar(select(_tiene_ventas(producto_id))))

    stock.cantidad_disponible = datos.cantidad_disponible
    db.commit()
    db.refresh(stock)

    return _stock_out(producto, stock.cantidad_disponible, tiene_ventas)
