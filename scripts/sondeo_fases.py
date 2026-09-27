"""Sondeo de las fases 2, 5, 6 y 7 (punto 7): 1 corrida por modelo y fase.

    python scripts/sondeo_fases.py ejecutar    # 12 ejecuciones (reanudable)
    python scripts/sondeo_fases.py calificar   # Quality Gate de cada fase
    python scripts/sondeo_fases.py informe     # evidence/punto7_seleccion/sondeo/sondeo.csv

NO forma parte de las 27 ejecuciones del benchmark (el enunciado no exige
corridas en estas fases). Mismos modelos, parámetros y política de reintentos
que el benchmark (benchmarks/modelos.json) y los prompts aprobados del punto 4.
Casos: benchmarks/casos_sondeo/. Calificadores: benchmarks/calificadores_sondeo.py.
"""

import argparse
import asyncio
import csv
import json
import random
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from benchmarks.proveedores import (
    calentar_ollama,
    generar_con_reintentos,
    version_modelo,
)
from scripts.benchmark import cargar_modelos
from scripts.probar_proveedores import contexto_maquina

CASOS = RAIZ / "benchmarks" / "casos_sondeo"
FASES = {2: "fase2_especificacion.json", 5: "fase5_testing.json", 6: "fase6_deployment.json",
         7: "fase7_mantenimiento.json"}
SALIDA = RAIZ / "evidence" / "punto7_seleccion" / "sondeo"
DIR_EJ, DIR_CAL = SALIDA / "ejecuciones", SALIDA / "calificaciones"
SEMILLA = 20260928


def cargar_caso(fase: int) -> dict:
    return json.loads((CASOS / FASES[fase]).read_text(encoding="utf-8"))


def valor(v: str) -> str:
    """Las variables que empiezan con @ son rutas a un archivo del repositorio."""
    return (RAIZ / v[1:]).read_text(encoding="utf-8") if v.startswith("@") else v


def prompt_de(fase: int) -> str:
    caso = cargar_caso(fase)
    texto = (RAIZ / caso["prompt"]).read_text(encoding="utf-8")
    for nombre, v in caso["variables"].items():
        texto = texto.replace("{{" + nombre + "}}", valor(v))
    restantes = re.findall(r"\{\{\s*[A-Z_]+\s*\}\}", texto)
    # El prompt de Deployment trae ${{ github.sha }} en su ejemplo: no es una variable de plantilla.
    if restantes:
        raise ValueError(f"fase {fase}: quedaron variables sin sustituir: {restantes}")
    return texto


def plan() -> list[tuple[int, str]]:
    modelos, _, _ = cargar_modelos()
    combinaciones = [(f, m.clave) for f in FASES for m in modelos]
    random.Random(SEMILLA).shuffle(combinaciones)
    return combinaciones


async def ejecutar() -> None:
    env = dotenv_values(RAIZ / ".env")
    modelos, params, config = cargar_modelos()
    por_clave = {m.clave: m for m in modelos}
    DIR_EJ.mkdir(parents=True, exist_ok=True)
    pendientes = [p for p in plan() if not (DIR_EJ / f"f{p[0]}_{p[1]}.json").exists()]
    print(f"{len(pendientes)} de {len(plan())} ejecuciones pendientes", flush=True)
    if not pendientes:
        return
    async with httpx.AsyncClient(timeout=1800) as c:
        manifiesto = {
            "inicio_utc": datetime.now(UTC).isoformat(), "maquina": contexto_maquina(),
            "versiones": {m.clave: await version_modelo(c, m, nvidia_base_url=env["NVIDIA_BASE_URL"]) for m in modelos},
            "parametros": config["parametros"], "reintentos": config["reintentos"], "semilla_orden": SEMILLA,
            "orden": [f"f{f}_{k}" for f, k in plan()],
        }
        local = next((m for m in modelos if m.proveedor == "ollama"), None)
        if local:
            manifiesto["local_carga_al_calentar_s"] = await calentar_ollama(c, local)
        prompts = {f: prompt_de(f) for f in FASES}
        for fase, clave in pendientes:
            t0 = time.perf_counter()
            res = await generar_con_reintentos(
                por_clave[clave], [{"role": "user", "content": prompts[fase]}], params,
                max_intentos=config["reintentos"]["max_intentos"], client=c,
                nvidia_base_url=env["NVIDIA_BASE_URL"], nvidia_api_key=env["NVIDIA_API_KEY"],
            )
            registro = {"id": f"f{fase}_{clave}", "fase": fase, "modelo_clave": clave,
                        "modelo": por_clave[clave].__dict__, "parametros": config["parametros"],
                        "prompt_enviado": prompts[fase], "resultado": res.a_dict()}
            (DIR_EJ / f"{registro['id']}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2),
                                                         encoding="utf-8")
            print(f"{registro['id']:<26} {'OK   ' if res.ok else 'FALLO'} total={res.latencia_total_s:.0f}s "
                  f"tokens={res.tokens_entrada}/{res.tokens_salida} intentos={res.intentos} "
                  f"({time.perf_counter() - t0:.0f}s){' ERROR=' + res.error if res.error else ''}", flush=True)
        manifiesto["fin_utc"] = datetime.now(UTC).isoformat()
        (SALIDA / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")


def calificar() -> None:
    from benchmarks.calificadores_sondeo import (
        calificar_fase2,
        calificar_fase5,
        calificar_fase6,
        calificar_fase7,
    )

    DIR_CAL.mkdir(parents=True, exist_ok=True)
    for archivo in sorted(DIR_EJ.glob("*.json")):
        ej = json.loads(archivo.read_text(encoding="utf-8"))
        caso = cargar_caso(ej["fase"])
        r = ej["resultado"]
        salida = r["contenido"] or ""
        # Si el modelo agota max_tokens razonando, el servidor de NVIDIA devuelve el
        # razonamiento como respuesta: no hay entregable (visto en f2_cloud_razonamiento).
        solo_razonamiento = bool(r["razonamiento"]) and salida.strip() == r["razonamiento"].strip()
        if not r["ok"] or solo_razonamiento:
            motivo = (f"agotó max_tokens razonando (finish_reason={r['finish_reason']!r}): la respuesta es su "
                      "razonamiento, no el entregable") if solo_razonamiento else f"la ejecución falló: {r['error']}"
            cal = {"puntaje": 0.0, "cumple_tarea": False, "schema_ok": False, "detalle": {"error": motivo}}
        elif ej["fase"] == 2:
            cal = calificar_fase2(salida, caso["esperado"])
        elif ej["fase"] == 5:
            cal = calificar_fase5(salida, caso["esperado"])
        elif ej["fase"] == 6:
            cal = calificar_fase6(salida, caso["esperado"])
        else:
            cal = calificar_fase7(salida, valor(caso["variables"]["CODIGO_ACTUAL"]), caso["esperado"])
        cal = {"id": ej["id"], "fase": ej["fase"], "modelo_clave": ej["modelo_clave"],
               "calificado_en": datetime.now(UTC).isoformat(), **cal}
        (DIR_CAL / archivo.name).write_text(json.dumps(cal, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"calificado {ej['id']:<26} puntaje={cal['puntaje']:>6} cumple={cal['cumple_tarea']}", flush=True)


def informe() -> None:
    filas = []
    for archivo in sorted(DIR_EJ.glob("*.json")):
        ej = json.loads(archivo.read_text(encoding="utf-8"))
        cal_archivo = DIR_CAL / archivo.name
        cal = json.loads(cal_archivo.read_text(encoding="utf-8")) if cal_archivo.exists() else {}
        r = ej["resultado"]
        filas.append({
            "id": ej["id"], "fase": ej["fase"], "modelo_clave": ej["modelo_clave"], "modelo": ej["modelo"]["modelo"],
            "inicio_utc": r["inicio_utc"], "ejecucion_ok": r["ok"], "intentos": r["intentos"],
            "finish_reason": r["finish_reason"], "ttft_respuesta_s": r["ttft_contenido_s"],
            "latencia_total_s": r["latencia_total_s"], "duracion_con_reintentos_s": r["duracion_con_reintentos_s"],
            "tokens_entrada": r["tokens_entrada"], "tokens_salida": r["tokens_salida"], "costo_usd": 0.0,
            "quality_gate_score": cal.get("puntaje"), "cumple_tarea": cal.get("cumple_tarea"),
            "schema_ok": cal.get("schema_ok"),
            "chequeos_fallidos": " | ".join(k for k, v in (cal.get("chequeos") or {}).items() if not v),
            "componentes": json.dumps(cal.get("componentes") or {}, ensure_ascii=False),
        })
    with (SALIDA / "sondeo.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)
    print(f"Generado {SALIDA / 'sondeo.csv'} ({len(filas)} filas)")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("accion", choices=["ejecutar", "calificar", "informe", "plan"])
    a = p.parse_args()
    if a.accion == "ejecutar":
        asyncio.run(ejecutar())
    elif a.accion == "calificar":
        calificar()
    elif a.accion == "informe":
        informe()
    else:
        for f, k in plan():
            print(f"f{f}_{k}")


if __name__ == "__main__":
    main()
