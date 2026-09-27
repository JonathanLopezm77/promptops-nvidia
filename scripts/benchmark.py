"""Benchmark de modelos por fase del SDLC (Parcial 1, Componente 4).

3 modelos × 3 fases (1 Requisitos, 3 Arquitectura, 4 Implementación) × 3
corridas = 27 ejecuciones. Diseño y reglas: benchmarks/DISENO.md.

    python scripts/benchmark.py ejecutar     # genera las 27 salidas (reanudable)
    python scripts/benchmark.py calificar    # Quality Gates y jueces (reanudable)
    python scripts/benchmark.py informe      # execution_log.csv, results.csv, RESULTADOS.md

`ejecutar` corre una ejecución a la vez, en orden aleatorio con semilla fija,
y guarda cada una al terminar: si se interrumpe, al relanzarlo continúa.
`calificar` guarda cada calificación; `--forzar` las repite.
"""

import argparse
import asyncio
import csv
import json
import random
import re
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from benchmarks.proveedores import (  # noqa: E402
    ModeloBench, Parametros, calentar_ollama, generar_con_reintentos, modelo_cargado, version_modelo,
)
from scripts.probar_proveedores import contexto_maquina  # noqa: E402

DIR_BENCH = RAIZ / "benchmarks"
DIR_EVIDENCIA = RAIZ / "evidence" / "punto6_benchmark"
DIR_EJECUCIONES = DIR_EVIDENCIA / "ejecuciones"
DIR_CALIFICACIONES = DIR_EVIDENCIA / "calificaciones"
MANIFIESTO = DIR_EVIDENCIA / "manifiesto.json"
FASES = {1: "fase1_requisitos.json", 3: "fase3_arquitectura.json", 4: "fase4_implementacion.json"}
CORRIDAS = 3
SEMILLA = 20260927
JUEZ_PRINCIPAL = "openai/gpt-oss-20b"
JUEZ_SECUNDARIO = "nvidia/nemotron-3-super-120b-a12b"


def cargar_modelos() -> tuple[list[ModeloBench], Parametros, dict]:
    datos = json.loads((DIR_BENCH / "modelos.json").read_text(encoding="utf-8"))
    return [ModeloBench(**m) for m in datos["modelos"]], Parametros(**datos["parametros"]), datos


def cargar_caso(fase: int) -> dict:
    return json.loads((DIR_BENCH / "casos" / FASES[fase]).read_text(encoding="utf-8"))


def prompt_de(fase: int) -> str:
    """Prompt aprobado con las variables del caso sustituidas."""
    caso = cargar_caso(fase)
    texto = (RAIZ / caso["prompt"]).read_text(encoding="utf-8")
    for nombre, valor in caso["variables"].items():
        texto = texto.replace("{{" + nombre + "}}", valor)
    restantes = re.findall(r"\{\{\s*[A-Z_]+\s*\}\}", texto)
    if restantes:
        raise ValueError(f"fase {fase}: quedaron variables sin sustituir: {restantes}")
    return texto


def id_ejecucion(fase: int, clave: str, n: int) -> str:
    return f"f{fase}_{clave}_{n}"


def plan() -> list[tuple[int, str, int]]:
    modelos, _, _ = cargar_modelos()
    combinaciones = [(f, m.clave, n) for f in FASES for m in modelos for n in range(1, CORRIDAS + 1)]
    random.Random(SEMILLA).shuffle(combinaciones)
    return combinaciones


# ---------------------------------------------------------------------------
# ejecutar
# ---------------------------------------------------------------------------


async def ejecutar() -> None:
    env = dotenv_values(RAIZ / ".env")
    modelos, params, config = cargar_modelos()
    por_clave = {m.clave: m for m in modelos}
    DIR_EJECUCIONES.mkdir(parents=True, exist_ok=True)
    pendientes = [p for p in plan() if not (DIR_EJECUCIONES / f"{id_ejecucion(*p)}.json").exists()
                  and (SOLO is None or id_ejecucion(*p) in SOLO)]
    print(f"{len(pendientes)} de {len(plan())} ejecuciones pendientes", flush=True)
    if not pendientes:
        return

    async with httpx.AsyncClient(timeout=1800) as c:
        manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8")) if MANIFIESTO.exists() else {"sesiones": []}
        sesion = {"inicio_utc": datetime.now(timezone.utc).isoformat(), "maquina_antes": contexto_maquina(),
                  "versiones": {m.clave: await version_modelo(c, m, nvidia_base_url=env["NVIDIA_BASE_URL"])
                                for m in modelos},
                  "parametros": config["parametros"], "reintentos": config["reintentos"], "semilla_orden": SEMILLA}
        local = next((m for m in modelos if m.proveedor == "ollama"), None)
        if local:
            sesion["local_ya_cargado"] = await modelo_cargado(c, local)
            sesion["local_carga_al_calentar_s"] = await calentar_ollama(c, local)
        manifiesto["sesiones"].append(sesion)
        MANIFIESTO.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")

        prompts = {f: prompt_de(f) for f in FASES}
        orden = {p: i for i, p in enumerate(plan(), start=1)}
        for fase, clave, n in pendientes:
            cfg = por_clave[clave]
            t0 = time.perf_counter()
            res = await generar_con_reintentos(
                cfg, [{"role": "user", "content": prompts[fase]}], params,
                max_intentos=config["reintentos"]["max_intentos"], client=c,
                nvidia_base_url=env["NVIDIA_BASE_URL"], nvidia_api_key=env["NVIDIA_API_KEY"],
            )
            registro = {
                "id": id_ejecucion(fase, clave, n), "fase": fase, "modelo_clave": clave, "corrida": n,
                "posicion_en_orden": orden[(fase, clave, n)], "modelo": cfg.__dict__,
                "parametros": config["parametros"], "prompt_enviado": prompts[fase], "resultado": res.a_dict(),
            }
            (DIR_EJECUCIONES / f"{registro['id']}.json").write_text(
                json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[{orden[(fase, clave, n)]:>2}/27] {registro['id']:<28} {'OK   ' if res.ok else 'FALLO'} "
                  f"total={res.latencia_total_s:.0f}s ttft_resp={res.ttft_contenido_s and round(res.ttft_contenido_s, 1)}s "
                  f"tokens={res.tokens_entrada}/{res.tokens_salida} intentos={res.intentos} "
                  f"({time.perf_counter() - t0:.0f}s){' ERROR=' + res.error if res.error else ''}", flush=True)

        sesion["fin_utc"] = datetime.now(timezone.utc).isoformat()
        sesion["maquina_despues"] = contexto_maquina()
        MANIFIESTO.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# calificar
# ---------------------------------------------------------------------------


async def calificar(forzar: bool) -> None:
    from backend.config import get_settings
    from benchmarks.calificadores import calificar_fase1, calificar_fase3, calificar_fase4
    from benchmarks.juez import juzgar_arquitectura, juzgar_requisitos

    s = get_settings()
    # Jueces: modo JSON y más tiempo (gpt-oss-20b tardó hasta 545 s en la prueba previa).
    s.json_mode_models = frozenset(s.json_mode_models | {JUEZ_PRINCIPAL, JUEZ_SECUNDARIO})
    s.llm_timeout_seconds = 600
    s.llm_max_retries = 1

    DIR_CALIFICACIONES.mkdir(parents=True, exist_ok=True)
    casos = {f: cargar_caso(f) for f in FASES}
    limite = asyncio.Semaphore(4)

    async def jueces(fase: int, salida: str) -> dict:
        v = casos[fase]["variables"]
        async with limite:
            if fase == 1:
                contexto = f"{v['NECESIDAD_DEL_STAKEHOLDER']}\n{v['CONTEXTO_DEL_PROYECTO']}"
                resultados = await asyncio.gather(juzgar_requisitos(JUEZ_PRINCIPAL, salida, contexto),
                                                  juzgar_requisitos(JUEZ_SECUNDARIO, salida, contexto))
            else:
                resultados = await asyncio.gather(
                    juzgar_arquitectura(JUEZ_PRINCIPAL, v["ESPECIFICACION_APROBADA"], v["RESTRICCIONES_TECNICAS"], salida),
                    juzgar_arquitectura(JUEZ_SECUNDARIO, v["ESPECIFICACION_APROBADA"], v["RESTRICCIONES_TECNICAS"], salida))
        return {r.juez: r.__dict__ for r in resultados}

    async def una(archivo: Path) -> None:
        destino = DIR_CALIFICACIONES / archivo.name
        if SOLO is not None and archivo.stem not in SOLO:
            return
        if destino.exists() and not forzar:
            return
        ej = json.loads(archivo.read_text(encoding="utf-8"))
        res, fase = ej["resultado"], ej["fase"]
        salida = res["contenido"] if res["ok"] else ""
        cal = {"id": ej["id"], "fase": fase, "modelo_clave": ej["modelo_clave"], "corrida": ej["corrida"],
               "ejecucion_ok": res["ok"], "calificado_en": datetime.now(timezone.utc).isoformat()}
        if not res["ok"]:
            cal.update({"puntaje": 0.0, "cumple_tarea": False, "schema_ok": False, "violaciones": [],
                        "supuestos_no_sustentados": [], "nota": f"la ejecución falló: {res['error']}"})
        elif fase == 4:
            cal.update(await asyncio.to_thread(calificar_fase4, salida))
        else:
            cal["jueces"] = await jueces(fase, salida)
            principal = cal["jueces"][JUEZ_PRINCIPAL]
            elegido = principal if principal["ok"] else cal["jueces"][JUEZ_SECUNDARIO]
            cal["juez_usado"] = elegido["juez"] if elegido["ok"] else None
            cal["autoevaluacion"] = (cal["juez_usado"] == JUEZ_SECUNDARIO
                                     and ej["modelo"]["modelo"] == JUEZ_SECUNDARIO)
            datos = elegido["datos"] if elegido["ok"] else None
            if fase == 1:
                cal.update(calificar_fase1(salida, casos[1]["variables"], datos["global_score"] if datos else None))
            else:
                cal.update(calificar_fase3(salida, casos[3]["ids_spec"], datos))
            # Puntaje alternativo con el otro juez, para comparar jueces.
            otro = cal["jueces"][JUEZ_SECUNDARIO if elegido["juez"] == JUEZ_PRINCIPAL else JUEZ_PRINCIPAL]
            if otro["ok"] and datos is not None:
                alt = (calificar_fase1(salida, casos[1]["variables"], otro["datos"]["global_score"]) if fase == 1
                       else calificar_fase3(salida, casos[3]["ids_spec"], otro["datos"]))
                cal["puntaje_otro_juez"] = {"juez": otro["juez"], "puntaje": alt["puntaje"]}
        destino.write_text(json.dumps(cal, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        print(f"calificado {ej['id']:<28} puntaje={cal.get('puntaje')} cumple={cal.get('cumple_tarea')} "
              f"juez={cal.get('juez_usado', '-')}", flush=True)

    await asyncio.gather(*(una(a) for a in sorted(DIR_EJECUCIONES.glob("*.json"))))


# ---------------------------------------------------------------------------
# informe
# ---------------------------------------------------------------------------


def _media_sd(valores: list[float]) -> tuple[float | None, float | None]:
    v = [x for x in valores if x is not None]
    if not v:
        return None, None
    return round(statistics.mean(v), 2), round(statistics.stdev(v), 2) if len(v) > 1 else 0.0


def informe() -> None:
    filas = []
    for archivo in sorted(DIR_EJECUCIONES.glob("*.json")):
        ej = json.loads(archivo.read_text(encoding="utf-8"))
        cal_archivo = DIR_CALIFICACIONES / archivo.name
        cal = json.loads(cal_archivo.read_text(encoding="utf-8")) if cal_archivo.exists() else {}
        r = ej["resultado"]
        rec = r.get("recursos") or {}
        vram = (rec.get("modelos_cargados_ollama") or [{}])[0] if rec else {}
        filas.append({
            "id": ej["id"], "fase": ej["fase"], "modelo_clave": ej["modelo_clave"], "modelo": ej["modelo"]["modelo"],
            "corrida": ej["corrida"], "posicion_en_orden": ej["posicion_en_orden"],
            "inicio_utc": r["inicio_utc"], "fin_utc": r["fin_utc"],
            "temperature": ej["parametros"]["temperature"], "top_p": ej["parametros"]["top_p"],
            "max_tokens": ej["parametros"]["max_tokens"], "extra_modelo": json.dumps(ej["modelo"]["extra"]),
            "ejecucion_ok": r["ok"], "intentos": r["intentos"], "errores_previos": " | ".join(r["errores_previos"]),
            "error": r["error"] or "", "finish_reason": r["finish_reason"],
            "ttft_s": r["ttft_s"], "ttft_respuesta_s": r["ttft_contenido_s"], "latencia_total_s": r["latencia_total_s"],
            "duracion_con_reintentos_s": r["duracion_con_reintentos_s"],
            "tokens_entrada": r["tokens_entrada"], "tokens_salida": r["tokens_salida"],
            "tokens_razonamiento": r["tokens_razonamiento"], "caracteres_razonamiento": len(r["razonamiento"]),
            "costo_usd": 0.0,
            "ram_proceso_max_mb": (rec.get("ram_proceso_mb") or {}).get("max"),
            "cpu_proceso_media_pct": (rec.get("cpu_proceso_pct") or {}).get("media"),
            "gpu_uso_max_pct": (rec.get("gpu_uso_pct") or {}).get("max"),
            "vram_modelo_mb": vram.get("vram_mb"), "fraccion_modelo_en_gpu": vram.get("fraccion_gpu"),
            "quality_gate_score": cal.get("puntaje"), "cumple_tarea": cal.get("cumple_tarea"),
            "schema_ok": cal.get("schema_ok"), "n_violaciones": len(cal.get("violaciones") or []),
            "n_supuestos_no_sustentados": len(cal.get("supuestos_no_sustentados") or []),
            "juez_usado": cal.get("juez_usado", ""), "autoevaluacion": cal.get("autoevaluacion", ""),
            "puntaje_otro_juez": (cal.get("puntaje_otro_juez") or {}).get("puntaje"),
        })
    if not filas:
        print("no hay ejecuciones")
        return
    with (DIR_BENCH_SALIDA / "execution_log.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
        w.writeheader()
        w.writerows(filas)

    resumen = []
    for fase in FASES:
        for clave in dict.fromkeys(x["modelo_clave"] for x in filas):
            g = [x for x in filas if x["fase"] == fase and x["modelo_clave"] == clave]
            if not g:
                continue
            n = len(g)
            qg_media, qg_sd = _media_sd([x["quality_gate_score"] for x in g])
            ttft, _ = _media_sd([x["ttft_respuesta_s"] for x in g])
            lat, lat_sd = _media_sd([x["latencia_total_s"] for x in g])
            resumen.append({
                "fase": fase, "modelo_clave": clave, "modelo": g[0]["modelo"], "ejecuciones": n,
                "task_success_rate": round(sum(bool(x["cumple_tarea"]) for x in g) / n, 3),
                "quality_gate_score_media": qg_media, "consistency_sd_quality_gate": qg_sd,
                "constraint_violation_rate": round(sum(x["n_violaciones"] > 0 for x in g) / n, 3),
                "hallucination_rate": round(sum(x["n_supuestos_no_sustentados"] > 0 for x in g) / n, 3),
                "schema_compliance": round(sum(bool(x["schema_ok"]) for x in g) / n, 3),
                "ttft_respuesta_media_s": ttft, "latencia_media_s": lat, "latencia_sd_s": lat_sd,
                "tokens_entrada_media": _media_sd([x["tokens_entrada"] for x in g])[0],
                "tokens_salida_media": _media_sd([x["tokens_salida"] for x in g])[0],
                "costo_usd_total": 0.0,
                "intentos_totales": sum(x["intentos"] for x in g),
                "ejecuciones_fallidas": sum(not x["ejecucion_ok"] for x in g),
                "ram_proceso_max_mb": max((x["ram_proceso_max_mb"] or 0) for x in g) or None,
                "vram_modelo_mb": max((x["vram_modelo_mb"] or 0) for x in g) or None,
                "gpu_uso_max_pct": max((x["gpu_uso_max_pct"] or 0) for x in g) or None,
                "quality_gate_otro_juez_media": _media_sd([x["puntaje_otro_juez"] for x in g])[0],
            })
    with (DIR_BENCH_SALIDA / "results.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(resumen[0].keys()))
        w.writeheader()
        w.writerows(resumen)
    print(f"Generados {DIR_BENCH_SALIDA / 'execution_log.csv'} ({len(filas)} filas) y results.csv ({len(resumen)} filas)")


SOLO: set[str] | None = None


def _usar_carpeta(carpeta: Path) -> None:
    """Redirige toda la evidencia (y los CSV) a otra carpeta: para ensayos."""
    global DIR_EVIDENCIA, DIR_EJECUCIONES, DIR_CALIFICACIONES, MANIFIESTO, DIR_BENCH_SALIDA
    DIR_EVIDENCIA = carpeta
    DIR_EJECUCIONES = carpeta / "ejecuciones"
    DIR_CALIFICACIONES = carpeta / "calificaciones"
    MANIFIESTO = carpeta / "manifiesto.json"
    DIR_BENCH_SALIDA = carpeta


DIR_BENCH_SALIDA = DIR_BENCH


def main() -> None:
    global SOLO
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--salida", type=Path, help="carpeta alternativa para un ensayo (no toca la evidencia real)")
    p.add_argument("--solo", help="ids de ejecución separados por comas, p. ej. f1_local_1,f4_local_2")
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("ejecutar")
    c = sub.add_parser("calificar")
    c.add_argument("--forzar", action="store_true")
    sub.add_parser("informe")
    sub.add_parser("plan", help="muestra el orden de las 27 ejecuciones")
    a = p.parse_args()
    if a.salida:
        _usar_carpeta(a.salida.resolve())
    SOLO = {x.strip() for x in a.solo.split(",") if x.strip()} if a.solo else None
    if a.comando == "ejecutar":
        asyncio.run(ejecutar())
    elif a.comando == "calificar":
        asyncio.run(calificar(a.forzar))
    elif a.comando == "informe":
        informe()
    else:
        for i, x in enumerate(plan(), 1):
            print(i, id_ejecucion(*x))


if __name__ == "__main__":
    main()
