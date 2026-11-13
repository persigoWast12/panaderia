"""Pruebas de la administración de empleados (solo dueño)."""

from seed import PASSWORD_CAJERO


def crear_cajero(client, usuario="cajero2", nombre="Cajero dos"):
    return client.post(
        "/empleados",
        json={
            "nombre": nombre,
            "usuario": usuario,
            "rol": "cajero",
            "password": PASSWORD_CAJERO,
        },
    )


def test_listar_empleados(client, login):
    login(client, "dueno1", "dueno123")

    respuesta = client.get("/empleados")
    assert respuesta.status_code == 200

    empleados = respuesta.json()
    assert {empleado["usuario"] for empleado in empleados} == {
        "cajero1",
        "encargado1",
        "contador1",
        "dueno1",
    }
    assert all("password_hash" not in empleado for empleado in empleados)


def test_crear_empleado_y_entrar(client, login):
    login(client, "dueno1", "dueno123")

    respuesta = client.post(
        "/empleados",
        json={
            "nombre": "Contador de prueba",
            "usuario": "contador_prueba",
            "rol": "contador",
            "password": "contador123",
        },
    )
    assert respuesta.status_code == 201

    datos = respuesta.json()
    assert datos["usuario"] == "contador_prueba"
    assert datos["rol"] == "contador"
    assert datos["activo"] is True

    client.cookies.clear()
    login(client, "contador_prueba", "contador123")
    assert client.get("/me").json()["rol"] == "contador"


def test_usuario_repetido(client, login):
    login(client, "dueno1", "dueno123")

    respuesta = crear_cajero(client, usuario="Cajero1")
    assert respuesta.status_code == 400
    assert "usuario" in respuesta.json()["detail"]


def test_password_corta(client, login):
    login(client, "dueno1", "dueno123")

    respuesta = client.post(
        "/empleados",
        json={
            "nombre": "Cajero dos",
            "usuario": "cajero2",
            "rol": "cajero",
            "password": "corta",
        },
    )
    assert respuesta.status_code == 422


def test_editar_empleado(client, login):
    login(client, "dueno1", "dueno123")
    creado = crear_cajero(client).json()

    respuesta = client.put(
        f"/empleados/{creado['id']}",
        json={
            "nombre": "Cajero renombrado",
            "usuario": "cajero2b",
            "rol": "encargado",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["nombre"] == "Cajero renombrado"
    assert respuesta.json()["usuario"] == "cajero2b"
    assert respuesta.json()["rol"] == "encargado"

    client.cookies.clear()
    login(client, "cajero2b", PASSWORD_CAJERO)
    assert client.get("/me").json()["rol"] == "encargado"


def test_resetear_password_cierra_sesiones(client, login, crear_cliente):
    login(client, "dueno1", "dueno123")
    creado = crear_cajero(client).json()

    otro = crear_cliente()
    login(otro, "cajero2", PASSWORD_CAJERO)
    assert otro.get("/me").status_code == 200

    respuesta = client.put(
        f"/empleados/{creado['id']}/password",
        json={"password": "nueva123"},
    )
    assert respuesta.status_code == 200

    # La sesión que estaba abierta deja de servir.
    assert otro.get("/me").status_code == 401

    # La contraseña vieja ya no entra y la nueva sí.
    otro.cookies.clear()
    assert (
        otro.post(
            "/login",
            json={"usuario": "cajero2", "password": PASSWORD_CAJERO},
        ).status_code
        == 401
    )
    login(otro, "cajero2", "nueva123")


def test_desactivar_empleado_cierra_sesion(client, login, crear_cliente):
    login(client, "dueno1", "dueno123")
    creado = crear_cajero(client).json()

    otro = crear_cliente()
    login(otro, "cajero2", PASSWORD_CAJERO)

    respuesta = client.put(
        f"/empleados/{creado['id']}", json={"activo": False}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["activo"] is False

    assert otro.get("/me").status_code == 401

    otro.cookies.clear()
    assert (
        otro.post(
            "/login",
            json={"usuario": "cajero2", "password": PASSWORD_CAJERO},
        ).status_code
        == 401
    )


def test_no_puede_desactivarse_a_si_mismo(client, login):
    login(client, "dueno1", "dueno123")
    yo = client.get("/me").json()

    respuesta = client.put(
        f"/empleados/{yo['id']}", json={"activo": False}
    )
    assert respuesta.status_code == 400


def test_no_puede_cambiar_su_propio_rol(client, login):
    login(client, "dueno1", "dueno123")
    yo = client.get("/me").json()

    respuesta = client.put(
        f"/empleados/{yo['id']}", json={"rol": "encargado"}
    )
    assert respuesta.status_code == 400


def test_encargado_no_administra_empleados(client, login):
    login(client, "encargado1", "encargado123")

    assert client.get("/empleados").status_code == 403
    assert (
        client.put(
            "/empleados/1",
            json={"nombre": "Otro nombre"},
        ).status_code
        == 403
    )
    assert (
        client.put(
            "/empleados/1/password", json={"password": "nueva123"}
        ).status_code
        == 403
    )
