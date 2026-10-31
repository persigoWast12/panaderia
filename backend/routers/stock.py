"""Endpoints de consulta y ajuste de stock."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_db
from models import Empleado, Producto, Stock
from schemas import StockIn, StockOut
from security import require_rol

router = APIRouter(tags=["Stock"])


@router.get("/stock", response_model=list[StockOut])
def listar_stock(
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("cajero", "encargado")),
):
    """Lista el stock de todos los productos, incluidos los inactivos."""
    filas = db.execute(
        select(Producto, Stock.cantidad_disponible)
        .join(Stock)
        .order_by(Producto.nombre)
    ).all()

    return [
        {
            "producto_id": producto.id,
            "nombre": producto.nombre,
            "codigo_barras": producto.codigo_barras,
            "unidad": producto.unidad,
            "activo": producto.activo,
            "cantidad_disponible": cantidad,
        }
        for producto, cantidad in filas
    ]


@router.put("/stock/{producto_id}", response_model=StockOut)
def actualizar_stock(
    producto_id: int,
    datos: StockIn,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("encargado")),
):
    """Fija la cantidad disponible de un producto."""
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    stock = db.scalar(select(Stock).where(Stock.producto_id == producto_id))
    if stock is None:
        raise HTTPException(
            status_code=404, detail="El producto no tiene stock registrado."
        )

    stock.cantidad_disponible = datos.cantidad_disponible
    db.commit()
    db.refresh(stock)

    return {
        "producto_id": producto.id,
        "nombre": producto.nombre,
        "codigo_barras": producto.codigo_barras,
        "unidad": producto.unidad,
        "activo": producto.activo,
        "cantidad_disponible": stock.cantidad_disponible,
    }
