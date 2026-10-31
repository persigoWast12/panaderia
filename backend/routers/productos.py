"""Endpoints de consulta, creación y edición de productos."""

from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from database import get_db
from models import DetalleVenta, Empleado, Producto, Proveedor, Stock
from schemas import ProductoIn, ProductoOut, ProductoUpdate
from security import require_rol

router = APIRouter(tags=["Productos"])

MENSAJE_CODIGO_REPETIDO = "Ya existe un producto con ese código de barras."


def _producto_out(producto: Producto) -> dict:
    """Arma la respuesta plana del producto con su stock actual."""
    return {
        "id": producto.id,
        "nombre": producto.nombre,
        "codigo_barras": producto.codigo_barras,
        "unidad": producto.unidad,
        "precio": producto.precio,
        "proveedor_id": producto.proveedor_id,
        "activo": producto.activo,
        "cantidad_disponible": (
            producto.stock.cantidad_disponible
            if producto.stock is not None
            else Decimal("0")
        ),
    }


@router.get("/productos", response_model=list[ProductoOut])
def listar_productos(
    q: str | None = None,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("cajero", "encargado")),
):
    """Lista los productos activos, con su stock y búsqueda opcional por nombre."""
    consulta = (
        select(Producto)
        .options(selectinload(Producto.stock))
        .join(Stock)
        .where(Producto.activo.is_(True))
        .order_by(Producto.nombre)
    )
    if q and q.strip():
        consulta = consulta.where(Producto.nombre.ilike(f"%{q.strip()}%"))

    productos = db.scalars(consulta).all()
    return [_producto_out(producto) for producto in productos]


@router.get("/productos/codigo/{codigo_barras}", response_model=ProductoOut)
def buscar_por_codigo(
    codigo_barras: str,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("cajero", "encargado")),
):
    """Busca un producto por código exacto, incluso si está inactivo."""
    producto = db.scalar(
        select(Producto)
        .options(selectinload(Producto.stock))
        .where(Producto.codigo_barras == codigo_barras.strip())
    )
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    return _producto_out(producto)


@router.post("/productos", response_model=ProductoOut, status_code=201)
def crear_producto(
    datos: ProductoIn,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("encargado")),
):
    """Crea un producto y su fila de stock en una sola transacción."""
    repetido = db.scalar(
        select(Producto).where(Producto.codigo_barras == datos.codigo_barras)
    )
    if repetido is not None:
        raise HTTPException(status_code=400, detail=MENSAJE_CODIGO_REPETIDO)

    if datos.proveedor_id is not None:
        if db.get(Proveedor, datos.proveedor_id) is None:
            raise HTTPException(
                status_code=400, detail="El proveedor indicado no existe."
            )

    producto = Producto(
        nombre=datos.nombre,
        codigo_barras=datos.codigo_barras,
        unidad=datos.unidad,
        precio=datos.precio,
        proveedor_id=datos.proveedor_id,
        activo=datos.activo,
        stock=Stock(cantidad_disponible=datos.cantidad_inicial),
    )
    db.add(producto)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=MENSAJE_CODIGO_REPETIDO
        ) from None

    db.refresh(producto)
    return _producto_out(producto)


@router.put("/productos/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate | None = None,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("encargado")),
):
    """Actualiza solo los campos enviados del producto."""
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado.")

    cambios = (
        datos.model_dump(exclude_unset=True, exclude_none=True) if datos else {}
    )
    if not cambios:
        raise HTTPException(
            status_code=400, detail="No se enviaron campos para actualizar."
        )

    if "codigo_barras" in cambios:
        repetido = db.scalar(
            select(Producto).where(
                Producto.codigo_barras == cambios["codigo_barras"],
                Producto.id != producto_id,
            )
        )
        if repetido is not None:
            raise HTTPException(status_code=400, detail=MENSAJE_CODIGO_REPETIDO)

    if "unidad" in cambios and cambios["unidad"] != producto.unidad:
        ventas = db.scalar(
            select(func.count())
            .select_from(DetalleVenta)
            .where(DetalleVenta.producto_id == producto_id)
        )
        if ventas > 0:
            raise HTTPException(
                status_code=400,
                detail=(
                    "No se puede cambiar la unidad de un producto que ya tiene "
                    "ventas."
                ),
            )

    for campo, valor in cambios.items():
        setattr(producto, campo, valor)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=MENSAJE_CODIGO_REPETIDO
        ) from None

    db.refresh(producto)
    return _producto_out(producto)
