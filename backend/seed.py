"""Carga inicial de datos de ejemplo (solo si la base está vacía)."""

from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Empleado, Producto, Proveedor, Stock
from security import hash_password

# Contraseñas de desarrollo. Se documentan en el README; en la base va solo el hash.
PASSWORD_CAJERO = "cajero123"
PASSWORD_ENCARGADO = "encargado123"


def cargar_datos_iniciales(db: Session) -> bool:
    """Carga empleados, proveedores y productos si no hay ningún empleado.

    Devuelve True si cargó datos y False si ya existían. Todo se guarda en una
    sola transacción: si algo falla, no queda nada a medias.
    """
    if db.scalar(select(func.count()).select_from(Empleado)) > 0:
        return False

    try:
        molino = Proveedor(nombre="Molino San Blas", contacto="11-5555-0101")
        espiga = Proveedor(nombre="Distribuidora La Espiga", contacto="11-5555-0202")
        db.add_all([molino, espiga])
        db.flush()

        db.add_all(
            [
                Empleado(
                    nombre="Cajero de prueba",
                    rol="cajero",
                    usuario="cajero1",
                    password_hash=hash_password(PASSWORD_CAJERO),
                    activo=True,
                ),
                Empleado(
                    nombre="Encargado de prueba",
                    rol="encargado",
                    usuario="encargado1",
                    password_hash=hash_password(PASSWORD_ENCARGADO),
                    activo=True,
                ),
            ]
        )

        # (nombre, código de barras, unidad, precio, stock inicial, proveedor)
        datos = [
            ("Pan francés", "2000000000015", "kg", "3200.00", "15.000", molino),
            ("Pan de campo", "2000000000022", "kg", "4200.00", "8.000", molino),
            ("Pan integral", "2000000000039", "kg", "4800.00", "6.000", molino),
            ("Facturas surtidas", "2000000000046", "unidad", "450.00", "60.000", espiga),
            ("Medialunas de manteca", "2000000000053", "unidad", "550.00", "48.000", espiga),
            ("Torta de ricota", "2000000000060", "unidad", "7800.00", "4.000", espiga),
            ("Budín de limón", "2000000000077", "unidad", "5200.00", "6.000", espiga),
            ("Scones", "2000000000084", "unidad", "400.00", "30.000", espiga),
            ("Chips de queso", "2000000000091", "unidad", "600.00", "40.000", espiga),
            ("Pan saborizado", "2000000000107", "unidad", "900.00", "25.000", molino),
        ]

        productos = [
            Producto(
                nombre=nombre,
                codigo_barras=codigo,
                unidad=unidad,
                precio=Decimal(precio),
                activo=True,
                proveedor=proveedor,
                # El stock se crea junto con el producto (relación uno a uno).
                stock=Stock(cantidad_disponible=Decimal(cantidad)),
            )
            for nombre, codigo, unidad, precio, cantidad, proveedor in datos
        ]
        db.add_all(productos)

        db.commit()
        return True
    except Exception:
        db.rollback()
        raise
