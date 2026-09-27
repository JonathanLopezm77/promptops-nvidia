# File: wishlist_service.py
# Implements: ARCH-01, ARCH-02, SPEC-01, SPEC-02, SPEC-03, SPEC-04
"""Lista de deseos en memoria y detección de bajas de precio."""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal


class WishlistError(Exception):
    """Base de los errores del módulo."""


class DuplicateItemError(WishlistError):
    """El producto ya está en la lista del cliente."""


class WishlistFullError(WishlistError):
    """La lista del cliente ya tiene max_items productos."""


class ItemNotFoundError(WishlistError):
    """El producto no está en la lista del cliente."""


class InvalidPriceError(WishlistError):
    """Precio menor o igual a cero."""


@dataclass(frozen=True)
class WishlistItem:
    product_id: str
    added_at: datetime
    price_at_add: Decimal


@dataclass(frozen=True)
class PriceDrop:
    product_id: str
    old_price: Decimal
    new_price: Decimal
    drop_pct: Decimal


class WishlistService:
    def __init__(self, max_items: int = 50) -> None:
        if max_items < 1:
            raise ValueError("max_items debe ser >= 1")
        self._max_items = max_items
        self._listas: dict[str, list[WishlistItem]] = {}

    def add_item(self, customer_id: str, product_id: str, price: Decimal, now: datetime) -> WishlistItem:
        if not customer_id or not customer_id.strip() or not product_id or not product_id.strip():
            raise ValueError("customer_id y product_id son obligatorios")
        if price <= 0:
            raise InvalidPriceError("el precio debe ser mayor que cero")
        lista = self._listas.setdefault(customer_id, [])
        if any(item.product_id == product_id for item in lista):
            raise DuplicateItemError(product_id)
        if len(lista) >= self._max_items:
            raise WishlistFullError(customer_id)
        item = WishlistItem(product_id=product_id, added_at=now, price_at_add=price)
        lista.append(item)
        return item

    def remove_item(self, customer_id: str, product_id: str) -> None:
        lista = self._listas.get(customer_id, [])
        for i, item in enumerate(lista):
            if item.product_id == product_id:
                del lista[i]
                return
        raise ItemNotFoundError(product_id)

    def list_items(self, customer_id: str) -> list[WishlistItem]:
        # La lista interna conserva el orden de inserción, que coincide con el orden por fecha.
        return list(self._listas.get(customer_id, []))


def detect_price_drops(
    items: list[WishlistItem], current_prices: dict[str, Decimal], min_drop_pct: Decimal
) -> list[PriceDrop]:
    if min_drop_pct <= 0 or min_drop_pct > 100:
        raise ValueError("min_drop_pct debe estar en (0, 100]")
    bajas = []
    for item in items:
        actual = current_prices.get(item.product_id)
        if actual is None or actual >= item.price_at_add:
            continue
        pct = ((item.price_at_add - actual) / item.price_at_add * 100).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        if pct >= min_drop_pct:
            bajas.append(PriceDrop(item.product_id, item.price_at_add, actual, pct))
    return sorted(bajas, key=lambda b: (-b.drop_pct, b.product_id))
