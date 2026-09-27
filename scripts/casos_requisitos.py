"""Casos mínimos de prueba de la capa de Ingeniería de Requisitos
(Parcial 1, Componente 1, sección 4.4) con evidencia reproducible.

    A. Requisito claro          -> reconoce alta calidad y no lo modifica.
    B. Requisito ambiguo        -> detecta ambigüedad, pregunta y mejora
                                   (y mejora más al responder las preguntas).
    C. Contradictorio/incompleto-> señala la contradicción y lo que falta, y
                                   se abstiene de inventar datos.
    D. Requisito por voz        -> transcribe, valida, mejora y responde
                                   hablando. Requiere un humano con micrófono:
                                   se ejecuta desde la interfaz y aquí solo se
                                   exporta y verifica.

Uso (con el servidor corriendo, p. ej. uvicorn backend.main:app):

    python scripts/casos_requisitos.py ejecutar --repeticiones 3
    python scripts/casos_requisitos.py voz --id <uuid del análisis por voz>
    python scripts/casos_requisitos.py informe

`ejecutar` y `voz` guardan la respuesta completa de la API de cada análisis
(incluidas las respuestas crudas de los modelos) en <salida>/corridas/.
`informe` NO llama a la API: recalcula todas las verificaciones a partir de
esos JSON y genera resultados.csv y RESULTADOS.md. Ningún número del informe
se escribe a mano.
"""

import argparse
import asyncio
import csv
import json
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx

RAIZ = Path(__file__).resolve().parent.parent
SALIDA_POR_DEFECTO = RAIZ / "evidence" / "punto3_casos"
TERMINALES = {"COMPLETED", "ERROR"}

# ---------------------------------------------------------------------------
# Definición de los casos (entradas fijas, escritas antes de ejecutar)
# ---------------------------------------------------------------------------

CASOS: dict[str, dict] = {
    "A": {
        "tipo": "Requisito claro",
        "esperado": "Debe reconocer alta calidad y evitar modificaciones innecesarias.",
        "requirement": (
            "REQ-AUT-03 (origen: política de seguridad de la tienda en línea). El sistema deberá "
            "bloquear durante 15 minutos la cuenta de un cliente registrado cuando se produzcan 5 "
            "intentos fallidos consecutivos de inicio de sesión dentro de un periodo de 10 minutos.\n"
            "Criterios de aceptación:\n"
            "1. Dado un cliente con 4 intentos fallidos consecutivos en los últimos 10 minutos, cuando "
            "falla el quinto intento, entonces la cuenta queda bloqueada y el sistema rechaza todo "
            "inicio de sesión de esa cuenta durante 15 minutos.\n"
            "2. Dado una cuenta bloqueada hace 15 minutos o más, cuando el cliente ingresa su "
            "contraseña correcta, entonces el inicio de sesión es exitoso.\n"
            "3. Dado un cliente con 4 intentos fallidos consecutivos, cuando inicia sesión "
            "correctamente, entonces el contador de intentos fallidos vuelve a 0."
        ),
        "project_context": (
            "Tienda en línea. Los clientes registrados inician sesión con correo y contraseña. "
            "La política de seguridad exige bloqueo temporal de cuentas ante intentos fallidos repetidos."
        ),
    },
    "B": {
        "tipo": "Requisito ambiguo",
        "esperado": "Debe detectar ambigüedad, formular preguntas y mejorar el requisito.",
        "requirement": (
            "El sistema debe permitir a los clientes buscar productos de forma rápida y sencilla, "
            "mostrando resultados relevantes."
        ),
        "project_context": (
            "Tienda en línea de artículos deportivos con catálogo público. Los clientes pueden "
            "comprar como invitados o con una cuenta registrada."
        ),
        # Respuestas del stakeholder, fijadas de antemano (no dependen de las
        # preguntas que genere el modelo en cada corrida).
        "aclaracion": (
            "La búsqueda se hace desde un único cuadro de texto visible en la parte superior de todas "
            "las páginas y busca por nombre, marca y categoría del producto. Los resultados deben "
            "mostrarse en máximo 2 segundos con un catálogo de hasta 20000 productos. 'Relevantes' "
            "significa que el texto buscado aparece en el nombre, la marca o la categoría; primero se "
            "muestran las coincidencias en el nombre y luego las demás, ordenadas por unidades "
            "vendidas. 'Sencilla' significa que no hace falta iniciar sesión ni usar filtros para "
            "buscar. Aplica a clientes registrados e invitados."
        ),
    },
    "C": {
        "tipo": "Requisito contradictorio o incompleto",
        "esperado": (
            "Debe señalar la inconsistencia o falta de información y abstenerse de inventar datos."
        ),
        "requirement": (
            "Los reportes de ventas deben generarse automáticamente cada día, pero solo cuando el "
            "gerente los solicite manualmente, y deben incluir los datos necesarios."
        ),
        "project_context": (
            "Sistema de ventas para una cadena de tiendas. Los gerentes consultan reportes desde la web."
        ),
    },
    "D": {
        "tipo": "Requisito ingresado por voz",
        "esperado": "Debe transcribir, validar, mejorar y devolver retroalimentación hablada.",
    },
}

# Términos vagos del requisito B: al menos uno debe detectarse como ambiguo.
TERMINOS_VAGOS_B = ("rápid", "sencill", "relevant")


# ---------------------------------------------------------------------------
# Ejecución contra la API
# ---------------------------------------------------------------------------


async def _esperar(client: httpx.AsyncClient, analysis_id: str, etiqueta: str, limite_s: int) -> dict:
    inicio = time.monotonic()
    estado_anterior = None
    while True:
        r = await client.get(f"/api/requirements/{analysis_id}")
        r.raise_for_status()
        analisis = r.json()
        if analisis["status"] != estado_anterior:
            print(f"  [{etiqueta}] {time.monotonic() - inicio:6.1f}s  {analisis['status']}", flush=True)
            estado_anterior = analisis["status"]
        if analisis["status"] in TERMINALES:
            return analisis
        if time.monotonic() - inicio > limite_s:
            raise TimeoutError(f"{etiqueta}: el análisis {analysis_id} no terminó en {limite_s}s")
        await asyncio.sleep(5)


async def _correr(client: httpx.AsyncClient, caso: str, n: int, corridas: Path, limite_s: int) -> None:
    datos = CASOS[caso]
    etiqueta = f"{caso}{n}"
    r = await client.post(
        "/api/requirements",
        json={"requirement": datos["requirement"], "project_context": datos["project_context"]},
    )
    r.raise_for_status()
    analisis = await _esperar(client, r.json()["id"], etiqueta, limite_s)
    _guardar(corridas / f"{caso}_{n}.json", analisis)

    if "aclaracion" in datos and analisis["status"] == "COMPLETED":
        r = await client.post(
            f"/api/requirements/{analisis['id']}/clarify", json={"answers": datos["aclaracion"]}
        )
        r.raise_for_status()
        hijo = await _esperar(client, r.json()["id"], f"{etiqueta}-aclaración", limite_s)
        _guardar(corridas / f"{caso}_{n}_aclaracion.json", hijo)


def _guardar(ruta: Path, analisis: dict) -> None:
    ruta.write_text(json.dumps(analisis, ensure_ascii=False, indent=2), encoding="utf-8")


def _commit() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True).stdout.strip()

    return {"commit": git("rev-parse", "HEAD"), "cambios_sin_commit": bool(git("status", "--porcelain"))}


def _config_local() -> dict:
    """Parámetros NO secretos del .env local (nunca la API key ni la URL de la BD)."""
    permitidas = ("NVIDIA_BASE_URL", "LLM_TIMEOUT_SECONDS", "LLM_MAX_RETRIES", "LLM_JSON_MODE")
    config = {}
    env = RAIZ / ".env"
    if env.exists():
        for linea in env.read_text(encoding="utf-8").splitlines():
            clave, _, valor = linea.partition("=")
            if clave.strip() in permitidas:
                config[clave.strip()] = valor.strip()
    config["temperatura"] = "no se envía: valor por defecto de cada modelo en NVIDIA"
    return config


async def ejecutar(base_url: str, repeticiones: int, salida: Path, limite_s: int) -> None:
    corridas = salida / "corridas"
    corridas.mkdir(parents=True, exist_ok=True)
    manifiesto = {
        "ejecutado_en": datetime.now(timezone.utc).isoformat(),
        "servidor": base_url,
        "repeticiones": repeticiones,
        **_commit(),
        "configuracion": _config_local() if "localhost" in base_url or "127.0.0.1" in base_url else {},
        "casos": {k: {c: v for c, v in d.items()} for k, d in CASOS.items() if k != "D"},
    }
    (salida / "manifiesto.json").write_text(json.dumps(manifiesto, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Ejecutando A, B y C x{repeticiones} contra {base_url} (en paralelo)...")
    inicio = time.monotonic()
    async with httpx.AsyncClient(base_url=base_url, timeout=60) as client:
        tareas = [
            _correr(client, caso, n, corridas, limite_s)
            for caso in ("A", "B", "C")
            for n in range(1, repeticiones + 1)
        ]
        resultados = await asyncio.gather(*tareas, return_exceptions=True)
    for r in resultados:
        if isinstance(r, Exception):
            print(f"  FALLO DE EJECUCIÓN: {type(r).__name__}: {r}")
    print(f"Terminado en {time.monotonic() - inicio:.0f}s. Evidencia en {corridas}")


def exportar_voz(base_url: str, analysis_id: str, salida: Path) -> None:
    corridas = salida / "corridas"
    corridas.mkdir(parents=True, exist_ok=True)
    r = httpx.get(f"{base_url}/api/requirements/{analysis_id}", timeout=60)
    r.raise_for_status()
    analisis = r.json()
    if analisis.get("input_mode") != "voice":
        print(f"Atención: el análisis {analysis_id} no se ingresó por voz (input_mode={analisis.get('input_mode')}).")
    # Reexportar el mismo análisis lo actualiza en vez de duplicarlo.
    existentes = sorted(corridas.glob("D_*.json"))
    ruta = next(
        (p for p in existentes if json.loads(p.read_text(encoding="utf-8"))["id"] == analisis["id"]),
        corridas / f"D_{len(existentes) + 1}.json",
    )
    _guardar(ruta, analisis)
    print(f"Guardado {ruta} (estado {analisis.get('status')})")


# ---------------------------------------------------------------------------
# Verificaciones (se recalculan siempre desde los JSON guardados)
# ---------------------------------------------------------------------------


@dataclass
class Verificacion:
    codigo: str
    descripcion: str
    requerida: bool
    ok: bool
    detalle: str


def _evaluacion(a: dict, etapa: str) -> dict | None:
    return next((e for e in a.get("evaluations", []) if e["stage"] == etapa and e["parse_ok"]), None)


def _criterio(ev: dict | None, clave: str) -> dict | None:
    if not ev:
        return None
    return next((c for c in ev["criteria"] if c["criterion"] == clave), None)


def _puntaje_final(a: dict) -> int | None:
    """Puntaje de la versión recomendada: el mejorado si existe y se recomienda,
    si no el original."""
    mej = _evaluacion(a, "improved")
    if mej and a.get("recommended_version") == "improved":
        return mej["global_score"]
    orig = _evaluacion(a, "original")
    return orig["global_score"] if orig else None


def _v(codigo, descripcion, requerida, ok, detalle="") -> Verificacion:
    return Verificacion(codigo, descripcion, requerida, bool(ok), detalle)


def verificar(caso: str, a: dict, hijo: dict | None = None) -> list[Verificacion]:
    orig = _evaluacion(a, "original")
    imp = a.get("improvement") or {}
    mejorado = a.get("improved_requirement") or ""
    vs = [
        _v("G1", "El análisis terminó sin error", True, a["status"] == "COMPLETED",
           a.get("error_message") or a["status"]),
        _v("G2", "La evaluación del original es válida (10 criterios)", True, orig is not None),
    ]
    if orig is None:
        return vs

    preguntas = orig.get("clarification_questions") or []
    ambiguos = [t["term"] for t in orig.get("ambiguous_terms") or []]

    if caso == "A":
        vs += [
            _v("A1", "Reconoce alta calidad (≥ 80 y ningún criterio < 6)", True,
               orig["is_high_quality"], f"puntaje {orig['global_score']}, mínimo "
               f"{min(c['score'] for c in orig['criteria'])}"),
            _v("A2", "No modifica el requisito", True,
               a.get("improvement_skipped") and not mejorado,
               "omitida" if a.get("improvement_skipped") else "se generó una versión mejorada"),
            _v("A3", "No hace preguntas de aclaración", False, not preguntas, f"{len(preguntas)} preguntas"),
            _v("A4", "No marca términos ambiguos", False, not ambiguos, ", ".join(ambiguos) or "ninguno"),
        ]
    elif caso == "B":
        vagos = [t for t in ambiguos if any(v in t.lower() for v in TERMINOS_VAGOS_B)]
        vs += [
            _v("B1", "Detecta los términos vagos (rápida / sencilla / relevantes)", True, vagos,
               ", ".join(ambiguos) or "ninguno"),
            _v("B2", "Formula preguntas de aclaración", True, preguntas, f"{len(preguntas)} preguntas"),
            _v("B3", "Mejora el requisito (versión mejorada con delta > 0)", True,
               mejorado and a.get("recommended_version") == "improved", f"delta {a.get('score_delta')}"),
            _v("B4", "No inventa valores numéricos", True, not imp.get("unsupported_values"),
               ", ".join(imp.get("unsupported_values") or []) or "ninguno"),
        ]
        if hijo is not None:
            final_hijo = _puntaje_final(hijo)
            imp_hijo = hijo.get("improvement") or {}
            pend_padre = len(imp.get("pending_items") or [])
            pend_hijo = len(imp_hijo.get("pending_items") or [])
            vs += [
                _v("B5", "Con las respuestas del stakeholder el requisito final supera al original", True,
                   hijo["status"] == "COMPLETED" and final_hijo is not None
                   and final_hijo > orig["global_score"],
                   f"original {orig['global_score']} → final tras aclarar {final_hijo}"),
                _v("B6", "Tras aclarar quedan menos datos por definir", False,
                   hijo["status"] == "COMPLETED" and pend_hijo < pend_padre,
                   f"{pend_padre} → {pend_hijo} pendientes"),
                _v("B7", "Tras aclarar no inventa valores numéricos", True,
                   not imp_hijo.get("unsupported_values"),
                   ", ".join(imp_hijo.get("unsupported_values") or []) or "ninguno"),
            ]
    elif caso == "C":
        consistencia = _criterio(orig, "consistencia")
        pendientes = imp.get("pending_items") or []
        # La contradicción queda pendiente si se nombra como tal o si algún
        # pendiente pide elegir entre generación automática y a solicitud.
        deja_pendiente = "contradic" in (mejorado + " " + " ".join(pendientes)).lower() or any(
            "automátic" in p.lower() and ("manual" in p.lower() or "solicit" in p.lower())
            for p in pendientes
        )
        vs += [
            _v("C1", "Detecta la contradicción (consistencia ≤ 3)", True,
               consistencia and consistencia["score"] <= 3,
               f"consistencia {consistencia['score'] if consistencia else '—'}"),
            _v("C2", "Señala la información faltante y pregunta", True,
               orig.get("missing_information") and preguntas,
               f"{len(orig.get('missing_information') or [])} faltantes, {len(preguntas)} preguntas"),
            _v("C3", "Deja explícito lo que falta con [POR DEFINIR]", True,
               "[POR DEFINIR" in mejorado.upper() and pendientes, f"{len(pendientes)} pendientes"),
            _v("C4", "No resuelve la contradicción por su cuenta (la deja pendiente)", True, deja_pendiente),
            _v("C5", "No inventa valores numéricos", True, not imp.get("unsupported_values"),
               ", ".join(imp.get("unsupported_values") or []) or "ninguno"),
        ]
    elif caso == "D":
        stt = a.get("stt_metadata") or {}
        tts = a.get("tts_log") or []
        vs += [
            _v("D1", "Entrada por voz con metadata de STT (motor, proveedor, local/remoto, idioma)", True,
               a.get("input_mode") == "voice"
               and all(stt.get(k) for k in ("engine", "provider", "processing", "language")),
               f"{stt.get('engine')} · {stt.get('provider')} · {stt.get('processing')}"),
            _v("D2", "Valida y mejora (o reconoce alta calidad)", True,
               mejorado or a.get("improvement_skipped")),
            _v("D3", "Devuelve retroalimentación hablada registrada (TTS)", True,
               tts and all(e.get("voice") and e.get("processing") for e in tts),
               f"{len(tts)} lecturas" + (f" · {tts[-1]['voice']} ({tts[-1]['processing']})" if tts else "")),
            _v("D4", "Transcripción usada sin corregir a mano", False, not stt.get("edited"),
               "corregida a mano" if stt.get("edited") else "sin cambios"),
        ]
    return vs


# ---------------------------------------------------------------------------
# Informe
# ---------------------------------------------------------------------------


def _cargar(salida: Path) -> tuple[dict, list[tuple[str, int, dict, dict | None]]]:
    corridas = salida / "corridas"
    manifiesto = json.loads((salida / "manifiesto.json").read_text(encoding="utf-8"))
    filas = []
    for ruta in sorted(corridas.glob("*.json")):
        if ruta.stem.endswith("_aclaracion"):
            continue
        caso, n = ruta.stem.split("_")
        analisis = json.loads(ruta.read_text(encoding="utf-8"))
        ruta_hijo = corridas / f"{ruta.stem}_aclaracion.json"
        hijo = json.loads(ruta_hijo.read_text(encoding="utf-8")) if ruta_hijo.exists() else None
        filas.append((caso, int(n), analisis, hijo))
    return manifiesto, filas


def _seg(ms: int | None) -> str:
    return f"{ms / 1000:.1f}" if ms is not None else "—"


def _latencia_total(a: dict) -> int | None:
    partes = [e.get("latency_ms") for e in a.get("evaluations", [])] + [a.get("improvement_latency_ms")]
    partes = [p for p in partes if p is not None]
    return sum(partes) if partes else None


def _media_de(valores: list) -> str:
    valores = [v for v in valores if v is not None]
    if not valores:
        return "—"
    if len(valores) == 1:
        return f"{valores[0]:.1f}"
    return f"{statistics.mean(valores):.1f} ± {statistics.stdev(valores):.1f}"


def informe(salida: Path) -> None:
    manifiesto, filas = _cargar(salida)
    resultados = [(caso, n, a, hijo, verificar(caso, a, hijo)) for caso, n, a, hijo in filas]

    # CSV: una fila por corrida.
    with (salida / "resultados.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "caso", "corrida", "analysis_id", "estado", "input_mode", "evaluador", "mejorador",
            "puntaje_original", "alta_calidad", "puntaje_mejorado", "delta", "version_recomendada",
            "terminos_ambiguos", "preguntas", "pendientes", "valores_sin_respaldo",
            "latencia_total_s", "tokens_evaluacion_original", "puntaje_final_tras_aclarar",
            "verificaciones_requeridas_ok", "verificaciones_requeridas", "cumple",
        ])
        for caso, n, a, hijo, vs in resultados:
            orig = _evaluacion(a, "original")
            mej = _evaluacion(a, "improved")
            imp = a.get("improvement") or {}
            req = [v for v in vs if v.requerida]
            w.writerow([
                caso, n, a["id"], a["status"], a.get("input_mode"), a["evaluator_model"], a["improver_model"],
                orig["global_score"] if orig else "", orig["is_high_quality"] if orig else "",
                mej["global_score"] if mej else "", a.get("score_delta") if a.get("score_delta") is not None else "",
                a.get("recommended_version") or "",
                len(orig.get("ambiguous_terms") or []) if orig else "",
                len(orig.get("clarification_questions") or []) if orig else "",
                len(imp.get("pending_items") or []), len(imp.get("unsupported_values") or []),
                _seg(_latencia_total(a)),
                (orig["prompt_tokens"] or 0) + (orig["completion_tokens"] or 0) if orig else "",
                _puntaje_final(hijo) if hijo else "",
                sum(v.ok for v in req), len(req), all(v.ok for v in req),
            ])

    # Markdown.
    L: list[str] = []
    cfg = manifiesto.get("configuracion", {})
    modelos = sorted({(a["evaluator_model"], a["improver_model"]) for _, _, a, _, _ in resultados})
    L += [
        "# Punto 3 — Casos mínimos de prueba (Componente 1, sección 4.4)",
        "",
        "> Archivo generado por `scripts/casos_requisitos.py informe` a partir de los JSON de",
        "> `corridas/`. No editar a mano: la revisión humana está en `REVISION_MANUAL.md`.",
        "",
        "## Condiciones de ejecución",
        "",
        f"- Ejecutado: {manifiesto['ejecutado_en']} (UTC) contra `{manifiesto['servidor']}`",
        f"- Commit: `{manifiesto['commit'][:10]}`"
        + (" (con cambios sin commit)" if manifiesto.get("cambios_sin_commit") else ""),
        f"- Repeticiones por caso (A, B, C): {manifiesto['repeticiones']}",
    ]
    for ev, mj in modelos:
        L.append(f"- Evaluador: `{ev}` · Mejorador: `{mj}`")
    for k, v in cfg.items():
        L.append(f"- {k}: `{v}`")
    L += [
        "- Fórmula: Requirements Quality Score = promedio de los 10 criterios (1-10) × 10; "
        "alta calidad = ≥ 80 y ningún criterio < 6.",
        "",
        "## Resumen",
        "",
        "| Caso | Tipo | Corridas que cumplen | Puntaje original | Puntaje mejorado | Delta | Latencia total (s) |",
        "|---|---|---|---|---|---|---|",
    ]
    for caso in ("A", "B", "C", "D"):
        del_caso = [r for r in resultados if r[0] == caso]
        if not del_caso:
            L.append(f"| {caso} | {CASOS[caso]['tipo']} | sin ejecutar | — | — | — | — |")
            continue
        cumplen = sum(all(v.ok for v in vs if v.requerida) for *_, vs in del_caso)
        origs = [(_evaluacion(a, "original") or {}).get("global_score") for _, _, a, _, _ in del_caso]
        mejs = [(_evaluacion(a, "improved") or {}).get("global_score") for _, _, a, _, _ in del_caso]
        deltas = [a.get("score_delta") for _, _, a, _, _ in del_caso]
        lats = [(_latencia_total(a) or 0) / 1000 for _, _, a, _, _ in del_caso]
        L.append(
            f"| {caso} | {CASOS[caso]['tipo']} | **{cumplen}/{len(del_caso)}** | {_media_de(origs)} | "
            f"{_media_de(mejs)} | {_media_de(deltas)} | {_media_de(lats)} |"
        )
    L += ["", "Valores: media ± desviación estándar entre corridas.", ""]

    for caso in ("A", "B", "C", "D"):
        del_caso = [r for r in resultados if r[0] == caso]
        if not del_caso:
            continue
        datos = CASOS[caso]
        L += [f"## Caso {caso} — {datos['tipo']}", "", f"**Esperado (enunciado):** {datos['esperado']}", ""]
        if "requirement" in datos:
            L += ["**Entrada:**", "", "```text", datos["requirement"], "```", ""]
        if "aclaracion" in datos:
            L += ["**Respuestas del stakeholder usadas al aclarar:**", "", "```text", datos["aclaracion"], "```", ""]

        descripciones = {v.codigo: (v.descripcion, v.requerida) for *_, vs in del_caso for v in vs}
        codigos = list(dict.fromkeys(c for *_, vs in del_caso for c in (v.codigo for v in vs)))
        L += ["| Verificación | " + " | ".join(f"Corrida {n}" for _, n, *_ in del_caso) + " |",
              "|---|" + "---|" * len(del_caso)]
        for c in codigos:
            desc, req = descripciones[c]
            celdas = []
            for *_, vs in del_caso:
                v = next((x for x in vs if x.codigo == c), None)
                celdas.append("—" if v is None else f"{'✅' if v.ok else '❌'} {v.detalle}".strip())
            L.append(f"| **{c}**{'' if req else ' (informativa)'} {desc} | " + " | ".join(celdas) + " |")
        L.append("")

        for _, n, a, hijo, _ in del_caso:
            orig = _evaluacion(a, "original")
            L += [f"<details><summary>Corrida {n} — análisis <code>{a['id']}</code></summary>", ""]
            if a.get("input_mode") == "voice":
                L += [f"**Transcripción:** {a['original_requirement']}", ""]
            if orig:
                L += [f"**Diagnóstico:** {orig['summary']}", ""]
                L += ["| Criterio | Original | Mejorado | Hallazgo (original) |", "|---|---|---|---|"]
                mej = _evaluacion(a, "improved")
                for c in orig["criteria"]:
                    cm = _criterio(mej, c["criterion"])
                    hallazgo = c["finding"].replace("|", "/").replace("\n", " ")
                    L.append(f"| {c['criterion']} | {c['score']} | {cm['score'] if cm else '—'} | {hallazgo} |")
                L.append("")
                if orig.get("clarification_questions"):
                    L += ["**Preguntas:**", ""] + [f"- {p}" for p in orig["clarification_questions"]] + [""]
            if a.get("improved_requirement"):
                L += ["**Requisito mejorado:**", "", "```text", a["improved_requirement"], "```", ""]
                crit = (a.get("improvement") or {}).get("acceptance_criteria") or []
                if crit:
                    L += ["**Criterios de aceptación:**", ""] + [f"- {x}" for x in crit] + [""]
            if hijo:
                mej_h = _evaluacion(hijo, "improved")
                L += [f"**Tras responder las preguntas** (análisis `{hijo['id']}`): estado {hijo['status']}, "
                      f"puntaje original {(_evaluacion(hijo, 'original') or {}).get('global_score')}, "
                      f"mejorado {mej_h['global_score'] if mej_h else '—'}.", ""]
                if hijo.get("improved_requirement"):
                    L += ["```text", hijo["improved_requirement"], "```", ""]
            if a.get("tts_log"):
                L += ["**Lecturas en voz alta registradas:**", ""]
                L += [f"- {e['played_at']} · {e['voice']} ({e['language']}) · {e['processing']}" for e in a["tts_log"]]
                L.append("")
            L += ["</details>", ""]

    (salida / "RESULTADOS.md").write_text("\n".join(L), encoding="utf-8")
    print(f"Generados {salida / 'resultados.csv'} y {salida / 'RESULTADOS.md'}")
    for caso, n, a, hijo, vs in resultados:
        fallidas = [v.codigo for v in vs if v.requerida and not v.ok]
        print(f"  {caso}{n}: {'CUMPLE' if not fallidas else 'NO CUMPLE ' + ', '.join(fallidas)}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--salida", type=Path, default=SALIDA_POR_DEFECTO)
    sub = p.add_subparsers(dest="comando", required=True)
    e = sub.add_parser("ejecutar", help="ejecuta A, B y C contra la API y guarda la evidencia")
    e.add_argument("--repeticiones", type=int, default=3)
    e.add_argument("--limite-s", type=int, default=1500, help="tiempo máximo por análisis")
    v = sub.add_parser("voz", help="exporta un análisis hecho por voz desde la interfaz (caso D)")
    v.add_argument("--id", required=True)
    sub.add_parser("informe", help="verifica los JSON guardados y genera resultados.csv y RESULTADOS.md")
    args = p.parse_args()

    if args.comando == "ejecutar":
        asyncio.run(ejecutar(args.base_url, args.repeticiones, args.salida, args.limite_s))
        informe(args.salida)
    elif args.comando == "voz":
        exportar_voz(args.base_url, args.id, args.salida)
        informe(args.salida)
    else:
        informe(args.salida)


if __name__ == "__main__":
    main()
