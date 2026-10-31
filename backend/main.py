"""Aplicación FastAPI del sistema de la panadería."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

import models  # noqa: F401  (registra las tablas en Base.metadata)
from database import Base, SessionLocal, engine
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
    finally:
        db.close()

    yield


app = FastAPI(title="Panadería", lifespan=lifespan)


@app.get("/test")
def test_endpoint():
    """Endpoint de prueba: confirma que el servidor está arriba."""
    return {"status": "ok"}
