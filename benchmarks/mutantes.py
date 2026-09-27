"""Los 12 errores sutiles (mutantes) de la implementación de referencia.

Cada uno es (texto a buscar, reemplazo) en benchmarks/referencia/wishlist_service.py.
Los usan el experimento que valida las pruebas ocultas (punto 6) y el sondeo
de la fase de Testing (punto 7) para medir el puntaje de mutación.
"""

MUTANTES = {
    "redondeo bancario (ROUND_HALF_EVEN)": ("rounding=ROUND_HALF_UP", "rounding=__import__('decimal').ROUND_HALF_EVEN"),
    "umbral exclusivo (>)": ("if pct >= min_drop_pct:", "if pct > min_drop_pct:"),
    "lista llena antes que duplicado": (
        "        if any(item.product_id == product_id for item in lista):\n            raise DuplicateItemError(product_id)\n        if len(lista) >= self._max_items:\n            raise WishlistFullError(customer_id)",
        "        if len(lista) >= self._max_items:\n            raise WishlistFullError(customer_id)\n        if any(item.product_id == product_id for item in lista):\n            raise DuplicateItemError(product_id)"),
    "devuelve la lista interna": ("return sorted(self._listas.get(customer_id, []), key=lambda item: item.added_at)",
                                  "lista = self._listas.get(customer_id, [])\n        lista.sort(key=lambda item: item.added_at)\n        return lista"),
    "orden descendente por fecha": ("key=lambda item: item.added_at)", "key=lambda item: item.added_at, reverse=True)"),
    "desempate por id descendente": ("key=lambda b: (-b.drop_pct, b.product_id)", "key=lambda b: (-b.drop_pct, [-ord(c) for c in b.product_id])"),
    "max_items por defecto 100": ("max_items: int = 50", "max_items: int = 100"),
    "no valida espacios en ids": ("not customer_id or not customer_id.strip() or not product_id or not product_id.strip()",
                                  "not customer_id or not product_id"),
    "umbral 100 invalido": ("min_drop_pct > 100", "min_drop_pct >= 100"),
    "eliminar inexistente silencioso": ("        raise ItemNotFoundError(product_id)", "        return None"),
    "precio cero permitido": ("if price <= 0:", "if price < 0:"),
    "sin redondeo": (".quantize(\n            Decimal(\"0.01\"), rounding=ROUND_HALF_UP\n        )", ""),
}
