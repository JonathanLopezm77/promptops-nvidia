"""¿Sirve openai/gpt-oss-20b como juez neutral (no compite en el benchmark)?

Evalúa con el Evaluador de requisitos de la plataforma (10 criterios) dos
listas de requisitos, una buena y una mala, 2 veces cada una, y compara con
nemotron-3-super (el Evaluador actual, que sí compite). Mide: JSON válido,
tiempo y si distingue la buena de la mala.
"""
import asyncio
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8")

from backend.config import get_settings  # noqa: E402
from backend.services.requirements_evaluator import evaluate_requirement  # noqa: E402

BUENA = """## Requisitos funcionales
RF-01: El sistema deberá permitir a un cliente registrado agregar un producto del catálogo a su lista de deseos.
Criterio de aceptación: Tras pulsar "Agregar a lista de deseos", el producto aparece en la lista del cliente y se muestra el mensaje "Producto agregado".
RF-02: El sistema deberá enviar un correo al cliente cuando el precio de un producto de su lista de deseos disminuya.
Criterio de aceptación: Al registrar un precio menor para un producto que está en la lista de un cliente, se envía un correo a ese cliente que incluye el precio anterior y el nuevo.

## Requisitos no funcionales
Sin elementos

## Información faltante
- ¿Cuál es el tiempo máximo aceptable entre el cambio de precio y el envío del aviso?
- ¿Cuántos productos como máximo puede tener la lista de deseos de un cliente?

## Aclaraciones sobre información ambigua
- ¿Los clientes invitados pueden usar la lista de deseos (sin sesión) o solo los registrados?"""

MALA = """Requisitos:
- El sistema debe gestionar la lista de deseos de forma rápida y fácil.
- El sistema debe avisar a los usuarios adecuadamente cuando haya ofertas, por correo, SMS y notificaciones push, en menos de 5 minutos y con un máximo de 100 productos."""

JUECES = ["openai/gpt-oss-20b", "nvidia/nemotron-3-super-120b-a12b"]
CONTEXTO = "Tienda en línea de artículos deportivos; ya envía correos transaccionales."


async def evaluar(juez, nombre, texto):
    t0 = time.perf_counter()
    try:
        r = await evaluate_requirement(texto, project_context=CONTEXTO, model=juez)
        e = r.evaluation
        return f"{juez:<36} {nombre:<5} OK    score={e.global_score():>3} {time.perf_counter() - t0:6.1f}s"
    except Exception as exc:  # noqa: BLE001
        return f"{juez:<36} {nombre:<5} FALLO {type(exc).__name__}: {str(exc)[:120]} {time.perf_counter() - t0:6.1f}s"


async def main():
    s = get_settings()
    s.json_mode_models = frozenset(JUECES)  # modo JSON para ambos jueces
    tareas = [evaluar(j, n, t) for j in JUECES for n, t in (("buena", BUENA), ("mala", MALA)) for _ in range(2)]
    for linea in await asyncio.gather(*tareas):
        print(linea, flush=True)


asyncio.run(main())
