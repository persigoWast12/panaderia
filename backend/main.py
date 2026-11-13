"""Aplicación FastAPI del sistema de la panadería.

Concentra el arranque: registro de routers, creación de tablas, seed inicial
y limpieza de sesiones vencidas. Se debe correr con un solo worker, porque el
seed no está preparado para dos procesos arrancando a la vez.
"""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import Depends, FastAPI
from sqlalchemy import delete, text
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from models import Sesion  # también registra todas las tablas en Base.metadata
from routers import auth, empleados, productos, stock, ventas
from seed import cargar_datos_iniciales


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas y carga el seed una sola vez al arrancar."""
    # create_all es idempotente: no borra ni modifica tablas existentes.
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Necesaria para que la búsqueda ignore acentos ("budin" -> "Budín").
        db.execute(text("CREATE EXTENSION IF NOT EXISTS unaccent"))
        db.commit()

        # El seed solo inserta si no hay ningún empleado (base vacía).
        if cargar_datos_iniciales(db):
            print("Seed: datos de ejemplo cargados.")
        else:
            print("Seed: la base ya tenía datos, no se cargó nada.")

        # Las sesiones vencidas ya no sirven: se borran al arrancar.
        db.execute(delete(Sesion).where(Sesion.vence < datetime.now()))
        db.commit()
    finally:
        db.close()

    yield


app = FastAPI(title="Panadería", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(productos.router)
app.include_router(stock.router)
app.include_router(ventas.router)
app.include_router(empleados.router)


@app.get("/test")
def test_endpoint(db: Session = Depends(get_db)):
    """Confirma que el servidor y la base de datos responden.

    Si PostgreSQL está caído, la consulta falla y el endpoint devuelve 500.
    """
    db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}
