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
MENSAJE_LIMITE = "El precio o el stock superan el máximo permitido."


def _escapar_like(texto: str) -> str:
    """Escapa los comodines de LIKE para buscar el texto literal.

    Si el usuario busca "%" o "_", no queremos que actúen como comodines.
    """
    return (
        texto.replace("\\", "\\\\")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _mensaje_integridad(error: IntegrityError) -> str:
    """Traduce un error de constraint a un mensaje para el usuario.

    No todos los IntegrityError son códigos repetidos: también pueden venir
    de los CHECK de precio y stock.
    """
    constraint = getattr(
        getattr(error.orig, "diag", None), "constraint_name", ""
    ) or ""
    texto = str(error.orig)

    if constraint == "producto_codigo_barras_key" or "duplicate key" in texto:
        return MENSAJE_CODIGO_REPETIDO
    if constraint in ("ck_producto_precio_max", "ck_stock_cantidad_max"):
        return MENSAJE_LIMITE
    return "No se pudo guardar el producto."


def _producto_out(producto: Producto) -> dict:
    """Arma la respuesta plana del producto con su stock actual.

    Si por algún motivo faltara la fila de stock, devuelve 0 en vez de fallar.
    """
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
    _empleado: Empleado = Depends(require_rol("cajero", "encargado", "dueno")),
):
    """Lista los productos activos, con su stock y búsqueda opcional por nombre.

    El cajero usa este endpoint para buscar y vender; por eso no incluye los
    productos inactivos (esos se ven en /stock, que es la pantalla del
    encargado).
    """
    consulta = (
        select(Producto)
        .options(selectinload(Producto.stock))
        .join(Stock)
        .where(Producto.activo.is_(True))
        .order_by(Producto.nombre)
    )
    if q and q.strip():
        patron = f"%{_escapar_like(q.strip())}%"
        consulta = consulta.where(
            func.unaccent(Producto.nombre).ilike(
                func.unaccent(patron), escape="\\"
            )
        )

    productos = db.scalars(consulta).all()
    return [_producto_out(producto) for producto in productos]


@router.get("/productos/codigo/{codigo_barras}", response_model=ProductoOut)
def buscar_por_codigo(
    codigo_barras: str,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("cajero", "encargado", "dueno")),
):
    """Busca un producto por código exacto, incluso si está inactivo.

    El cajero necesita el dato aunque esté inactivo para poder avisar
    "producto inactivo" en la pantalla de caja.
    """
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
    _empleado: Empleado = Depends(require_rol("encargado", "dueno")),
):
    """Crea un producto y su fila de stock en una sola transacción.

    Se valida el código antes de insertar para dar un mensaje claro. El
    `IntegrityError` queda como red de seguridad ante dos pedidos simultáneos.
    """
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
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=_mensaje_integridad(error)
        ) from None

    db.refresh(producto)
    return _producto_out(producto)


@router.put("/productos/{producto_id}", response_model=ProductoOut)
def actualizar_producto(
    producto_id: int,
    datos: ProductoUpdate | None = None,
    db: Session = Depends(get_db),
    _empleado: Empleado = Depends(require_rol("encargado", "dueno")),
):
    """Actualiza solo los campos enviados del producto.

    `exclude_unset` permite mandar un único campo, por ejemplo `{"activo":
    false}`. La unidad solo se puede cambiar si el producto todavía no tiene
    ventas, para no romper el historial de cantidades.
    """
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
        if cambios["unidad"] == "unidad" and producto.stock is not None:
            cantidad = producto.stock.cantidad_disponible
            if cantidad != cantidad.to_integral_value():
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Ajustá el stock a un número entero antes de cambiar "
                        "la unidad."
                    ),
                )

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
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=400, detail=_mensaje_integridad(error)
        ) from None

    db.refresh(producto)
    return _producto_out(producto)
