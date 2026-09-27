"""Mismos pares (original, mejorado) de la corrida real, evaluados por
distintos modelos. ¿Cuál sigue la regla de los [POR DEFINIR] y da JSON válido?"""
import asyncio
import json
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from backend.config import get_settings  # noqa: E402
from backend.services import requirements_evaluator as ev  # noqa: E402

MODELOS = sys.argv[1:] or [
    "nvidia/nemotron-3.5-lightning-30b-a3b",
    "nvidia/nemotron-3-super-120b-a12b",
    "moonshotai/kimi-k3",
]
CORRIDAS = Path("evidence/punto3_casos_exploratorio/ejecucion_1_nemotron_lightning/corridas")
get_settings().llm_json_mode = True


def pares():
    for nombre in ("B_2", "B_3", "C_2"):
        a = json.loads((CORRIDAS / f"{nombre}.json").read_text(encoding="utf-8"))
        mejorado = next(e["evaluated_text"] for e in a["evaluations"] if e["stage"] == "improved")
        yield nombre, a, a["original_requirement"], mejorado


async def evaluar(modelo, nombre, a, etapa, texto):
    # Cada tarea usa su propio modelo: se fija justo antes de la llamada.
    t = time.perf_counter()
    try:
        r = await ev.evaluate_requirement(texto, project_context=a["project_context"], model=modelo)
        e = r.evaluation
        pd = next(t2 for t2 in e.ambiguous_terms if "POR DEFINIR" in t2.term.upper()) if any(
            "POR DEFINIR" in t2.term.upper() for t2 in e.ambiguous_terms) else None
        return (modelo, nombre, etapa, e.global_score(), round(time.perf_counter() - t), bool(pd),
                {c.criterion: c.score for c in e.criteria})
    except Exception as exc:  # noqa: BLE001
        return (modelo, nombre, etapa, None, round(time.perf_counter() - t), type(exc).__name__, str(exc)[:120])


async def main():
    tareas = []
    for modelo in MODELOS:
        for nombre, a, orig, mej in pares():
            tareas.append(evaluar(modelo, nombre, a, "original", orig))
            tareas.append(evaluar(modelo, nombre, a, "mejorado", mej))
    res = await asyncio.gather(*tareas)
    for modelo in MODELOS:
        print(f"\n### {modelo}")
        for nombre, *_ in pares():
            o = next(r for r in res if r[0] == modelo and r[1] == nombre and r[2] == "original")
            m = next(r for r in res if r[0] == modelo and r[1] == nombre and r[2] == "mejorado")
            if o[3] is None or m[3] is None:
                print(f"  {nombre}: FALLO orig={o[5:]} mej={m[5:]}")
                continue
            print(f"  {nombre}: {o[3]:>3} -> {m[3]:>3} (delta {m[3]-o[3]:+d})  tiempos {o[4]}s/{m[4]}s  "
                  f"marca POR DEFINIR como ambiguo: {m[5]}")
            print(f"        atom {o[6]['atomicidad']}->{m[6]['atomicidad']}  claridad {o[6]['claridad']}->{m[6]['claridad']}"
                  f"  ambig {o[6]['ausencia_ambiguedad']}->{m[6]['ausencia_ambiguedad']}"
                  f"  complet {o[6]['completitud']}->{m[6]['completitud']}  CA {o[6]['criterios_aceptacion']}->{m[6]['criterios_aceptacion']}"
                  f"  consist {o[6]['consistencia']}->{m[6]['consistencia']}")


asyncio.run(main())

