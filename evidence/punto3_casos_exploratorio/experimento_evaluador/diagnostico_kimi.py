"""Reproduce respuestas vacías de kimi-k3 con el prompt real del Mejorador."""
import asyncio
import json
import sys
import time

import httpx
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, ".")
from backend.services.prompts.requirements_improver_system_prompt import (  # noqa: E402
    REQUIREMENTS_IMPROVER_SYSTEM_PROMPT,
)

env = dotenv_values(".env")
MODELO = sys.argv[1] if len(sys.argv) > 1 else "moonshotai/kimi-k3"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 4
USER = (
    "REQUISITO ORIGINAL:\nEl sistema debe permitir a los clientes buscar productos de forma rápida y "
    "sencilla, mostrando resultados relevantes.\n\nDIAGNÓSTICO DEL EVALUADOR:\nDiagnóstico general: "
    "ambiguo y sin criterios de aceptación.\n- Claridad: 4/10. 'rápida', 'sencilla' y 'relevantes' son vagos.\n"
    "Términos ambiguos: 'rápida'; 'sencilla'; 'relevantes'\n\nCONTEXTO DEL PROYECTO:\nTienda en línea."
)


async def una(client, i):
    t = time.perf_counter()
    r = await client.post(
        f"{env['NVIDIA_BASE_URL']}/chat/completions",
        headers={"Authorization": f"Bearer {env['NVIDIA_API_KEY']}"},
        json={"model": MODELO, "messages": [
            {"role": "system", "content": REQUIREMENTS_IMPROVER_SYSTEM_PROMPT},
            {"role": "user", "content": USER}]},
    )
    seg = time.perf_counter() - t
    if r.status_code != 200:
        return f"#{i} HTTP {r.status_code} {seg:.0f}s {r.text[:150]}"
    body = r.json()
    ch = body["choices"][0]
    msg = ch.get("message") or {}
    content = msg.get("content") or ""
    razon = msg.get("reasoning_content") or msg.get("reasoning") or ""
    return (f"#{i} {seg:5.0f}s finish={ch.get('finish_reason')} content={len(content)} chars "
            f"reasoning={len(razon)} chars usage={json.dumps(body.get('usage'))} "
            f"claves_msg={sorted(msg.keys())}")


async def main():
    async with httpx.AsyncClient(timeout=400) as c:
        for linea in await asyncio.gather(*(una(c, i) for i in range(1, N + 1))):
            print(linea)


asyncio.run(main())
