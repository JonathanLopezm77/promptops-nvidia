"""Verificador de trazabilidad de la cadena SDD y generador de la matriz.

    python -m sdd.trazabilidad            # verifica y escribe specs/traceability_matrix.md
    python -m sdd.trazabilidad --sellar   # aprueba el código contra la especificación actual

Cadena: NEC → REQ → AC → SPEC → ARCH → CODE → TEST. Verifica que:

1. el requisito de specs/requirements.md es el origen declarado por la especificación;
2. cada ARCH del contrato existe en un módulo que lo declara (`# Implements:`) y
   ningún módulo declara un ARCH que el contrato no define;
3. el SPEC está cubierto por al menos un ARCH;
4. cada módulo lleva el SELLO con que fue aprobado
   (`# Spec: SPEC-XXX-NN vX.Y.Z huella H código C`): H es la huella de la
   especificación y C la del propio módulo, calculadas por la herramienta al
   sellar. Si la especificación cambió, o el código cambió después de la
   aprobación (incluido un modelo que reescribe su propio sello), el módulo queda
   no conforme hasta revisarlo y volver a sellarlo;
5. cada criterio de aceptación tiene al menos una prueba que lo declara, y
   ninguna prueba declara un criterio que la especificación no tiene;
6. los documentos generados desde la especificación no fueron editados a mano.

`tests/test_sdd_trazabilidad.py` ejecuta esta verificación dentro de pytest:
una ruptura de la cadena hace fallar la suite.
"""

import argparse
import ast
import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

from sdd.esquema import Especificacion, cargar, huella
from sdd.render import generar

RAIZ = Path(__file__).resolve().parent.parent
SPECS, SRC, TESTS = RAIZ / "specs", RAIZ / "src" / "auth_lockout", RAIZ / "tests" / "sdd"
_IMPLEMENTS = re.compile(r"^#\s*Implements:\s*(.+)$", re.MULTILINE)
_SELLO = re.compile(r"^#\s*Spec:\s*(SPEC-[A-Z]+-\d{2})\s+v(\d+\.\d+\.\d+)\s+huella\s+([0-9a-f]{12})"
                    r"(?:\s+c[oó]digo\s+([0-9a-f]{12}))?\s*$", re.MULTILINE)
_LINEA_SELLO = re.compile(r"^#\s*Spec:")
_ARCH_FILA = re.compile(r"^\|\s*(ARCH-\d{2})\s*\|[^|]*\|\s*`([^`]+\.py)`\s*\|[^|]*\|([^|]*)\|", re.MULTILINE)
_RB_RANGO = re.compile(r"RB-(\d+) a RB-(\d+)")
_RB = re.compile(r"RB-(\d+)")
_AC = re.compile(r"AC-[A-Z]+-\d{2}-\d{2}")


@dataclass
class Resultado:
    errores: list[str] = field(default_factory=list)
    arch_modulo: dict[str, str] = field(default_factory=dict)
    reglas_por_arch: dict[str, set[str]] = field(default_factory=dict)
    modulos_por_arch: dict[str, list[str]] = field(default_factory=dict)
    pruebas_por_ac: dict[str, list[str]] = field(default_factory=dict)


def _reglas(cubre: str) -> set[str]:
    """RB-x que cubre un ARCH según la columna "Cubre" del contrato ("RB-1 a RB-8", "RB-1, RB-7")."""
    reglas = {f"RB-{n}" for a, b in _RB_RANGO.findall(cubre) for n in range(int(a), int(b) + 1)}
    return reglas | {f"RB-{n}" for n in _RB.findall(_RB_RANGO.sub("", cubre))}


def _pruebas(carpeta: Path) -> dict[str, list[str]]:
    """{archivo::prueba: [AC que declara en su nombre, su docstring o los comentarios justo encima]}."""
    res = {}
    for archivo in sorted(carpeta.glob("test_*.py")):
        fuente = archivo.read_text(encoding="utf-8")
        lineas, arbol = fuente.splitlines(), ast.parse(fuente)
        for nodo in ast.walk(arbol):
            if isinstance(nodo, ast.FunctionDef) and nodo.name.startswith("test_"):
                inicio = min([nodo.lineno, *(d.lineno for d in nodo.decorator_list)]) - 1
                comentarios = []
                while inicio > 0 and lineas[inicio - 1].lstrip().startswith("#"):
                    inicio -= 1
                    comentarios.append(lineas[inicio])
                texto = f"{nodo.name} {ast.get_docstring(nodo) or ''} {' '.join(comentarios)}".replace("_", "-").upper()
                res[f"{archivo.name}::{nodo.name}"] = sorted(set(_AC.findall(texto)))
    return res


def verificar(raiz: Path = RAIZ) -> tuple[Especificacion, Resultado]:
    specs, src, tests = raiz / "specs", raiz / "src" / "auth_lockout", raiz / "tests" / "sdd"
    r = Resultado()
    ruta_spec = specs / "specification.json"
    spec, h = cargar(ruta_spec), huella(ruta_spec)

    if spec.requisito_origen not in (specs / "requirements.md").read_text(encoding="utf-8"):
        r.errores.append(f"requirements.md no contiene {spec.requisito_origen}")

    contrato = (specs / "architecture_contract.md").read_text(encoding="utf-8")
    filas = _ARCH_FILA.findall(contrato)
    r.arch_modulo = {a: m for a, m, _ in filas}
    r.reglas_por_arch = {a: _reglas(c) for a, _, c in filas}
    if not r.arch_modulo:
        r.errores.append("el contrato de arquitectura no define componentes ARCH")
    if spec.id not in contrato:
        r.errores.append(f"{spec.id} no está cubierto por ningún ARCH del contrato")

    declarados: dict[str, list[str]] = {}
    for modulo in sorted(src.glob("*.py")):
        texto = modulo.read_text(encoding="utf-8")
        nombre = modulo.relative_to(raiz).as_posix()
        m = _IMPLEMENTS.search(texto)
        ids = [x.strip() for x in m.group(1).split(",")] if m else []
        if not ids:
            r.errores.append(f"{nombre}: sin comentario '# Implements:'")
        for i in ids:
            if i.startswith("ARCH-"):
                declarados.setdefault(i, []).append(nombre)
                if i not in r.arch_modulo:
                    r.errores.append(f"{nombre} declara {i}, que el contrato no define")
            elif i != spec.id:
                r.errores.append(f"{nombre} declara {i}, que no es la especificación vigente ({spec.id})")
        sello = _SELLO.search(texto)
        if not sello:
            r.errores.append(f"{nombre}: sin sello de especificación ('# Spec: ...'); no fue aprobado contra la especificación")
        elif sello.groups()[:3] != (spec.id, spec.version, h):
            r.errores.append(f"{nombre}: aprobado contra {sello.group(1)} v{sello.group(2)} huella {sello.group(3)}, "
                             f"pero la especificación vigente es v{spec.version} huella {h}: revisar y volver a sellar")
        elif sello.group(4) != huella_codigo(texto, h):
            r.errores.append(f"{nombre}: el código cambió después de su aprobación (o el sello no lo emitió la "
                             "herramienta): revisar y volver a sellar")
    r.modulos_por_arch = declarados
    for arch, modulo in r.arch_modulo.items():
        if not (raiz / modulo).exists():
            r.errores.append(f"{arch}: el módulo {modulo} no existe")
        elif modulo not in declarados.get(arch, []):
            r.errores.append(f"{arch}: {modulo} no lo declara en '# Implements:'")

    pruebas = _pruebas(tests)
    ids_ac = [c.id for c in spec.criterios_aceptacion]
    r.pruebas_por_ac = {ac: [p for p, acs in pruebas.items() if ac in acs] for ac in ids_ac}
    for ac, ps in r.pruebas_por_ac.items():
        if not ps:
            r.errores.append(f"{ac}: ninguna prueba lo verifica")
    for p, acs in pruebas.items():
        for ac in set(acs) - set(ids_ac):
            r.errores.append(f"{p} declara {ac}, que la especificación no tiene")

    for nombre, texto in generar().items() if raiz == RAIZ else ():
        if (specs / nombre).read_text(encoding="utf-8") != texto:
            r.errores.append(f"specs/{nombre} no coincide con la especificación: ejecutar 'python -m sdd.render'")
    return spec, r


def matriz(spec: Especificacion, r: Resultado) -> str:
    reglas = {x.id: x for x in spec.reglas_negocio}
    filas = []
    for c in spec.criterios_aceptacion:
        cubren = [a for a, rbs in r.reglas_por_arch.items() if rbs & set(c.reglas)]
        archs = ", ".join(cubren) or "**ninguno**"
        codigo = ", ".join(f"`{r.arch_modulo[a].removeprefix('src/')}`" for a in cubren)
        filas.append(f"| {spec.requisito_origen} | {c.id} | {', '.join(c.reglas)} | {spec.id} | {archs} | {codigo} | "
                     + "<br>".join(r.pruebas_por_ac.get(c.id, [])) + " |")
    arch_filas = [f"| {a} | `{m}` | {'sí' if m in r.modulos_por_arch.get(a, []) else '**no**'} |"
                  for a, m in r.arch_modulo.items()]
    no_cubiertas = [x for x in reglas if not any(x in c.reglas for c in spec.criterios_aceptacion)]
    estado = "**CONFORME**" if not r.errores else f"**NO CONFORME** ({len(r.errores)} problemas)"
    return "\n".join([
        f"# Matriz de trazabilidad — {spec.requisito_origen} → {spec.id}\n",
        (f"> Generada por `python -m sdd.trazabilidad` (especificación v{spec.version}, "
         f"huella `{huella(SPECS / 'specification.json')}`). No editar a mano.\n"),
        f"Estado de la cadena: {estado}\n",
        f"Cadena: {spec.necesidad} → {spec.requisito_origen} → AC → {spec.id} → ARCH → CODE → TEST\n",
        "## Criterio de aceptación → prueba\n",
        "| REQ | AC | Reglas | SPEC | ARCH | Código | Pruebas |", "|---|---|---|---|---|---|---|", *filas,
        "\n## ARCH → código\n", "| ARCH | Módulo | Declara `Implements:` |", "|---|---|---|", *arch_filas,
        f"\nReglas sin criterio de aceptación: {', '.join(no_cubiertas) or 'ninguna'}.",
        *(["\n## Problemas\n", *[f"- {e}" for e in r.errores]] if r.errores else []), "",
    ])


def huella_codigo(texto: str, huella_spec: str) -> str:
    """Huella del módulo (sin su línea de sello) LIGADA a la huella de la especificación.

    Cambia si cambia el código o si cambia la especificación contra la que se
    aprueba. La calcula la herramienta al sellar: quien edite el sello a mano
    (visto en la demostración: el modelo de mantenimiento cambió la versión y la
    huella de la especificación en su propio sello) no la puede reproducir."""
    sin_sello = "\n".join(ln for ln in texto.replace("\r\n", "\n").split("\n") if not _LINEA_SELLO.match(ln))
    return hashlib.sha256(f"{huella_spec}\n{sin_sello}".encode()).hexdigest()[:12]


def sellar() -> None:
    """Acto de aprobación humana: sella cada módulo contra la especificación vigente
    y contra su propio contenido. Debe ejecutarse solo después de revisar el
    código y de que pasen las pruebas."""
    ruta = SPECS / "specification.json"
    spec, h = cargar(ruta), huella(ruta)
    for modulo in sorted(SRC.glob("*.py")):
        texto = modulo.read_text(encoding="utf-8")
        if not _SELLO.search(texto):
            texto = _IMPLEMENTS.sub(lambda m: m.group(0) + "\n# Spec: pendiente", texto, count=1)
        linea = f"# Spec: {spec.id} v{spec.version} huella {h} código {huella_codigo(texto, h)}"
        texto = re.sub(r"^# Spec: .*$", linea, texto, count=1, flags=re.MULTILINE)
        modulo.write_text(texto, encoding="utf-8")
        print(f"sellado {modulo.relative_to(RAIZ).as_posix()}: {linea}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sellar", action="store_true", help="aprobar el código contra la especificación vigente")
    if p.parse_args().sellar:
        sellar()
    spec, r = verificar()
    (SPECS / "traceability_matrix.md").write_text(matriz(spec, r), encoding="utf-8")
    for e in r.errores:
        print(f"  ✗ {e}")
    print(f"{'CONFORME' if not r.errores else 'NO CONFORME'}: {len(r.errores)} problemas "
          f"(matriz en specs/traceability_matrix.md)")
    sys.exit(1 if r.errores else 0)


if __name__ == "__main__":
    main()
