r"""Reinicia la base de la panadería.

Borra todas las tablas, las vuelve a crear y carga el seed. Pensado para
desarrollo y para volver al estado inicial antes de una demo.

Uso, desde backend/:

    .\.venv\Scripts\python.exe reset_db.py
    .\.venv\Scripts\python.exe reset_db.py --yes

Sin `--yes` pide confirmación. Usa la misma `DATABASE_URL` que la aplicación.
"""

import argparse
import sys

from sqlalchemy import func, select, text

import models  # noqa: F401  (registra todas las tablas en Base.metadata)
from database import Base, SessionLocal, engine
from models import Empleado, Producto, Venta
from seed import cargar_datos_iniciales


def contar(db, modelo):
    return db.scalar(select(func.count()).select_from(modelo))


def main() -> int:
    parser = argparse.ArgumentParser(description="Reinicia la base y carga el seed.")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="No pedir confirmación (para scripts o demos).",
    )
    args = parser.parse_args()

    nombre_base = engine.url.database
    print(f"Base de datos: {nombre_base}")

    if not args.yes:
        print("Esto va a borrar TODAS las tablas y volver a cargar el seed.")
        respuesta = input("Escribí 'si' para continuar: ").strip().lower()
        if respuesta != "si":
            print("Cancelado.")
            return 1

    print("Borrando tablas...")
    Base.metadata.drop_all(bind=engine)

    print("Creando tablas...")
    Base.metadata.create_all(bind=engine)

    # La búsqueda sin acentos necesita esta extensión.
    with engine.begin() as conexion:
        conexion.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))

    db = SessionLocal()
    try:
        if cargar_datos_iniciales(db):
            print("Seed cargado.")
        else:
            print("La base ya tenía datos; no se cargó el seed.")
        print(
            "Resumen:",
            f"{contar(db, Empleado)} empleados,",
            f"{contar(db, Producto)} productos,",
            f"{contar(db, Venta)} ventas.",
        )
    finally:
        db.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
