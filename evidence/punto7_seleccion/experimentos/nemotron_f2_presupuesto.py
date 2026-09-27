"""¿Nemotron falla la especificación (fase 2) por capacidad o por presupuesto?

En el sondeo, nemotron-3-super gastó los 8192 tokens de max_tokens razonando y
no entregó la especificación (f2_cloud_razonamiento, finish_reason='length').
Se repite la MISMA entrada y el MISMO prompt dos veces con max_tokens 16384
(el resto de los parámetros igual) y se califica con el mismo Quality Gate.
Es una variante: no reemplaza el resultado del sondeo, que usa los parámetros
constantes del benchmark.
"""
import asyncio
import json
import sys
from dataclasses import replace
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(RAIZ))
sys.stdout.reconfigure(encoding="utf-8")

import httpx  # noqa: E402
from dotenv import dotenv_values  # noqa: E402

from benchmarks.calificadores_sondeo import calificar_fase2  # noqa: E402
from benchmarks.proveedores import generar_con_reintentos  # noqa: E402
from scripts.benchmark import cargar_modelos  # noqa: E402
from scripts.sondeo_fases import cargar_caso, prompt_de  # noqa: E402

SALIDA = Path(__file__).with_name("nemotron_f2_presupuesto_ejecuciones")


async def main() -> None:
    env = dotenv_values(RAIZ / ".env")
    modelos, params, config = cargar_modelos()
    nemotron = next(m for m in modelos if m.clave == "cloud_razonamiento")
    params = replace(params, max_tokens=16384)
    SALIDA.mkdir(exist_ok=True)
    async with httpx.AsyncClient(timeout=1800) as c:
        for n in (1, 2):
            res = await generar_con_reintentos(
                nemotron, [{"role": "user", "content": prompt_de(2)}], params,
                max_intentos=config["reintentos"]["max_intentos"], client=c,
                nvidia_base_url=env["NVIDIA_BASE_URL"], nvidia_api_key=env["NVIDIA_API_KEY"])
            r = res.a_dict()
            solo_razon = bool(r["razonamiento"]) and r["contenido"].strip() == r["razonamiento"].strip()
            cal = calificar_fase2(r["contenido"], cargar_caso(2)["esperado"]) if res.ok and not solo_razon else None
            (SALIDA / f"f2_nemotron_16k_{n}.json").write_text(json.dumps(
                {"max_tokens": 16384, "resultado": r, "calificacion": cal}, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print(f"corrida {n}: finish={r['finish_reason']} tokens={r['tokens_entrada']}/{r['tokens_salida']} "
                  f"total={r['latencia_total_s']:.0f}s solo_razonamiento={solo_razon} "
                  f"puntaje={cal and cal['puntaje']} cumple={cal and cal['cumple_tarea']}", flush=True)
            if cal:
                print("   fallidos:", [k for k, v in cal["chequeos"].items() if not v], flush=True)


asyncio.run(main())
