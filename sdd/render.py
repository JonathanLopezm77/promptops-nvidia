"""Genera los documentos legibles de la especificación a partir de
specs/specification.json (la única fuente): specification.md,
acceptance_criteria.md y acceptance/<REQ>.feature. No se editan a mano:

    python -m sdd.render
"""

from pathlib import Path

from sdd.esquema import Especificacion, cargar, huella

RAIZ = Path(__file__).resolve().parent.parent
SPECS = RAIZ / "specs"
AVISO = ("> Generado por `python -m sdd.render` desde `specs/specification.json` "
         "(huella `{h}`). No editar a mano: se cambia la especificación y se regenera.\n")


def _tabla(filas: list[list[str]], encabezado: list[str]) -> str:
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "---|" * len(encabezado)]
    lineas += ["| " + " | ".join(c.replace("|", "\\|").replace("\n", " ") for c in f) + " |" for f in filas]
    return "\n".join(lineas)


def especificacion_md(e: Especificacion, h: str) -> str:
    p = e.parametros
    partes = [
        f"# {e.id} — Especificación (contrato del desarrollo)\n", AVISO.format(h=h),
        f"- **Versión:** {e.version} · **Estado:** {e.estado}",
        f"- **Trazabilidad:** {e.necesidad} → {e.requisito_origen} → {e.id}",
        f"- **Alcance:** {e.alcance}\n",
        f"## Descripción\n\n{e.descripcion}\n",
        "## Parámetros de la política\n",
        _tabla([["max_intentos_fallidos", str(p.max_intentos_fallidos), "intentos fallidos consecutivos que bloquean"],
                ["ventana_minutos", str(p.ventana_minutos), "periodo en que deben ocurrir"],
                ["bloqueo_minutos", str(p.bloqueo_minutos), "duración del bloqueo"]],
               ["Parámetro", "Valor", "Significado"]),
        "\n## Entradas\n", _tabla([[c.nombre, c.tipo, c.validaciones] for c in e.entradas], ["Nombre", "Tipo", "Validaciones"]),
        "\n## Salidas\n", _tabla([[c.nombre, c.tipo] for c in e.salidas], ["Nombre", "Tipo"]),
        "\n## Reglas de negocio\n", _tabla([[r.id, r.texto, r.origen] for r in e.reglas_negocio], ["ID", "Regla", "Origen"]),
        "\n## Criterios de aceptación\n",
        _tabla([[c.id, f"**Dado** {c.gherkin.dado}, **cuando** {c.gherkin.cuando}, **entonces** {c.gherkin.entonces}.",
                 ", ".join(c.reglas)] for c in e.criterios_aceptacion], ["ID", "Criterio", "Verifica"]),
        "\n## Decisiones de la revisión (supuestos resueltos)\n",
        _tabla([[d.id, d.tema, d.decision, d.fundamento] for d in e.decisiones], ["ID", "Tema", "Decisión", "Fundamento"]),
        "\n## Alertas\n", _tabla([[a.tipo, a.descripcion, a.tratamiento] for a in e.alertas], ["Tipo", "Descripción", "Tratamiento"]),
    ]
    return "\n".join(partes) + "\n"


def criterios_md(e: Especificacion, h: str) -> str:
    partes = [f"# Criterios de aceptación — {e.requisito_origen} / {e.id}\n", AVISO.format(h=h),
              (f"Formato Gherkin ejecutable: `specs/acceptance/{e.requisito_origen}.feature`. Cada criterio "
               "tiene al menos una prueba que lo declara (`specs/traceability_matrix.md`).\n")]
    for c in e.criterios_aceptacion:
        partes.append(f"## {c.id}\n\n- **Origen:** {c.origen}\n- **Verifica:** {', '.join(c.reglas)}\n\n"
                      f"```gherkin\nDado {c.gherkin.dado}\nCuando {c.gherkin.cuando}\nEntonces {c.gherkin.entonces}\n```\n")
    return "\n".join(partes)


def feature(e: Especificacion, h: str) -> str:
    lineas = ["# language: es", f"# Generado desde specs/specification.json (huella {h}). No editar a mano.",
              f"Característica: {e.id} — bloqueo temporal de cuenta ({e.requisito_origen})", ""]
    for c in e.criterios_aceptacion:
        lineas += [f"  @{c.id} " + " ".join(f"@{r}" for r in c.reglas), f"  Escenario: {c.id}",
                   f"    Dado {c.gherkin.dado}", f"    Cuando {c.gherkin.cuando}", f"    Entonces {c.gherkin.entonces}", ""]
    return "\n".join(lineas)


def generar() -> dict[str, str]:
    ruta = SPECS / "specification.json"
    e, h = cargar(ruta), huella(ruta)
    return {"specification.md": especificacion_md(e, h), "acceptance_criteria.md": criterios_md(e, h),
            f"acceptance/{e.requisito_origen}.feature": feature(e, h)}


def main() -> None:
    for nombre, texto in generar().items():
        destino = SPECS / nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(texto, encoding="utf-8")
        print(f"generado specs/{nombre}")


if __name__ == "__main__":
    main()
