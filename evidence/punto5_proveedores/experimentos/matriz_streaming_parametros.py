"""¿Qué provoca content vacío en kimi-k3: el streaming o los parámetros?
¿Cómo se comporta nemotron con y sin razonamiento? 3 repeticiones por celda."""
import asyncio
import json
import sys
import time

import httpx
from dotenv import dotenv_values

sys.stdout.reconfigure(encoding="utf-8")
env = dotenv_values(".env")
URL = f"{env['NVIDIA_BASE_URL']}/chat/completions"
H = {"Authorization": f"Bearer {env['NVIDIA_API_KEY']}"}
MSG = [{"role": "user", "content": "Devuelve solo un JSON con la clave 'saludo' y un saludo corto en español."}]
PARAMS = {"temperature": 0.2, "top_p": 0.95, "max_tokens": 1024}


async def llamar(c, modelo, stream, params, extra):
    body = {"model": modelo, "messages": MSG, **params, **extra}
    t0 = time.perf_counter()
    if not stream:
        r = await c.post(URL, json=body, headers=H)
        d = r.json()
        m = d["choices"][0]["message"]
        return (bool(m.get("content")), len(m.get("reasoning_content") or ""), round(time.perf_counter() - t0, 1))
    body.update({"stream": True, "stream_options": {"include_usage": True}})
    contenido, razon = "", 0
    async with c.stream("POST", URL, json=body, headers=H) as r:
        async for linea in r.aiter_lines():
            if not linea.startswith("data:") or linea[5:].strip() == "[DONE]":
                continue
            d = json.loads(linea[5:])
            for ch in d.get("choices", []):
                de = ch.get("delta", {})
                contenido += de.get("content") or ""
                razon += len(de.get("reasoning_content") or "")
    return (bool(contenido), razon, round(time.perf_counter() - t0, 1))


CELDAS = [
    ("moonshotai/kimi-k3", False, {}, {}),
    ("moonshotai/kimi-k3", False, PARAMS, {}),
    ("moonshotai/kimi-k3", True, {}, {}),
    ("moonshotai/kimi-k3", True, PARAMS, {}),
    ("moonshotai/kimi-k3", True, {**PARAMS, "seed": 1}, {}),
    ("nvidia/nemotron-3-super-120b-a12b", True, PARAMS, {}),
    ("nvidia/nemotron-3-super-120b-a12b", True, PARAMS, {"chat_template_kwargs": {"thinking": False}}),
    ("nvidia/nemotron-3-super-120b-a12b", True, PARAMS, {"chat_template_kwargs": {"enable_thinking": False}}),
]


async def main():
    async with httpx.AsyncClient(timeout=400) as c:
        for modelo, stream, params, extra in CELDAS:
            res = await asyncio.gather(*(llamar(c, modelo, stream, params, extra) for _ in range(3)),
                                       return_exceptions=True)
            etiqueta = f"{modelo.split('/')[1]:<24} stream={stream!s:<5} params={sorted(params)} extra={json.dumps(extra)}"
            print(etiqueta)
            for x in res:
                print("    ", x if isinstance(x, Exception) else f"contenido={x[0]} razonamiento={x[1]} chars {x[2]}s")


asyncio.run(main())
