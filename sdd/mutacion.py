"""Prueba de mutación para el Quality Gate de la fase de pruebas.

Genera mutantes del paquete src/auth_lockout (cada uno con UN cambio pequeño:
un operador de comparación distinto o una constante entera ±1) y corre las
pruebas indicadas contra cada mutante. Una suite que deja vivir muchos
mutantes no protege la especificación, aunque pase al 100 %.

    python -m sdd.mutacion tests/sdd/test_conformidad_spec.py [otra_suite.py ...]
"""

import ast
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAQUETE = RAIZ / "src" / "auth_lockout"
_CAMBIOS = {ast.Lt: ast.LtE, ast.LtE: ast.Lt, ast.Gt: ast.GtE, ast.GtE: ast.Gt, ast.Eq: ast.NotEq,
            ast.NotEq: ast.Eq, ast.Is: ast.IsNot, ast.IsNot: ast.Is}


@dataclass
class Mutante:
    archivo: str
    linea: int
    descripcion: str
    codigo: str


def generar(paquete: Path = PAQUETE) -> list[Mutante]:
    mutantes = []
    for archivo in sorted(paquete.glob("*.py")):
        fuente = archivo.read_text(encoding="utf-8")
        arbol = ast.parse(fuente)
        objetivos = [n for n in ast.walk(arbol)
                     if (isinstance(n, ast.Compare) and type(n.ops[0]) in _CAMBIOS)
                     or (isinstance(n, ast.Constant) and type(n.value) is int)]
        for k in range(len(objetivos)):
            copia = ast.parse(fuente)
            nodo = [n for n in ast.walk(copia)
                    if (isinstance(n, ast.Compare) and type(n.ops[0]) in _CAMBIOS)
                    or (isinstance(n, ast.Constant) and type(n.value) is int)][k]
            if isinstance(nodo, ast.Compare):
                antes = type(nodo.ops[0]).__name__
                nodo.ops[0] = _CAMBIOS[type(nodo.ops[0])]()
                desc = f"{antes} -> {type(nodo.ops[0]).__name__}"
            else:
                desc = f"{nodo.value} -> {nodo.value + 1}"
                nodo.value += 1
            mutantes.append(Mutante(archivo.name, nodo.lineno, desc, ast.unparse(copia)))
    return mutantes


def correr(mutantes: list[Mutante], suites: list[Path], paquete: Path = PAQUETE) -> dict[str, bool]:
    """{descripción del mutante: True si alguna prueba falló (mutante detectado)}."""
    resultado = {}
    for m in mutantes:
        with tempfile.TemporaryDirectory() as d:
            destino = Path(d) / "src" / "auth_lockout"
            shutil.copytree(paquete, destino)
            (destino / m.archivo).write_text(m.codigo, encoding="utf-8")
            (Path(d) / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            r = subprocess.run(
                [sys.executable, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider", "-c", str(Path(d) / "pytest.ini"),
                 "--rootdir", d, *map(str, suites)],
                cwd=d, capture_output=True, text=True, timeout=120, check=False,
                env={"PYTHONPATH": f"{Path(d) / 'src'};{RAIZ}", "SYSTEMROOT": "C:\\Windows", "PYTHONIOENCODING": "utf-8"})
            resultado[f"{m.archivo}:{m.linea} {m.descripcion}"] = r.returncode != 0
    return resultado


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    suites = [Path(a).resolve() for a in sys.argv[1:]]
    res = correr(generar(), suites)
    for nombre, muerto in res.items():
        print(f"  {'detectado ' if muerto else 'SOBREVIVE '} {nombre}")
    print(f"mutantes detectados: {sum(res.values())}/{len(res)}")


if __name__ == "__main__":
    main()
