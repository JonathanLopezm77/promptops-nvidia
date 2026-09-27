"""Pruebas ocultas de la fase 4 (Implementación) del benchmark.

Verifican el contrato de benchmarks/casos/fase4_implementacion.json. Los
modelos no las ven. Se ejecutan contra el wishlist_service.py generado por
cada modelo (y contra la implementación de referencia, que debe pasar el
100 %). Cada prueba se identifica con el SPEC que verifica.
"""

import dataclasses
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

import wishlist_service as ws

T0 = datetime(2026, 1, 1, 12, 0, 0)


def _servicio(max_items=50):
    return ws.WishlistService(max_items=max_items)


# --- Estructura del contrato -------------------------------------------------


def test_contrato_excepciones_heredan_de_wishlisterror():
    for nombre in ("DuplicateItemError", "WishlistFullError", "ItemNotFoundError", "InvalidPriceError"):
        assert issubclass(getattr(ws, nombre), ws.WishlistError)
    assert issubclass(ws.WishlistError, Exception)


def test_contrato_dataclasses_inmutables_con_campos_exactos():
    assert [f.name for f in dataclasses.fields(ws.WishlistItem)] == ["product_id", "added_at", "price_at_add"]
    assert [f.name for f in dataclasses.fields(ws.PriceDrop)] == ["product_id", "old_price", "new_price", "drop_pct"]
    item = ws.WishlistItem("p1", T0, Decimal("10"))
    with pytest.raises(dataclasses.FrozenInstanceError):
        item.product_id = "otro"


def test_contrato_max_items_invalido():
    with pytest.raises(ValueError):
        ws.WishlistService(max_items=0)


# --- SPEC-01: agregar -----------------------------------------------------------


def test_spec01_agregar_devuelve_el_item():
    item = _servicio().add_item("c1", "p1", Decimal("99.90"), T0)
    assert item == ws.WishlistItem(product_id="p1", added_at=T0, price_at_add=Decimal("99.90"))


def test_spec01_max_items_por_defecto_es_50():
    s = ws.WishlistService()
    for i in range(50):
        s.add_item("c1", f"p{i}", Decimal("1"), T0)
    with pytest.raises(ws.WishlistFullError):
        s.add_item("c1", "p50", Decimal("1"), T0)


@pytest.mark.parametrize(("cliente", "producto"), [("", "p1"), ("c1", ""), ("   ", "p1"), ("c1", "  ")])
def test_spec01_ids_vacios(cliente, producto):
    with pytest.raises(ValueError):
        _servicio().add_item(cliente, producto, Decimal("1"), T0)


@pytest.mark.parametrize("precio", [Decimal("0"), Decimal("-5")])
def test_spec01_precio_invalido(precio):
    with pytest.raises(ws.InvalidPriceError):
        _servicio().add_item("c1", "p1", precio, T0)


def test_spec01_duplicado():
    s = _servicio()
    s.add_item("c1", "p1", Decimal("10"), T0)
    with pytest.raises(ws.DuplicateItemError):
        s.add_item("c1", "p1", Decimal("12"), T0)


def test_spec01_lista_llena():
    s = _servicio(max_items=2)
    s.add_item("c1", "p1", Decimal("10"), T0)
    s.add_item("c1", "p2", Decimal("10"), T0)
    with pytest.raises(ws.WishlistFullError):
        s.add_item("c1", "p3", Decimal("10"), T0)


def test_spec01_orden_de_validaciones_duplicado_antes_que_llena():
    s = _servicio(max_items=1)
    s.add_item("c1", "p1", Decimal("10"), T0)
    with pytest.raises(ws.DuplicateItemError):
        s.add_item("c1", "p1", Decimal("10"), T0)


def test_spec01_orden_de_validaciones_precio_antes_que_duplicado():
    s = _servicio()
    s.add_item("c1", "p1", Decimal("10"), T0)
    with pytest.raises(ws.InvalidPriceError):
        s.add_item("c1", "p1", Decimal("0"), T0)


def test_spec01_clientes_independientes():
    s = _servicio(max_items=1)
    s.add_item("c1", "p1", Decimal("10"), T0)
    s.add_item("c2", "p1", Decimal("10"), T0)  # no es duplicado ni llena para otro cliente
    assert [i.product_id for i in s.list_items("c2")] == ["p1"]


# --- SPEC-02: eliminar ----------------------------------------------------------


def test_spec02_eliminar():
    s = _servicio()
    s.add_item("c1", "p1", Decimal("10"), T0)
    s.add_item("c1", "p2", Decimal("10"), T0)
    s.remove_item("c1", "p1")
    assert [i.product_id for i in s.list_items("c1")] == ["p2"]


def test_spec02_eliminar_inexistente():
    s = _servicio()
    s.add_item("c1", "p1", Decimal("10"), T0)
    with pytest.raises(ws.ItemNotFoundError):
        s.remove_item("c1", "p9")


def test_spec02_eliminar_cliente_sin_lista():
    with pytest.raises(ws.ItemNotFoundError):
        _servicio().remove_item("nadie", "p1")


def test_spec02_eliminar_libera_espacio():
    s = _servicio(max_items=1)
    s.add_item("c1", "p1", Decimal("10"), T0)
    s.remove_item("c1", "p1")
    s.add_item("c1", "p2", Decimal("10"), T0)
    assert [i.product_id for i in s.list_items("c1")] == ["p2"]


# --- SPEC-03: consultar ---------------------------------------------------------


def test_spec03_orden_por_fecha_ascendente():
    s = _servicio()
    s.add_item("c1", "tarde", Decimal("1"), T0 + timedelta(hours=2))
    s.add_item("c1", "temprano", Decimal("1"), T0)
    s.add_item("c1", "medio", Decimal("1"), T0 + timedelta(hours=1))
    assert [i.product_id for i in s.list_items("c1")] == ["temprano", "medio", "tarde"]


def test_spec03_empate_conserva_orden_de_insercion():
    s = _servicio()
    for p in ("b", "a", "c"):
        s.add_item("c1", p, Decimal("1"), T0)
    assert [i.product_id for i in s.list_items("c1")] == ["b", "a", "c"]


def test_spec03_cliente_sin_productos():
    assert _servicio().list_items("nadie") == []


def test_spec03_devuelve_una_copia():
    s = _servicio()
    s.add_item("c1", "p1", Decimal("1"), T0)
    s.list_items("c1").clear()
    assert len(s.list_items("c1")) == 1


# --- SPEC-04: bajas de precio ---------------------------------------------------


def _items(*pares):
    return [ws.WishlistItem(pid, T0, Decimal(precio)) for pid, precio in pares]


def test_spec04_calcula_y_redondea_half_up():
    # (3 - 2.9) / 3 * 100 = 3.3333... -> 3.33 ; (8 - 6.9) / 8 * 100 = 13.75
    bajas = ws.detect_price_drops(_items(("a", "3"), ("b", "8")), {"a": Decimal("2.9"), "b": Decimal("6.9")},
                                  Decimal("1"))
    assert bajas == [ws.PriceDrop("b", Decimal("8"), Decimal("6.9"), Decimal("13.75")),
                     ws.PriceDrop("a", Decimal("3"), Decimal("2.9"), Decimal("3.33"))]


def test_spec04_redondeo_half_up_en_el_limite():
    # (200 - 198.99) / 200 * 100 = 0.505 -> 0.51 con ROUND_HALF_UP (0.50 con redondeo bancario)
    bajas = ws.detect_price_drops(_items(("a", "200")), {"a": Decimal("198.99")}, Decimal("0.5"))
    assert bajas[0].drop_pct == Decimal("0.51")


def test_spec04_umbral_inclusivo():
    bajas = ws.detect_price_drops(_items(("a", "100")), {"a": Decimal("90")}, Decimal("10"))
    assert [b.product_id for b in bajas] == ["a"]


def test_spec04_bajo_el_umbral_o_sube_o_igual_no_se_incluye():
    items = _items(("baja_poco", "100"), ("sube", "100"), ("igual", "100"))
    precios = {"baja_poco": Decimal("95"), "sube": Decimal("120"), "igual": Decimal("100")}
    assert ws.detect_price_drops(items, precios, Decimal("10")) == []


def test_spec04_ignora_productos_sin_precio_actual():
    bajas = ws.detect_price_drops(_items(("a", "100"), ("b", "100")), {"a": Decimal("50")}, Decimal("1"))
    assert [b.product_id for b in bajas] == ["a"]


def test_spec04_orden_por_porcentaje_desc_y_luego_id():
    items = _items(("z", "100"), ("a", "100"), ("m", "100"))
    precios = {"z": Decimal("50"), "a": Decimal("50"), "m": Decimal("20")}
    assert [b.product_id for b in ws.detect_price_drops(items, precios, Decimal("1"))] == ["m", "a", "z"]


@pytest.mark.parametrize("umbral", [Decimal("0"), Decimal("-1"), Decimal("100.01")])
def test_spec04_umbral_invalido(umbral):
    with pytest.raises(ValueError):
        ws.detect_price_drops([], {}, umbral)


def test_spec04_umbral_100_es_valido():
    assert ws.detect_price_drops([], {}, Decimal("100")) == []
