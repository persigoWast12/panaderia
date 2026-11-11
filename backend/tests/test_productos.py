"""Pruebas de productos y stock."""

PRODUCTO = {
    "nombre": "Pan de prueba",
    "codigo_barras": "3000000000010",
    "unidad": "unidad",
    "precio": 1200,
    "cantidad_inicial": 10,
}


def crear_producto(client, **cambios):
    datos = {**PRODUCTO, **cambios}
    return client.post("/productos", json=datos)


def test_encargado_crea_producto_y_stock(client, login):
    login(client, "encargado1", "encargado123")

    respuesta = crear_producto(client, cantidad_inicial=20)
    assert respuesta.status_code == 201

    producto = respuesta.json()
    assert producto["cantidad_disponible"] == 20.0

    fila = next(
        fila
        for fila in client.get("/stock").json()
        if fila["producto_id"] == producto["id"]
    )
    assert fila["cantidad_disponible"] == 20.0
    assert fila["tiene_ventas"] is False
    assert fila["precio"] == 1200.0


def test_codigo_de_barras_repetido(client, login):
    login(client, "encargado1", "encargado123")

    assert crear_producto(client).status_code == 201
    repetido = crear_producto(client, nombre="Otro pan")
    assert repetido.status_code == 400
    assert "código de barras" in repetido.json()["detail"]


def test_busqueda_por_nombre(client, login):
    login(client, "encargado1", "encargado123")
    crear_producto(client, nombre="Pan de nuez", precio=1500)

    productos = client.get("/productos?q=nuez").json()
    assert [producto["nombre"] for producto in productos] == ["Pan de nuez"]


def test_inactivo_no_aparece_en_productos_pero_si_en_stock(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(client).json()

    assert (
        client.put(
            f"/productos/{producto['id']}", json={"activo": False}
        ).status_code
        == 200
    )

    activos = [fila["id"] for fila in client.get("/productos").json()]
    assert producto["id"] not in activos

    fila = next(
        fila
        for fila in client.get("/stock").json()
        if fila["producto_id"] == producto["id"]
    )
    assert fila["activo"] is False


def test_buscar_por_codigo_incluye_inactivos(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(client).json()

    encontrado = client.get(
        f"/productos/codigo/{producto['codigo_barras']}"
    )
    assert encontrado.status_code == 200
    assert encontrado.json()["id"] == producto["id"]

    client.put(f"/productos/{producto['id']}", json={"activo": False})
    encontrado = client.get(
        f"/productos/codigo/{producto['codigo_barras']}"
    )
    assert encontrado.status_code == 200
    assert encontrado.json()["activo"] is False

    assert client.get("/productos/codigo/9999999999999").status_code == 404


def test_actualizar_stock(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(client, cantidad_inicial=5).json()

    respuesta = client.put(
        f"/stock/{producto['id']}", json={"cantidad_disponible": 12.5}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["cantidad_disponible"] == 12.5

    negativa = client.put(
        f"/stock/{producto['id']}", json={"cantidad_disponible": -1}
    )
    assert negativa.status_code == 422


def test_cambiar_unidad_sin_ventas(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(client).json()

    respuesta = client.put(
        f"/productos/{producto['id']}", json={"unidad": "kg"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["unidad"] == "kg"


def test_no_cambiar_unidad_con_ventas(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(client).json()

    client.cookies.clear()
    login(client, "cajero1", "cajero123")
    venta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": producto["id"], "cantidad": 1}],
        },
    )
    assert venta.status_code == 201

    client.cookies.clear()
    login(client, "encargado1", "encargado123")
    respuesta = client.put(
        f"/productos/{producto['id']}", json={"unidad": "kg"}
    )
    assert respuesta.status_code == 400
    assert "unidad" in respuesta.json()["detail"]


def test_dueno_administra_productos(client, login):
    login(client, "dueno1", "dueno123")
    producto = crear_producto(client).json()

    assert (
        client.put(
            f"/productos/{producto['id']}", json={"precio": 2000}
        ).status_code
        == 200
    )
    assert (
        client.put(
            f"/stock/{producto['id']}", json={"cantidad_disponible": 3}
        ).status_code
        == 200
    )
