"""Pruebas del registro y la consulta de ventas."""

import threading
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from main import app
from models import DetalleVenta, Venta

PRODUCTO = {
    "nombre": "Producto de prueba",
    "codigo_barras": "3000000000010",
    "unidad": "unidad",
    "precio": 100,
    "cantidad_inicial": 10,
}


def stock_de(client, producto_id):
    return next(
        fila
        for fila in client.get("/stock").json()
        if fila["producto_id"] == producto_id
    )


def test_venta_de_varios_productos_descuenta_stock(client, login):
    login(client, "cajero1", "cajero123")

    antes_1 = stock_de(client, 1)["cantidad_disponible"]
    antes_4 = stock_de(client, 4)["cantidad_disponible"]

    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [
                {"producto_id": 1, "cantidad": 1.25},
                {"producto_id": 4, "cantidad": 2},
            ],
        },
    )
    assert respuesta.status_code == 201

    venta = respuesta.json()
    assert venta["total"] == 4900.0
    assert len(venta["items"]) == 2
    assert {item["producto_id"] for item in venta["items"]} == {1, 4}

    assert stock_de(client, 1)["cantidad_disponible"] == pytest.approx(
        antes_1 - 1.25
    )
    assert stock_de(client, 4)["cantidad_disponible"] == pytest.approx(
        antes_4 - 2
    )


def test_total_es_la_suma_de_subtotales_redondeados(client, login):
    login(client, "encargado1", "encargado123")
    producto = client.post(
        "/productos",
        json={
            "nombre": "Pan por kilo",
            "codigo_barras": "3000000000010",
            "unidad": "kg",
            "precio": 100.05,
            "cantidad_inicial": 10,
        },
    ).json()

    client.cookies.clear()
    login(client, "cajero1", "cajero123")

    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "tarjeta",
            "items": [
                {"producto_id": producto["id"], "cantidad": 1.005},
                {"producto_id": 4, "cantidad": 1},
            ],
        },
    )
    assert respuesta.status_code == 201

    venta = respuesta.json()
    suma = round(sum(item["subtotal"] for item in venta["items"]), 2)
    assert venta["total"] == suma
    assert venta["total"] == 550.55


def test_total_enviado_por_el_cliente_se_ignora(client, login):
    login(client, "cajero1", "cajero123")

    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "total": 1,
            "items": [{"producto_id": 4, "cantidad": 1}],
        },
    )
    assert respuesta.status_code == 201
    assert respuesta.json()["total"] == 450.0


def test_stock_insuficiente_no_modifica_nada(client, login, db):
    login(client, "cajero1", "cajero123")
    antes = stock_de(client, 4)["cantidad_disponible"]
    ventas_antes = db.scalar(select(func.count()).select_from(Venta))

    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": 4, "cantidad": 999}],
        },
    )
    assert respuesta.status_code == 400
    assert "Facturas surtidas" in respuesta.json()["detail"]

    assert stock_de(client, 4)["cantidad_disponible"] == antes
    assert db.scalar(select(func.count()).select_from(Venta)) == ventas_antes


def test_precio_congelado_en_la_venta(client, login):
    login(client, "cajero1", "cajero123")
    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": 2, "cantidad": 1}],
        },
    )
    assert respuesta.status_code == 201
    venta_id = respuesta.json()["id"]

    client.cookies.clear()
    login(client, "dueno1", "dueno123")
    assert (
        client.put("/productos/2", json={"precio": 9999}).status_code == 200
    )

    ventas = client.get("/ventas").json()
    venta = next(venta for venta in ventas if venta["id"] == venta_id)
    assert venta["items"][0]["precio_unitario"] == 4200.0


def test_cantidad_fraccionaria_en_producto_por_unidad(client, login):
    login(client, "cajero1", "cajero123")

    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": 4, "cantidad": 1.5}],
        },
    )
    assert respuesta.status_code == 400
    assert "entera" in respuesta.json()["detail"]


def test_producto_inactivo_no_se_vende(client, login):
    login(client, "encargado1", "encargado123")
    assert (
        client.put("/productos/5", json={"activo": False}).status_code == 200
    )

    client.cookies.clear()
    login(client, "cajero1", "cajero123")
    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": 5, "cantidad": 1}],
        },
    )
    assert respuesta.status_code == 400
    assert "inactivo" in respuesta.json()["detail"]


def test_encargado_no_vende(client, login):
    login(client, "encargado1", "encargado123")

    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": 1, "cantidad": 1}],
        },
    )
    assert respuesta.status_code == 403


def test_renglones_repetidos_se_agrupan(client, login):
    login(client, "cajero1", "cajero123")
    antes = stock_de(client, 4)["cantidad_disponible"]

    respuesta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [
                {"producto_id": 4, "cantidad": 1},
                {"producto_id": 4, "cantidad": 2},
            ],
        },
    )
    assert respuesta.status_code == 201

    venta = respuesta.json()
    assert len(venta["items"]) == 1
    assert venta["items"][0]["cantidad"] == 3.0
    assert stock_de(client, 4)["cantidad_disponible"] == pytest.approx(
        antes - 3
    )


def test_get_ventas_incluye_renglones(client, login):
    login(client, "cajero1", "cajero123")
    creada = client.post(
        "/ventas",
        json={
            "forma_pago": "billetera_virtual",
            "items": [{"producto_id": 1, "cantidad": 0.5}],
        },
    ).json()

    client.cookies.clear()
    login(client, "dueno1", "dueno123")
    ventas = client.get("/ventas").json()

    venta = next(venta for venta in ventas if venta["id"] == creada["id"])
    assert venta["forma_pago"] == "billetera_virtual"
    assert venta["items"][0]["nombre"] == "Pan francés"
    assert venta["items"][0]["unidad"] == "kg"
    assert venta["items"][0]["cantidad"] == 0.5


def test_dos_ventas_simultaneas_no_dejan_stock_negativo(client, login):
    login(client, "encargado1", "encargado123")
    producto = client.post(
        "/productos",
        json={**PRODUCTO, "cantidad_inicial": 1},
    ).json()

    resultados = []
    barrera = threading.Barrier(2)

    def vender():
        with TestClient(app) as propio:
            login(propio, "cajero1", "cajero123")
            barrera.wait()
            respuesta = propio.post(
                "/ventas",
                json={
                    "forma_pago": "efectivo",
                    "items": [
                        {"producto_id": producto["id"], "cantidad": 1}
                    ],
                },
            )
            resultados.append(respuesta.status_code)

    hilos = [threading.Thread(target=vender) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    assert sorted(resultados) == [201, 400]
    assert stock_de(client, producto["id"])["cantidad_disponible"] == 0.0


def test_cantidad_maxima_por_item(client, login):
    login(client, "encargado1", "encargado123")
    producto = client.post(
        "/productos",
        json={
            "nombre": "Producto por kilo grande",
            "codigo_barras": "3000000000065",
            "unidad": "kg",
            "precio": 1,
            "cantidad_inicial": 20000,
        },
    ).json()

    client.cookies.clear()
    login(client, "cajero1", "cajero123")

    excedida = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [
                {"producto_id": producto["id"], "cantidad": 10000.001}
            ],
        },
    )
    assert excedida.status_code == 422

    valida = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": producto["id"], "cantidad": 10000}],
        },
    )
    assert valida.status_code == 201
    assert valida.json()["total"] == 10000.0


def test_total_maximo_de_venta(client, login, db):
    login(client, "encargado1", "encargado123")
    producto = client.post(
        "/productos",
        json={
            "nombre": "Producto de un millón",
            "codigo_barras": "3000000000072",
            "unidad": "unidad",
            "precio": 1000000,
            "cantidad_inicial": 20,
        },
    ).json()

    client.cookies.clear()
    login(client, "cajero1", "cajero123")
    ventas_antes = db.scalar(select(func.count()).select_from(Venta))

    excedida = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": producto["id"], "cantidad": 11}],
        },
    )
    assert excedida.status_code == 400
    assert "máximo" in excedida.json()["detail"]
    assert stock_de(client, producto["id"])["cantidad_disponible"] == 20.0
    assert db.scalar(select(func.count()).select_from(Venta)) == ventas_antes

    valida = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": producto["id"], "cantidad": 10}],
        },
    )
    assert valida.status_code == 201
    assert valida.json()["total"] == 10000000.0
    assert stock_de(client, producto["id"])["cantidad_disponible"] == 10.0


def test_nombre_producto_congelado_en_la_venta(client, login):
    login(client, "encargado1", "encargado123")
    producto = client.post(
        "/productos",
        json={
            "nombre": "Pan con nombre viejo",
            "codigo_barras": "3000000000096",
            "unidad": "unidad",
            "precio": 100,
            "cantidad_inicial": 5,
        },
    ).json()

    client.cookies.clear()
    login(client, "cajero1", "cajero123")
    venta = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": producto["id"], "cantidad": 1}],
        },
    ).json()

    client.cookies.clear()
    login(client, "encargado1", "encargado123")
    assert (
        client.put(
            f"/productos/{producto['id']}",
            json={"nombre": "Pan con nombre nuevo"},
        ).status_code
        == 200
    )

    client.cookies.clear()
    login(client, "dueno1", "dueno123")
    ventas = client.get("/ventas").json()
    encontrada = next(v for v in ventas if v["id"] == venta["id"])
    assert encontrada["items"][0]["nombre"] == "Pan con nombre viejo"


def test_cantidad_con_mas_de_tres_decimales(client, login):
    login(client, "encargado1", "encargado123")
    producto = client.post(
        "/productos",
        json={
            "nombre": "Pan por kilo con decimales",
            "codigo_barras": "3000000000133",
            "unidad": "kg",
            "precio": 100,
            "cantidad_inicial": 5,
        },
    ).json()

    client.cookies.clear()
    login(client, "cajero1", "cajero123")

    excedida = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [
                {"producto_id": producto["id"], "cantidad": 1.2345}
            ],
        },
    )
    assert excedida.status_code == 422

    valida = client.post(
        "/ventas",
        json={
            "forma_pago": "efectivo",
            "items": [{"producto_id": producto["id"], "cantidad": 1.234}],
        },
    )
    assert valida.status_code == 201


def test_constraint_de_cantidad_maxima(db):
    venta = Venta(
        empleado_id=1,
        forma_pago="efectivo",
        total=Decimal("1"),
    )
    venta.detalles.append(
        DetalleVenta(
            producto_id=1,
            nombre_producto="Producto de prueba",
            cantidad=Decimal("10000.001"),
            precio_unitario=Decimal("1"),
        )
    )
    db.add(venta)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_constraint_de_total_maximo(db):
    venta = Venta(
        empleado_id=1,
        forma_pago="efectivo",
        total=Decimal("10000000.01"),
    )
    db.add(venta)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
