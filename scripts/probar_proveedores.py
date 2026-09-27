"""Prueba de los proveedores del benchmark (Parcial 1, punto 5).

Verifica que los 3 modelos de benchmarks/modelos.json responden con los
parámetros comunes y registra, para cada ejecución: versión exacta del
modelo, TTFT, latencia, tokens, finish_reason y, para el modelo local,
tiempo de carga y recursos (RAM/CPU/VRAM/GPU).

Uso:  python scripts/probar_proveedores.py [--repeticiones 2] [--modelos local cloud_generalista]

Guarda todo en evidence/punto5_proveedores/prueba_<fecha>.json. No usa la
plataforma web: habla directo con Ollama y NVIDIA, como hará el benchmark.
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import psutil
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from benchmarks.proveedores import (  # noqa: E402
    ModeloBench, Parametros, calentar_ollama, generar_con_reintentos, modelo_cargado, version_modelo,
)

CONFIG = RAIZ / "benchmarks" / "modelos.json"
SALIDA = RAIZ / "evidence" / "punto5_proveedores"

# Tarea corta pero del mismo tipo que el benchmark: redactar requisitos a
# partir de una necesidad (fase 1), con formato de salida verificable.
TAREA = [
    {"role": "system", "content": "Eres un Ingeniero de Requisitos. Responde en español."},
    {"role": "user", "content": (
        "Necesidad del stakeholder: los clientes quieren guardar productos en una lista de deseos.\n"
        "Escribe exactamente 2 requisitos con la forma 'REQ-01: El sistema deberá ...', cada uno con "
        "un criterio de aceptación en la línea siguiente que empiece por 'Criterio:'. No agregues nada más."
    )},
]


def cargar_config() -> tuple[list[ModeloBench], Parametros, dict]:
    datos = json.loads(CONFIG.read_text(encoding="utf-8"))
    modelos = [ModeloBench(**m) for m in datos["modelos"]]
    return modelos, Parametros(**datos["parametros"]), datos


def contexto_maquina() -> dict:
    import platform
    import subprocess

    try:
        gpu = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used",
                              "--format=csv,noheader"], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:  # noqa: BLE001
        gpu = None
    return {
        "so": platform.platform(), "cpu": platform.processor(), "nucleos_logicos": psutil.cpu_count(),
        "ram_total_gb": round(psutil.virtual_memory().total / 2**30, 1),
        "ram_disponible_gb": round(psutil.virtual_memory().available / 2**30, 1),
        "gpu": gpu,
    }


async def main(repeticiones: int, solo: list[str] | None) -> None:
    env = dotenv_values(RAIZ / ".env")
    modelos, params, config = cargar_config()
    if solo:
        modelos = [m for m in modelos if m.clave in solo]
    registro = {
        "ejecutado_en": datetime.now(timezone.utc).isoformat(),
        "maquina_antes": contexto_maquina(),
        "parametros": config["parametros"], "nota_parametros": config.get("nota_parametros"),
        "tarea": TAREA, "modelos": [],
    }
    async with httpx.AsyncClient(timeout=900) as c:
        for m in modelos:
            entrada = {"config": m.__dict__, "version": await version_modelo(
                c, m, nvidia_base_url=env["NVIDIA_BASE_URL"]), "ejecuciones": []}
            if m.proveedor == "ollama":
                # Solo es una carga "en frío" si el modelo no estaba ya en
                # memoria (keep_alive lo mantiene entre ejecuciones).
                entrada["modelo_ya_cargado_antes_de_calentar"] = await modelo_cargado(c, m)
                entrada["carga_al_calentar_s"] = await calentar_ollama(c, m)
            for i in range(1, repeticiones + 1):
                res = await generar_con_reintentos(
                    m, TAREA, params, max_intentos=config["reintentos"]["max_intentos"], client=c,
                    nvidia_base_url=env["NVIDIA_BASE_URL"], nvidia_api_key=env["NVIDIA_API_KEY"],
                )
                entrada["ejecuciones"].append(res.a_dict())
                r = res.recursos or {}
                print(f"{m.clave:<20} #{i} {'OK   ' if res.ok else 'FALLO'} "
                      f"ttft={_f(res.ttft_s)} ttft_resp={_f(res.ttft_contenido_s)} total={_f(res.latencia_total_s)} "
                      f"tokens={res.tokens_entrada}/{res.tokens_salida} razon={res.tokens_razonamiento} "
                      f"fin={res.finish_reason} intentos={res.intentos}"
                      + (f" vram_modelo={(r.get('modelos_cargados_ollama') or [{}])[0].get('vram_mb', 0):.0f}MB "
                         f"ram_max={(r.get('ram_proceso_mb') or {}).get('max')}MB" if r else "")
                      + (f" ERROR={res.error}" if res.error else ""), flush=True)
            registro["modelos"].append(entrada)
    registro["maquina_despues"] = contexto_maquina()
    SALIDA.mkdir(parents=True, exist_ok=True)
    archivo = SALIDA / f"prueba_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    archivo.write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Guardado {archivo.relative_to(RAIZ)}")


def _f(x):
    return f"{x:.1f}s" if x is not None else "—"


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--repeticiones", type=int, default=2)
    ap.add_argument("--modelos", nargs="*")
    a = ap.parse_args()
    asyncio.run(main(a.repeticiones, a.modelos))
