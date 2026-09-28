"""Aplica los diffs que propone un modelo (fase de Mantenimiento) a una copia del código.

Los modelos no siempre entregan un diff unificado exacto: omiten los números de
línea de `@@`, mezclan varios archivos en un bloque o incluyen el archivo entero
con líneas de contexto sin prefijo. Por eso cada hunk se aplica por contenido:
se reconstruye el texto "antes" (contexto + líneas `-`) y el texto "después"
(contexto + líneas `+`), y se reemplaza el primero por el segundo si aparece
tal cual y UNA sola vez en el archivo. Si no, se reintenta cada grupo de cambios con menos
contexto; si sigue sin calzar o es ambiguo, el hunk NO se aplica (no se adivina).
"""

import re
from pathlib import Path

_BLOQUE_DIFF = re.compile(r"```diff\n(.*?)```", re.DOTALL)


def _secciones(bloque: str) -> list[tuple[str | None, str]]:
    """(archivo declarado o None, cuerpo) de cada archivo dentro de un bloque diff."""
    partes = re.split(r"(?m)^(?=--- )", bloque)
    res = []
    for parte in partes:
        if not parte.strip():
            continue
        archivo = re.search(r"^\+\+\+ (?:b/)?(\S+)", parte, re.MULTILINE) or \
            re.search(r"^[ +-]?#\s*File:\s*(\S+)", parte, re.MULTILINE)
        cuerpo = "\n".join(ln for ln in parte.splitlines() if not ln.startswith(("--- ", "+++ ")))
        res.append((archivo.group(1) if archivo else None, cuerpo))
    return res


def _antes_despues(lineas: list[str]) -> tuple[str, str]:
    antes = [ln[1:] if ln.startswith((" ", "-")) else ln for ln in lineas if not ln.startswith("+")]
    despues = [ln[1:] if ln.startswith((" ", "+")) else ln for ln in lineas if not ln.startswith("-")]
    return "\n".join(antes), "\n".join(despues)


def _hunks(cuerpo: str) -> list[list[str]]:
    """Líneas de cada hunk con al menos un cambio. Una línea sin prefijo cuenta como contexto."""
    res = []
    for hunk in re.split(r"(?m)^@@.*$", cuerpo):
        lineas = hunk.split("\n")
        while lineas and not lineas[0].strip():
            lineas.pop(0)
        while lineas and not lineas[-1].strip():
            lineas.pop()
        if any(ln.startswith(("+", "-")) for ln in lineas):
            res.append(lineas)
    return res


def _grupos(lineas: list[str], contexto: int) -> list[list[str]]:
    """Cada grupo contiguo de líneas +/- con `contexto` líneas alrededor (fuzz)."""
    cambios = [i for i, ln in enumerate(lineas) if ln.startswith(("+", "-"))]
    grupos, inicio = [], None
    for k, i in enumerate(cambios):
        inicio = i if inicio is None else inicio
        if k + 1 == len(cambios) or cambios[k + 1] != i + 1:
            grupos.append(lineas[max(0, inicio - contexto): i + 1 + contexto])
            inicio = None
    return grupos


def _aplicar_hunk(texto: str, lineas: list[str]) -> str | None:
    """Aplica el hunk completo; si no calza, cada grupo de cambios con cada vez menos
    contexto (3, 2, 1, 0 líneas), exigiendo que el texto a reemplazar sea ÚNICO."""
    antes, despues = _antes_despues(lineas)
    if antes.strip() and texto.count(antes) == 1:
        return texto.replace(antes, despues, 1)
    nuevo = texto
    for grupo in _grupos(lineas, 3):
        for contexto in (3, 2, 1, 0):
            recorte = next(g for g in _grupos(grupo, contexto))
            antes, despues = _antes_despues(recorte)
            if antes.strip() and nuevo.count(antes) == 1:
                nuevo = nuevo.replace(antes, despues, 1)
                break
        else:
            return None
    return nuevo


def aplicar(salida: str, carpeta: Path) -> dict[str, list[str]]:
    """Aplica los diffs de `salida` a los .py de `carpeta`.
    Devuelve {"aplicados": [archivo:hunk], "no_aplicados": [archivo:hunk]}."""
    modulos = {p.name: p for p in carpeta.glob("*.py")}
    informe: dict[str, list[str]] = {"aplicados": [], "no_aplicados": []}
    for bloque in _BLOQUE_DIFF.findall(salida):
        for archivo, cuerpo in _secciones(bloque):
            destino = modulos.get(Path(archivo).name) if archivo else None
            for k, lineas in enumerate(_hunks(cuerpo), start=1):
                etiqueta = f"{Path(archivo).name if archivo else '?'}:{k}"
                nuevo = _aplicar_hunk(destino.read_text(encoding="utf-8"), lineas) if destino else None
                if nuevo is None:
                    informe["no_aplicados"].append(etiqueta)
                else:
                    destino.write_text(nuevo, encoding="utf-8")
                    informe["aplicados"].append(etiqueta)
    return informe
