"""¿gpt-oss-20b responde a tiempo como juez si razona menos?

En el ensayo, juzgar los requisitos del modelo local agotó el tiempo con
HTTP 504 dos veces (606 s). Se prueba el mismo juicio con
reasoning_effort "low" y "medium" (2 llamadas cada uno) y se compara con el
comportamiento por defecto ya observado.
"""
import asyncio
import json
import os
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8")

from backend.config import get_settings  # noqa: E402
from backend.schemas.requirements import RequirementEvaluationResponse  # noqa: E402
from backend.services.json_extraction import extract_json_block  # noqa: E402
from backend.services.nvidia_client import chat_completion  # noqa: E402
from backend.services.prompts.requirements_evaluator_system_prompt import (  # noqa: E402
    REQUIREMENTS_EVALUATOR_SYSTEM_PROMPT,
)

ENSAYO = Path(os.environ["TEMP"]) / "ensayo_benchmark" / "ejecuciones" / "f1_local_1.json"
salida = json.loads(ENSAYO.read_text(encoding="utf-8"))["resultado"]["contenido"]
caso = json.loads((RAIZ / "benchmarks" / "casos" / "fase1_requisitos.json").read_text(encoding="utf-8"))["variables"]
contexto = f"{caso['NECESIDAD_DEL_STAKEHOLDER']}\n{caso['CONTEXTO_DEL_PROYECTO']}"
MENSAJES = [
    {"role": "system", "content": REQUIREMENTS_EVALUATOR_SYSTEM_PROMPT},
    {"role": "user", "content": f"REQUISITO A EVALUAR:\n{salida}\n\nCONTEXTO DEL PROYECTO:\n{contexto}"},
]


async def una(esfuerzo):
    t0 = time.perf_counter()
    try:
        r = await chat_completion("openai/gpt-oss-20b", MENSAJES, extra_payload={
            "reasoning_effort": esfuerzo, "response_format": {"type": "json_object"}})
        e = RequirementEvaluationResponse.model_validate_json(extract_json_block(r.content))
        return f"{esfuerzo:<7} OK    score={e.global_score():>3} {time.perf_counter() - t0:6.1f}s tokens={r.completion_tokens}"
    except Exception as exc:  # noqa: BLE001
        return f"{esfuerzo:<7} FALLO {type(exc).__name__}: {str(exc)[:100]} {time.perf_counter() - t0:6.1f}s"


async def main():
    s = get_settings()
    s.llm_timeout_seconds, s.llm_max_retries = 600, 0
    for linea in await asyncio.gather(*(una(e) for e in ("low", "low", "medium", "medium"))):
        print(linea, flush=True)


asyncio.run(main())
