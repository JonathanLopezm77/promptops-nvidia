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
sys.path.insert(0, str(RAIZ))
REFERENCIA = (RAIZ / "benchmarks" / "referencia" / "wishlist_service.py").read_text(encoding="utf-8")
SUITE = RAIZ / "benchmarks" / "pruebas_ocultas" / "test_wishlist_service.py"

from benchmarks.mutantes import MUTANTES  # noqa: E402


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
