"""¿Las pruebas ocultas de la fase 4 detectan implementaciones incorrectas?

Aplica a la implementación de referencia un error sutil por vez (mutante) y
ejecuta la suite oculta contra cada uno. Un mutante "sobrevive" si todas las
pruebas pasan: significaría que la suite no distingue ese error.
"""
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
REFERENCIA = (RAIZ / "benchmarks" / "referencia" / "wishlist_service.py").read_text(encoding="utf-8")
SUITE = RAIZ / "benchmarks" / "pruebas_ocultas" / "test_wishlist_service.py"

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


def correr(codigo: str) -> tuple[int, str]:
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "wishlist_service.py").write_text(codigo, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--rootdir", d, str(SUITE)],
            cwd=d, capture_output=True, text=True, env={"PYTHONPATH": d, "SYSTEMROOT": "C:\\Windows"},
        )
        return r.returncode, r.stdout.strip().splitlines()[-1] if r.stdout.strip() else r.stderr[-200:]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    codigo, resumen = correr(REFERENCIA)
    print(f"referencia: {resumen}")
    sobreviven = 0
    for nombre, (buscar, reemplazo) in MUTANTES.items():
        assert buscar in REFERENCIA, f"el mutante '{nombre}' no encontró su texto"
        codigo, resumen = correr(REFERENCIA.replace(buscar, reemplazo))
        estado = "DETECTADO" if codigo != 0 else "SOBREVIVE"
        sobreviven += codigo == 0
        print(f"  {estado:<10} {nombre:<38} {resumen}")
    print(f"mutantes detectados: {len(MUTANTES) - sobreviven}/{len(MUTANTES)}")


main()
