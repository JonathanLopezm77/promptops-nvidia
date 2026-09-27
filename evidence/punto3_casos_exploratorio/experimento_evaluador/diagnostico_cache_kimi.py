"""¿La respuesta degenerada de kimi-k3 ("!!!!" y content vacío) se repite
con la misma petición (caché de prefijo de NVIDIA) y desaparece si la
petición cambia mínimamente?

Reconstruye la petición exacta del Mejorador para un análisis que falló y
la envía N veces idéntica y N veces con un sufijo distinto por intento.

Uso: python .../diagnostico_cache_kimi.py <analysis_id> [N]
"""
import asyncio
import sys
import time

import httpx
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from backend.schemas.requirements import RequirementEvaluationResponse  # noqa: E402
from backend.services.prompts.requirements_improver_system_prompt import (  # noqa: E402
    REQUIREMENTS_IMPROVER_SYSTEM_PROMPT,
)
from backend.services.requirements_improver import _build_user_message  # noqa: E402

env = dotenv_values(".env")
ANALYSIS_ID = sys.argv[1]
N = int(sys.argv[2]) if len(sys.argv) > 2 else 3

a = httpx.get(f"http://localhost:8000/api/requirements/{ANALYSIS_ID}", timeout=30).json()
ev = next(e for e in a["evaluations"] if e["stage"] == "original" and e["parse_ok"])
evaluation = RequirementEvaluationResponse.model_validate(
    {k: ev[k] for k in ("criteria", "ambiguous_terms", "is_compound", "missing_information",
                        "clarification_questions", "summary")}
)
USER = _build_user_message(a["original_requirement"], evaluation, a["project_context"], a["clarifications"])


async def llamar(client, etiqueta, user):
    t = time.perf_counter()
    r = await client.post(
        f"{env['NVIDIA_BASE_URL']}/chat/completions",
        headers={"Authorization": f"Bearer {env['NVIDIA_API_KEY']}"},
        json={"model": "moonshotai/kimi-k3", "messages": [
            {"role": "system", "content": REQUIREMENTS_IMPROVER_SYSTEM_PROMPT},
            {"role": "user", "content": user}]},
    )
    b = r.json()
    ch = b["choices"][0]
    m = ch["message"]
    u = b.get("usage") or {}
    cache = (u.get("prompt_tokens_details") or {}).get("cached_tokens")
    return (f"{etiqueta:<12} {time.perf_counter() - t:5.0f}s content={len(m.get('content') or '')} chars "
            f"reasoning={(m.get('reasoning_content') or '')[:20]!r} cached={cache}/{u.get('prompt_tokens')}")


async def main():
    async with httpx.AsyncClient(timeout=400) as c:
        for i in range(1, N + 1):  # secuencial: la caché se forma con la llamada anterior
            print(await llamar(c, f"idéntica #{i}", USER), flush=True)
        for i in range(1, N + 1):
            print(await llamar(c, f"variada #{i}", f"{USER}\n\n(Intento {i}.)"), flush=True)


asyncio.run(main())
