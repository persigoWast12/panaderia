"""Configuración de las pruebas: base aparte, seed y clientes."""

import os

from sqlalchemy.engine import make_url

url_pruebas = os.environ.get("TEST_DATABASE_URL")
if not url_pruebas:
    raise RuntimeError(
        "Definí TEST_DATABASE_URL antes de correr pytest, por ejemplo: "
        "postgresql+psycopg://postgres:clave@localhost:5432/panaderia_test"
    )

# Guarda de seguridad: las pruebas hacen drop_all y TRUNCATE. Si la URL
# apuntara por error a la base real, se perderían todos los datos.
nombre_base = make_url(url_pruebas).database or ""
if not nombre_base.endswith("_test"):
    raise RuntimeError(
        f"TEST_DATABASE_URL apunta a '{nombre_base}'. "
        "Por seguridad, la base de pruebas tiene que terminar en '_test'."
    )

# Tiene que quedar definido antes de importar la app.
os.environ["DATABASE_URL"] = url_pruebas

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from database import Base, SessionLocal, engine
from main import app
from seed import cargar_datos_iniciales


@pytest.fixture(scope="session", autouse=True)
def preparar_base():
    """Deja la base de pruebas vacía y con las tablas nuevas."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture(autouse=True)
def base_limpia():
    """Vacía todas las tablas y vuelve a cargar el seed antes de cada prueba."""
    tablas = ", ".join(f'"{tabla.name}"' for tabla in Base.metadata.sorted_tables)
    with engine.begin() as conexion:
        conexion.execute(text(f"TRUNCATE {tablas} RESTART IDENTITY CASCADE"))

    db = SessionLocal()
    try:
        cargar_datos_iniciales(db)
    finally:
        db.close()

    yield


@pytest.fixture()
def db():
    sesion = SessionLocal()
    try:
        yield sesion
    finally:
        sesion.close()


@pytest.fixture()
def client():
    with TestClient(app) as cliente:
        yield cliente


@pytest.fixture()
def crear_cliente():
    """Crea clientes extra (por ejemplo, para probar dos sesiones a la vez)."""
    clientes = []

    def crear():
        cliente = TestClient(app)
        cliente.__enter__()
        clientes.append(cliente)
        return cliente

    yield crear

    for cliente in clientes:
        cliente.__exit__(None, None, None)


@pytest.fixture()
def login():
    """Inicia sesión en un cliente y deja la cookie lista."""

    def iniciar(cliente, usuario, password):
        respuesta = cliente.post(
            "/login", json={"usuario": usuario, "password": password}
        )
        assert respuesta.status_code == 200, respuesta.text
        return respuesta

    return iniciar
