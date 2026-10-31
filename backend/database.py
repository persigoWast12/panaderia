"""Conexión a PostgreSQL y sesión de SQLAlchemy."""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError(
        "Falta la variable de entorno DATABASE_URL. "
        "Copiá backend/.env.example a backend/.env y completá la conexión."
    )

# pool_pre_ping evita usar conexiones que PostgreSQL ya cerró.
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# autoflush=False: las escrituras se envían a la base solo cuando hacemos commit.
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """Clase base de todos los modelos (tablas)."""


def get_db():
    """Dependencia de FastAPI: entrega una sesión y la cierra al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
