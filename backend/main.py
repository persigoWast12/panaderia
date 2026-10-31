"""Aplicación FastAPI del sistema de la panadería."""

from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI
from sqlalchemy import delete

from database import Base, SessionLocal, engine
from models import Sesion  # también registra todas las tablas en Base.metadata
from routers import auth, productos, stock, ventas
from seed import cargar_datos_iniciales


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas y carga el seed una sola vez al arrancar."""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
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


@app.get("/test")
def test_endpoint():
    """Endpoint de prueba: confirma que el servidor está arriba."""
    return {"status": "ok"}
