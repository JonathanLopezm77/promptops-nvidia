"""¿Qué modelo cloud generalista responde de forma confiable, en streaming,
con un caso real del benchmark? Prompt aprobado de Requerimientos con una
necesidad concreta; 3 llamadas por configuración (en paralelo).

Motivo: en una matriz previa, moonshotai/kimi-k3 devolvió content vacío en
7 de 9 llamadas con streaming (y 1 de 6 sin streaming), y el TTFT exige
streaming.
"""
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
RAIZ = Path(__file__).resolve().parents[3]
env = dotenv_values(RAIZ / ".env")
URL = f"{env['NVIDIA_BASE_URL']}/chat/completions"
H = {"Authorization": f"Bearer {env['NVIDIA_API_KEY']}"}

plantilla = (RAIZ / "prompts" / "aprobados" / "1_requirements.txt").read_text(encoding="utf-8")
PROMPT = plantilla.replace(
    "{{NECESIDAD_DEL_STAKEHOLDER}}",
    "Los clientes de la tienda quieren poder guardar productos en una lista de deseos y recibir un aviso "
    "cuando alguno baje de precio.",
).replace(
    "{{CONTEXTO_DEL_PROYECTO}}",
    "Tienda en línea de artículos deportivos. Clientes registrados e invitados. Catálogo de 20000 productos.",
)
PARAMS = {"temperature": 0.2, "top_p": 0.95, "max_tokens": 4096}
CONFIGS = [
    ("moonshotai/kimi-k3", True),
    ("moonshotai/kimi-k3", False),
    ("openai/gpt-oss-20b", True),
    ("nvidia/nemotron-3.5-lightning-30b-a3b", True),
]


async def llamar(c, modelo, stream):
    body = {"model": modelo, "messages": [{"role": "user", "content": PROMPT}], **PARAMS}
    t0 = time.perf_counter()
    try:
        if not stream:
            r = await c.post(URL, json=body, headers=H)
            d = r.json()
            if not d.get("choices"):
                return f"FALLO HTTP {r.status_code} sin choices: {str(d)[:100]}"
            m = d["choices"][0]["message"]
            u = d.get("usage") or {}
            ok = bool(m.get("content"))
            return (f"{'OK   ' if ok else 'VACÍO'} total={time.perf_counter() - t0:5.1f}s ttft=n/d "
                    f"tokens={u.get('prompt_tokens')}/{u.get('completion_tokens')} chars={len(m.get('content') or '')}")
        body.update({"stream": True, "stream_options": {"include_usage": True}})
        contenido, ttft, ttft_c, usage = "", None, None, {}
        async with c.stream("POST", URL, json=body, headers=H) as r:
            async for linea in r.aiter_lines():
                if not linea.startswith("data:") or linea[5:].strip() == "[DONE]":
                    continue
                d = json.loads(linea[5:])
                usage = d.get("usage") or usage
                for ch in d.get("choices", []):
                    de = ch.get("delta", {})
                    if (de.get("content") or de.get("reasoning_content")) and ttft is None:
                        ttft = time.perf_counter() - t0
                    if de.get("content"):
                        if ttft_c is None:
                            ttft_c = time.perf_counter() - t0
                        contenido += de["content"]
        ok = bool(contenido)
        return (f"{'OK   ' if ok else 'VACÍO'} total={time.perf_counter() - t0:5.1f}s "
                f"ttft={ttft and round(ttft, 1)}s ttft_contenido={ttft_c and round(ttft_c, 1)}s "
                f"tokens={usage.get('prompt_tokens')}/{usage.get('completion_tokens')} chars={len(contenido)}")
    except Exception as e:  # noqa: BLE001
        return f"FALLO {type(e).__name__}: {str(e)[:100]} ({time.perf_counter() - t0:.0f}s)"


async def main():
    async with httpx.AsyncClient(timeout=600) as c:
        for modelo, stream in CONFIGS:
            res = await asyncio.gather(*(llamar(c, modelo, stream) for _ in range(3)))
            print(f"{modelo} stream={stream}", flush=True)
            for x in res:
                print("    ", x, flush=True)


asyncio.run(main())
