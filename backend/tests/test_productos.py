"""Pruebas de productos y stock."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from models import Producto, Stock

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
        f"/stock/{producto['id']}", json={"cantidad_disponible": 12}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["cantidad_disponible"] == 12.0

    negativa = client.put(
        f"/stock/{producto['id']}", json={"cantidad_disponible": -1}
    )
    assert negativa.status_code == 422


def test_actualizar_stock_decimal_en_producto_por_kg(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(
        client, unidad="kg", cantidad_inicial=5
    ).json()

    respuesta = client.put(
        f"/stock/{producto['id']}", json={"cantidad_disponible": 12.5}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["cantidad_disponible"] == 12.5


def test_stock_fraccionario_en_producto_por_unidad(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(client, cantidad_inicial=5).json()

    respuesta = client.put(
        f"/stock/{producto['id']}", json={"cantidad_disponible": 12.5}
    )
    assert respuesta.status_code == 400
    assert "entero" in respuesta.json()["detail"]


def test_limites_de_precio_y_stock(client, login):
    login(client, "encargado1", "encargado123")

    en_limite = crear_producto(
        client,
        codigo_barras="3000000000027",
        precio=1000000,
        cantidad_inicial=100000,
    )
    assert en_limite.status_code == 201

    precio_excedido = crear_producto(
        client,
        codigo_barras="3000000000034",
        precio=1000000.01,
    )
    assert precio_excedido.status_code == 422

    stock_excedido = crear_producto(
        client,
        codigo_barras="3000000000041",
        unidad="kg",
        cantidad_inicial=100000.001,
    )
    assert stock_excedido.status_code == 422


def test_precio_maximo_en_edicion(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(client).json()

    respuesta = client.put(
        f"/productos/{producto['id']}", json={"precio": 1000000.01}
    )
    assert respuesta.status_code == 422


def test_no_cambiar_a_unidad_con_stock_fraccionario(client, login):
    login(client, "encargado1", "encargado123")
    producto = crear_producto(
        client, unidad="kg", cantidad_inicial=2.5
    ).json()

    respuesta = client.put(
        f"/productos/{producto['id']}", json={"unidad": "unidad"}
    )
    assert respuesta.status_code == 400
    assert "entero" in respuesta.json()["detail"]

    assert (
        client.put(
            f"/stock/{producto['id']}", json={"cantidad_disponible": 2}
        ).status_code
        == 200
    )

    respuesta = client.put(
        f"/productos/{producto['id']}", json={"unidad": "unidad"}
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["unidad"] == "unidad"


def test_producto_por_unidad_rechaza_stock_fraccionario_al_crear(
    client, login
):
    login(client, "encargado1", "encargado123")

    respuesta = crear_producto(
        client, cantidad_inicial=2.5, codigo_barras="3000000000058"
    )
    assert respuesta.status_code == 422


def test_constraint_de_precio_maximo(db):
    producto = Producto(
        nombre="Precio excedido",
        codigo_barras="3999999999991",
        unidad="unidad",
        precio=Decimal("1000000.01"),
        stock=Stock(cantidad_disponible=Decimal("1")),
    )
    db.add(producto)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_constraint_de_stock_maximo(db):
    producto = Producto(
        nombre="Stock excedido",
        codigo_barras="3999999999992",
        unidad="kg",
        precio=Decimal("1"),
        stock=Stock(cantidad_disponible=Decimal("100000.001")),
    )
    db.add(producto)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_busqueda_sin_acentos(client, login):
    login(client, "encargado1", "encargado123")

    productos = client.get("/productos", params={"q": "budin"}).json()
    assert any(producto["nombre"] == "Budín de limón" for producto in productos)


def test_busqueda_escapa_comodines(client, login):
    login(client, "encargado1", "encargado123")
    crear_producto(
        client,
        nombre="Pan 100% integral",
        codigo_barras="3000000000089",
    )

    productos = client.get("/productos", params={"q": "%"}).json()
    assert [producto["nombre"] for producto in productos] == [
        "Pan 100% integral"
    ]

    assert client.get("/productos", params={"q": "_"}).json() == []


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
