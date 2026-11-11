"""Pruebas de login, sesiones y permisos por rol."""

from datetime import datetime, timedelta

from sqlalchemy import func, select

from models import Empleado, Sesion

VENTA = {
    "forma_pago": "efectivo",
    "items": [{"producto_id": 1, "cantidad": 1}],
}


def test_me_sin_cookie(client):
    assert client.get("/me").status_code == 401


def test_login_incorrecto(client):
    respuesta = client.post(
        "/login", json={"usuario": "cajero1", "password": "incorrecta"}
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["detail"] == "usuario o contraseña incorrectos"


def test_login_normaliza_usuario(client, login):
    for usuario in ("cajero1", "Cajero1", "  cajero1  "):
        client.cookies.clear()
        login(client, usuario, "cajero123")
        assert client.get("/me").json()["rol"] == "cajero"


def test_login_correcto_y_me(client, login):
    login(client, "cajero1", "cajero123")
    assert "session" in client.cookies

    datos = client.get("/me").json()
    assert datos["usuario"] == "cajero1"
    assert datos["nombre"] == "Cajero de prueba"
    assert datos["rol"] == "cajero"


def test_logout(client, login, db):
    login(client, "cajero1", "cajero123")
    assert client.post("/logout").status_code == 200
    assert client.get("/me").status_code == 401
    assert db.scalar(select(func.count()).select_from(Sesion)) == 0


def test_cookie_inventada(client):
    client.cookies.set("session", "token-inventado")
    assert client.get("/me").status_code == 401


def test_sesion_vencida(client, login, db):
    login(client, "cajero1", "cajero123")
    sesion = db.scalar(select(Sesion))
    sesion.vence = datetime.now() - timedelta(hours=1)
    db.commit()

    assert client.get("/me").status_code == 401


def test_empleado_inactivo(client, login, db):
    login(client, "cajero1", "cajero123")
    empleado = db.scalar(
        select(Empleado).where(Empleado.usuario == "cajero1")
    )
    empleado.activo = False
    db.commit()

    assert client.get("/me").status_code == 401


def test_cajero_no_puede_modificar(client, login):
    login(client, "cajero1", "cajero123")

    assert client.post(
        "/productos",
        json={
            "nombre": "Pan de prueba",
            "codigo_barras": "3000000000010",
            "unidad": "unidad",
            "precio": 1000,
            "cantidad_inicial": 5,
        },
    ).status_code == 403
    assert client.put(
        "/stock/1", json={"cantidad_disponible": 5}
    ).status_code == 403
    assert client.get("/empleados").status_code == 403


def test_encargado_no_administra_empleados(client, login):
    login(client, "encargado1", "encargado123")
    assert client.get("/empleados").status_code == 403


def test_contador_solo_consulta_ventas(client, login):
    login(client, "dueno1", "dueno123")
    creado = client.post(
        "/empleados",
        json={
            "nombre": "Contador de prueba",
            "usuario": "contador1",
            "rol": "contador",
            "password": "contador123",
        },
    )
    assert creado.status_code == 201

    client.cookies.clear()
    login(client, "contador1", "contador123")

    assert client.get("/ventas").status_code == 200
    assert client.get("/productos").status_code == 403
    assert client.get("/stock").status_code == 403
    assert client.get("/empleados").status_code == 403
    assert client.post("/ventas", json=VENTA).status_code == 403


def test_dueno_no_vende(client, login):
    login(client, "dueno1", "dueno123")

    assert client.post("/ventas", json=VENTA).status_code == 403
    assert client.get("/productos").status_code == 200
    assert client.get("/stock").status_code == 200
    assert client.get("/ventas").status_code == 200
    assert client.get("/empleados").status_code == 200
