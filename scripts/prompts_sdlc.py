"""Validación de los 7 prompts del SDLC con la plataforma de PromptOps
(Parcial 1, Componente 3, sección 6.1: Quality Gate obligatorio de prompts).

Por cada fase:  prompt inicial -> línea base (auditoría del original)
-> Optimizer -> auditoría -> auto-iteración hasta el objetivo -> decisión
humana (aprobar en la interfaz) -> versión aprobada.

Uso (con el servidor corriendo):

    python scripts/prompts_sdlc.py validar --objetivo 90 --intentos 3
    python scripts/prompts_sdlc.py estado
    # aprobar cada run en la interfaz (http://localhost:8000, HISTORIAL)
    python scripts/prompts_sdlc.py exportar

`validar` NUNCA aprueba: deja cada run en WAITING_HUMAN. La aprobación es
una decisión humana registrada en la plataforma (invariante del proyecto).
`exportar` solo publica como aprobada la versión que un humano aprobó; las
fases sin aprobar quedan marcadas como pendientes. Todas las métricas se
leen de la API: ninguna se escribe a mano.
"""

import argparse
import asyncio
import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
DIR_PROMPTS = RAIZ / "prompts"
DIR_INICIALES = DIR_PROMPTS / "iniciales"
DIR_APROBADOS = DIR_PROMPTS / "aprobados"
DIR_EVIDENCIA = RAIZ / "evidence" / "punto4_prompts"
MANIFIESTO = DIR_EVIDENCIA / "manifiesto.json"

# Tabla de la sección 6 del enunciado (entrada, rol, salida, Quality Gate).
FASES: list[dict] = [
    {"n": 1, "clave": "requirements", "archivo": "requirements.md", "fase": "Requerimientos",
     "rol": "Requirements Engineer", "entrada": "Necesidad + contexto del stakeholder",
     "salida": "Requisitos estructurados (REQ-XX)",
     "quality_gate": "Quality Score + verificabilidad + trazabilidad"},
    {"n": 2, "clave": "analysis_specification", "archivo": "analysis_specification.md",
     "fase": "Análisis / Especificación", "rol": "Analista / especificador",
     "entrada": "Requisitos aprobados", "salida": "Criterios de aceptación / especificación (SPEC-XX)",
     "quality_gate": "Completitud + consistencia + schema"},
    {"n": 3, "clave": "architecture", "archivo": "architecture.md", "fase": "Arquitectura / Diseño",
     "rol": "Software Architect", "entrada": "Especificación aprobada",
     "salida": "Arquitectura / contratos / diagramas (ARCH-XX)",
     "quality_gate": "Restricciones + trazabilidad + revisión"},
    {"n": 4, "clave": "implementation", "archivo": "implementation.md", "fase": "Implementación",
     "rol": "Developer", "entrada": "Diseño + contratos", "salida": "Código",
     "quality_gate": "Compilación + lint + tests"},
    {"n": 5, "clave": "testing", "archivo": "testing.md", "fase": "Testing / QA", "rol": "QA Engineer",
     "entrada": "Requisitos + código", "salida": "Casos y suites de prueba (TEST-XX)",
     "quality_gate": "Pass rate + cobertura + defectos"},
    {"n": 6, "clave": "deployment", "archivo": "deployment.md", "fase": "Deployment", "rol": "DevOps",
     "entrada": "Artefacto probado", "salida": "Pipeline / contenedor / despliegue",
     "quality_gate": "Build + seguridad + despliegue reproducible"},
    {"n": 7, "clave": "maintenance", "archivo": "maintenance.md", "fase": "Mantenimiento",
     "rol": "Maintainer", "entrada": "Código + incidencias + métricas",
     "salida": "Cambio / refactorización",
     "quality_gate": "Regression tests + deuda técnica + trazabilidad"},
]

_MARCADOR = re.compile(r"\{\{\s*([A-Z0-9_]+)\s*\}\}")
_ESPERANDO = {"WAITING_HUMAN"}
_TERMINADOS_OK = {"APPROVED", "EXECUTING", "COMPLETED"}


def _prompt_inicial(fase: dict) -> str:
    return (DIR_INICIALES / f"{fase['n']}_{fase['clave']}.txt").read_text(encoding="utf-8").strip()


def marcadores(texto: str) -> set[str]:
    return set(_MARCADOR.findall(texto or ""))


# ---------------------------------------------------------------------------
# Lectura de un run (todo sale de GET /api/runs/{id})
# ---------------------------------------------------------------------------


def _auditoria(iteracion: dict | None) -> dict | None:
    if not iteracion:
        return None
    return next((a for a in iteracion.get("audits", []) if a["parse_ok"]), None)


def linea_base(run: dict) -> dict | None:
    return next((it for it in run["iterations"] if it["source"] == "original"), None)


def iteracion_aprobada(run: dict) -> dict | None:
    """La iteración con la decisión humana 'approve' (la que se aprobó)."""
    for it in run["iterations"]:
        if any(d["decision"] == "approve" for d in it["human_decisions"]):
            return it
    return None


def ultima_iteracion(run: dict) -> dict | None:
    return run["iterations"][-1] if run["iterations"] else None


def mejor_score(run: dict) -> int | None:
    scores = [a["total_score"] for it in run["iterations"] if it["source"] != "original"
              for a in it["audits"] if a["parse_ok"]]
    return max(scores) if scores else None


def _resumen_gates(a: dict | None) -> str:
    if not a:
        return "—"
    return (f"{a['gates_passed']} PASS / {a['gates_failed']} FAIL / {a['gates_not_applicable']} N/A")


# ---------------------------------------------------------------------------
# validar
# ---------------------------------------------------------------------------


async def _esperar(client, run_id, etiqueta, condicion, limite_s=2400) -> dict:
    inicio = time.monotonic()
    anterior = None
    fallos = 0
    while True:
        try:
            r = await client.get(f"/api/runs/{run_id}")
            r.raise_for_status()
            fallos = 0
        except httpx.TransportError as exc:
            fallos += 1
            if fallos > 5:
                raise
            print(f"  [{etiqueta}] consulta fallida ({type(exc).__name__}), reintentando", flush=True)
            await asyncio.sleep(4)
            continue
        run = r.json()
        firma = (run["status"], len(run["iterations"]))
        if firma != anterior:
            ult = _auditoria(ultima_iteracion(run))
            print(f"  [{etiqueta}] {time.monotonic() - inicio:6.0f}s {run['status']:<14} "
                  f"iteraciones={len(run['iterations'])} último score={ult and ult['total_score']}", flush=True)
            anterior = firma
        if run["status"] == "ERROR" or condicion(run):
            return run
        if time.monotonic() - inicio > limite_s:
            raise TimeoutError(f"{etiqueta}: el run {run_id} no terminó en {limite_s}s")
        await asyncio.sleep(4)


def registrar_run(fase_clave: str, run_id: str) -> None:
    """Anota el run de una fase en el manifiesto en cuanto se crea (si el
    script se interrumpe, el run sigue en el servidor y no se pierde). Un
    run anterior de la misma fase queda como intento previo, no se borra."""
    DIR_EVIDENCIA.mkdir(parents=True, exist_ok=True)
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8")) if MANIFIESTO.exists() else {"fases": {}}
    anterior = manifiesto["fases"].get(fase_clave)
    previos = []
    if anterior and anterior["run_id"] != run_id:
        previos = anterior.get("intentos_previos", []) + [
            {k: v for k, v in anterior.items() if k != "intentos_previos"}
        ]
    elif anterior:
        previos = anterior.get("intentos_previos", [])
    manifiesto["fases"][fase_clave] = {
        "run_id": run_id, "validado_en": datetime.now(timezone.utc).isoformat(), **_commit(),
        **({"intentos_previos": previos} if previos else {}),
    }
    MANIFIESTO.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")


async def _validar_fase(client, fase, objetivo, intentos) -> dict:
    etiqueta = f"{fase['n']}-{fase['clave']}"
    r = await client.post("/api/runs", json={"prompt": _prompt_inicial(fase), "baseline_audit": True})
    r.raise_for_status()
    run_id = r.json()["id"]
    registrar_run(fase["clave"], run_id)
    run = await _esperar(client, run_id, etiqueta, lambda x: x["status"] in _ESPERANDO)

    if run["status"] == "WAITING_HUMAN" and (mejor_score(run) or 0) < objetivo and intentos > 0:
        iteraciones_antes = len(run["iterations"])
        r = await client.post(f"/api/runs/{run_id}/auto-iterate",
                              json={"target_score": objetivo, "max_attempts": intentos})
        r.raise_for_status()

        def termino_auto(x):
            ult = _auditoria(ultima_iteracion(x))
            hechas = len(x["iterations"]) - iteraciones_antes
            return x["status"] == "WAITING_HUMAN" and (
                hechas >= intentos or (ult is not None and ult["total_score"] >= objetivo)
            )

        run = await _esperar(client, run_id, etiqueta, termino_auto)
    return {"fase": fase["clave"], "run_id": run_id, "estado_final": run["status"]}


def _commit() -> dict:
    def git(*args):
        return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True).stdout.strip()
    return {"commit": git("rev-parse", "HEAD"),
            "cambios_sin_commit": bool(git("status", "--porcelain", "--untracked-files=no"))}


async def validar(base_url: str, objetivo: int, intentos: int, solo: list[str] | None) -> None:
    DIR_EVIDENCIA.mkdir(parents=True, exist_ok=True)
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8")) if MANIFIESTO.exists() else {"fases": {}}
    manifiesto.update({
        "servidor": base_url, "objetivo_auto_iteracion": objetivo, "intentos_auto_iteracion": intentos,
        "temperatura": "no se envía: valor por defecto de cada modelo en NVIDIA",
    })
    MANIFIESTO.write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")
    fases = [f for f in FASES if not solo or f["clave"] in solo]
    print(f"Validando {len(fases)} prompts contra {base_url} (objetivo {objetivo}, hasta {intentos} auto-iteraciones)...")
    async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
        resultados = await asyncio.gather(
            *(_validar_fase(client, f, objetivo, intentos) for f in fases), return_exceptions=True
        )
    for fase, res in zip(fases, resultados):
        if isinstance(res, Exception):
            print(f"  FALLO {fase['clave']}: {type(res).__name__}: {res}")
    estado(base_url)


# ---------------------------------------------------------------------------
# estado
# ---------------------------------------------------------------------------


def _cargar_runs(base_url: str) -> list[tuple[dict, dict | None]]:
    manifiesto = json.loads(MANIFIESTO.read_text(encoding="utf-8"))
    salida = []
    for fase in FASES:
        info = manifiesto["fases"].get(fase["clave"])
        run = httpx.get(f"{base_url}/api/runs/{info['run_id']}", timeout=60).json() if info else None
        salida.append((fase, run))
    return salida


def estado(base_url: str) -> None:
    print(f"\n{'Fase':<24}{'Estado':<15}{'Base':>5}{'Mejor':>6}{'Delta':>7}  Marcadores  Run")
    for fase, run in _cargar_runs(base_url):
        if run is None:
            print(f"{fase['fase']:<24}sin validar")
            continue
        base = _auditoria(linea_base(run))
        mejor = mejor_score(run)
        final = iteracion_aprobada(run) or ultima_iteracion(run)
        faltan = marcadores(run["original_prompt"]) - marcadores(final["output_prompt"] if final else "")
        delta = (mejor - base["total_score"]) if (mejor is not None and base) else None
        print(f"{fase['fase']:<24}{run['status']:<15}{base and base['total_score'] or '—':>5}"
              f"{mejor if mejor is not None else '—':>6}{('+' if (delta or 0) > 0 else '') + str(delta) if delta is not None else '—':>7}  "
              f"{'OK' if not faltan else 'FALTAN ' + ','.join(sorted(faltan)):<11} {run['id']}")


# ---------------------------------------------------------------------------
# exportar
# ---------------------------------------------------------------------------


def _bloque(texto: str) -> list[str]:
    return ["```text", texto.strip(), "```"]


def _tabla_gates(a: dict | None) -> list[str]:
    if not a:
        return ["_Sin auditoría válida._"]
    filas = ["| Gate | Estado | Justificación |", "|---|---|---|"]
    for g in a["gates"]:
        just = g["justification"].replace("|", "/").replace("\n", " ")
        filas.append(f"| {g['gate']} | {g['status']} | {just} |")
    return filas


def exportar(base_url: str) -> None:
    DIR_APROBADOS.mkdir(parents=True, exist_ok=True)
    (DIR_EVIDENCIA / "runs").mkdir(parents=True, exist_ok=True)
    filas_csv = []
    pendientes = []

    for fase, run in _cargar_runs(base_url):
        if run is None:
            pendientes.append(f"{fase['fase']}: sin validar")
            continue
        (DIR_EVIDENCIA / "runs" / f"{fase['n']}_{fase['clave']}.json").write_text(
            json.dumps(run, ensure_ascii=False, indent=2), encoding="utf-8")
        info = json.loads(MANIFIESTO.read_text(encoding="utf-8"))["fases"][fase["clave"]]
        for i, previo in enumerate(info.get("intentos_previos", []), start=1):
            run_previo = httpx.get(f"{base_url}/api/runs/{previo['run_id']}", timeout=60).json()
            (DIR_EVIDENCIA / "runs" / f"{fase['n']}_{fase['clave']}_intento_previo_{i}.json").write_text(
                json.dumps(run_previo, ensure_ascii=False, indent=2), encoding="utf-8")
        eventos = httpx.get(f"{base_url}/api/runs/{run['id']}/events", timeout=60).json()

        base_it = linea_base(run)
        base = _auditoria(base_it)
        aprobada = iteracion_aprobada(run)
        aprobado = run["status"] in _TERMINADOS_OK and aprobada is not None
        audit_final = _auditoria(aprobada) if aprobado else None
        decision = next((d for d in aprobada["human_decisions"] if d["decision"] == "approve"), None) if aprobada else None
        faltan = marcadores(run["original_prompt"]) - marcadores(aprobada["output_prompt"]) if aprobado else set()
        iteraciones_opt = [it for it in run["iterations"] if it["source"] != "original"]
        auto = sum(1 for it in run["iterations"] for d in it["human_decisions"]
                   if d["decision"] == "iterate" and (d["feedback"] or "").startswith("[AUTO-ITERACIÓN"))
        manuales = sum(1 for it in run["iterations"] for d in it["human_decisions"]
                       if d["decision"] in ("iterate", "edit") and not (d["feedback"] or "").startswith("[AUTO-ITERACIÓN"))
        delta = audit_final["total_score"] - base["total_score"] if (audit_final and base) else None

        if aprobado:
            (DIR_APROBADOS / f"{fase['n']}_{fase['clave']}.txt").write_text(
                aprobada["output_prompt"].strip() + "\n", encoding="utf-8")
        else:
            pendientes.append(f"{fase['fase']}: {run['status']} (falta la aprobación humana)")

        filas_csv.append({
            "fase": fase["n"], "nombre_fase": fase["fase"], "archivo": fase["archivo"], "run_id": run["id"],
            "estado": run["status"], "aprobado": aprobado,
            "score_inicial": base and base["total_score"],
            "gates_inicial": _resumen_gates(base),
            "gates_score_inicial": base and base["gates_score"],
            "score_aprobado": audit_final and audit_final["total_score"],
            "gates_aprobado": _resumen_gates(audit_final) if audit_final else "",
            "gates_score_aprobado": audit_final and audit_final["gates_score"],
            "delta_score": delta,
            "iteracion_aprobada": aprobada and aprobada["iteration_number"] if aprobado else "",
            "iteraciones_optimizacion": len(iteraciones_opt),
            "auto_iteraciones": auto, "intervenciones_humanas": manuales,
            "marcadores_conservados": (not faltan) if aprobado else "",
            "iteraciones_con_respaldo": sum(1 for it in run["iterations"] if it.get("optimizer_fallback")),
            "optimizer_model": run["optimizer_model"], "auditor_model": run["auditor_model"],
            "fecha_inicio": run["created_at"], "fecha_aprobacion": decision and decision["created_at"],
        })

        # Archivo de la fase (catálogo, sección 11 del enunciado).
        L = [f"# Fase {fase['n']} — {fase['fase']}", "",
             "> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación",
             "> de prompts. No editar a mano.", "",
             "| Campo | Valor |", "|---|---|",
             f"| Rol | {fase['rol']} |", f"| Entrada | {fase['entrada']} |",
             f"| Salida esperada | {fase['salida']} |", f"| Quality Gate de la fase (SDLC) | {fase['quality_gate']} |",
             f"| Variables de la plantilla | {', '.join('`{{' + m + '}}`' for m in sorted(marcadores(run['original_prompt'])))} |",
             f"| Run en la plataforma | `{run['id']}` |", f"| Estado | {run['status']} |",
             f"| Modelos | Optimizer `{run['optimizer_model']}` · Auditor `{run['auditor_model']}` |",
             f"| Validación | {run['created_at']} → aprobación {decision['created_at'] if decision else 'pendiente'} |",
             "", "## Métricas (Quality Gate de prompts, sección 6.1)", "",
             "| | Score | Gates | gates_score |", "|---|---|---|---|",
             f"| Inicial (línea base) | {base and base['total_score']} | {_resumen_gates(base)} | {base and base['gates_score']} |",
             f"| Aprobada | {audit_final['total_score'] if audit_final else 'pendiente'} | "
             f"{_resumen_gates(audit_final) if audit_final else 'pendiente'} | {audit_final['gates_score'] if audit_final else ''} |",
             f"| **Delta** | **{('+' if (delta or 0) > 0 else '') + str(delta) if delta is not None else 'pendiente'}** | | |",
             "", f"Iteraciones de optimización: {len(iteraciones_opt)} ({auto} automáticas, {manuales} humanas).",
             "", "## 1. Prompt inicial", "", *_bloque(run["original_prompt"]),
             "", "### Auditoría inicial (línea base)", "", *_tabla_gates(base)]
        if base and base["recommendations"]:
            L += ["", "Recomendaciones del Auditor:", ""] + [f"- {x}" for x in base["recommendations"]]
        L += ["", "## 2. Prompt optimizado y aprobado", ""]
        if aprobado:
            L += [*_bloque(aprobada["output_prompt"]), "",
                  f"Archivo para ejecución: `prompts/aprobados/{fase['n']}_{fase['clave']}.txt`"]
            if faltan:
                L += ["", f"**Atención:** la versión aprobada perdió variables de la plantilla: {', '.join(sorted(faltan))}."]
            L += ["", "### Auditoría de la versión aprobada", "", *_tabla_gates(audit_final)]
        else:
            L += ["_Pendiente de aprobación humana en la plataforma._"]
        L += ["", "## 3. Historial de iteraciones", "",
              "| # | Origen | Modelo | Score | Gates | Decisión humana |", "|---|---|---|---|---|---|"]
        for it in run["iterations"]:
            a = _auditoria(it)
            decs = "; ".join(
                d["decision"] + (" (automática)" if (d["feedback"] or "").startswith("[AUTO-ITERACIÓN") else "")
                for d in it["human_decisions"]) or "—"
            modelo = it.get("model") or "—"
            if it.get("optimizer_fallback"):
                modelo += f" (respaldo; `{it['optimizer_fallback']['from_model']}` no respondió)"
            L.append(f"| {it['iteration_number']} | {it['source']} | {modelo} | {a and a['total_score']} | "
                     f"{_resumen_gates(a)} | {decs} |")
        L += ["", "<details><summary>Timeline</summary>", ""] + \
             [f"- {e['timestamp']} — {e['description']}" for e in eventos] + ["", "</details>", ""]
        (DIR_PROMPTS / fase["archivo"]).write_text("\n".join(L), encoding="utf-8")

    with (DIR_PROMPTS / "validation_metrics.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(filas_csv[0].keys()))
        w.writeheader()
        w.writerows(filas_csv)
    print(f"Exportadas {len(filas_csv)} fases a {DIR_PROMPTS}")
    if pendientes:
        print("PENDIENTES:")
        for p in pendientes:
            print("  -", p)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default="http://localhost:8000")
    sub = p.add_subparsers(dest="comando", required=True)
    v = sub.add_parser("validar")
    v.add_argument("--objetivo", type=int, default=90)
    v.add_argument("--intentos", type=int, default=3)
    v.add_argument("--solo", nargs="*", help="claves de fase a (re)validar, p. ej. testing deployment")
    sub.add_parser("estado")
    sub.add_parser("exportar")
    args = p.parse_args()
    if args.comando == "validar":
        asyncio.run(validar(args.base_url, args.objetivo, args.intentos, args.solo))
    elif args.comando == "estado":
        estado(args.base_url)
    else:
        exportar(args.base_url)


if __name__ == "__main__":
    main()
