"""Demostración: ¿qué cambia cuando la especificación es la fuente de verdad?

Cambio pedido por el equipo de seguridad: el bloqueo pasa de 15 a 30 minutos.
Se ejecuta de dos formas, cada una en una COPIA temporal de la cadena
(specs/, src/, tests/sdd/, sdd/), para no alterar la cadena aprobada:

A. Instrucción temporal: se le pide el cambio directamente al modelo de
   mantenimiento (prompt aprobado de la fase 7), que modifica el código.
B. Especificación primero: se actualiza el requisito (REQ-AUT-03 v2, validado
   con el motor de requisitos), luego la especificación (v1.1.0), y el cambio
   del código se deriva de la diferencia de la especificación.

En cada etapa se ejecutan los mismos Quality Gates: pruebas de tests/sdd
(conformidad con la especificación, suite generada, contrato) y el verificador
de trazabilidad.

    python scripts/sdd_demo_cambio.py
"""

import asyncio
import difflib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from benchmarks.calificadores_sondeo import _suite_generada
from benchmarks.proveedores import generar_con_reintentos
from scripts.benchmark import cargar_modelos
from scripts.sdd_cadena import SELECCION, bloque
from sdd.esquema import Especificacion, huella
from sdd.parches import aplicar

SALIDA = RAIZ / "evidence" / "punto8_sdd" / "demostracion"


def copiar_cadena(destino: Path) -> None:
    for parte in ("specs", "src", "tests/sdd", "sdd", "context"):
        shutil.copytree(RAIZ / parte, destino / parte, ignore=shutil.ignore_patterns("__pycache__"))
    (destino / "pytest.ini").write_text("[pytest]\npythonpath = . src\n", encoding="utf-8")


def _en_copia(raiz: Path, *args: str) -> subprocess.CompletedProcess:
    """Ejecuta Python dentro de la copia: su sdd/ trabaja sobre los specs/ y src/ de la copia."""
    env = {"PYTHONPATH": f"{raiz};{raiz / 'src'}", "SYSTEMROOT": r"C:\Windows", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, *args], cwd=raiz, capture_output=True, text=True, encoding="utf-8",
                          env=env, timeout=300, check=False)


def _diff(a: Path, b: Path) -> str:
    """Diferencias de los módulos .py entre dos copias del paquete."""
    partes: list[str] = []
    for archivo in sorted({p.name for p in a.glob("*.py")} | {p.name for p in b.glob("*.py")}):
        viejo = (a / archivo).read_text(encoding="utf-8").splitlines() if (a / archivo).exists() else []
        nuevo = (b / archivo).read_text(encoding="utf-8").splitlines() if (b / archivo).exists() else []
        partes += difflib.unified_diff(viejo, nuevo, f"aprobado/{archivo}", f"cambiado/{archivo}", lineterm="")
    return "\n".join(partes)


def _reescribe_sello(ejecucion: dict) -> bool:
    """¿La propuesta del modelo edita la línea de sello (se "autoaprueba")?"""
    return bool(re.search(r"^\+#\s*Spec:", ejecucion["resultado"]["contenido"] or "", re.MULTILINE))


def gates(raiz: Path) -> dict:
    """Pruebas de tests/sdd y verificador de trazabilidad sobre una copia."""
    p = _en_copia(raiz, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/sdd")
    t = _en_copia(raiz, "-c", ("import json; from sdd import trazabilidad as t; "
                              "s, r = t.verificar(); print(json.dumps(r.errores, ensure_ascii=False))"))
    return {"pytest_resumen": (p.stdout.strip().splitlines() or [""])[-1],
            "pruebas_fallidas": re.findall(r"^FAILED (\S+)", p.stdout, re.MULTILINE),
            "trazabilidad": json.loads(t.stdout) if t.returncode == 0 else [f"error: {t.stderr[-300:]}"]}


def aplicar_diff(raiz: Path, salida: str) -> dict[str, list[str]]:
    """Aplica los diffs del modelo al paquete de la copia (sdd/parches.py)."""
    return aplicar(salida, raiz / "src" / "auth_lockout")


async def llamar_fase(fase: int, variables: dict[str, str]) -> dict:
    """Ejecuta el prompt aprobado de una fase con el modelo elegido en el punto 7."""
    env = dotenv_values(RAIZ / ".env")
    modelos, params, config = cargar_modelos()
    cfg_fase = next(f for f in SELECCION["fases"] if f["fase"] == fase)
    cfg = next(m for m in modelos if m.modelo == cfg_fase["modelo"])
    texto = (RAIZ / cfg_fase["prompt"]).read_text(encoding="utf-8")
    for k, v in variables.items():
        texto = texto.replace("{{" + k + "}}", v)
    async with httpx.AsyncClient(timeout=1800) as c:
        res = await generar_con_reintentos(cfg, [{"role": "user", "content": texto}], params,
                                           max_intentos=config["reintentos"]["max_intentos"], client=c,
                                           nvidia_base_url=env["NVIDIA_BASE_URL"], nvidia_api_key=env["NVIDIA_API_KEY"])
    return {"fase_sdlc": fase, "modelo": cfg.modelo, "prompt_enviado": texto, "resultado": res.a_dict()}


def _codigo(raiz: Path) -> str:
    # Cada módulo ya empieza con su línea "# File:".
    return "\n\n".join(p.read_text(encoding="utf-8") for p in sorted((raiz / "src" / "auth_lockout").glob("*.py")))


async def mantenimiento(raiz: Path, incidencia: str, metricas: str) -> dict:
    return await llamar_fase(7, {"CODIGO_ACTUAL": _codigo(raiz), "INCIDENCIA_O_CAMBIO": incidencia, "METRICAS": metricas})


async def regenerar_pruebas(raiz: Path) -> tuple[dict, bool]:
    """Fase 5 con la especificación nueva: reemplaza la suite generada. Devuelve (ejecución, reemplazada)."""
    especificacion = "\n\n---\n\n".join((raiz / "specs" / n).read_text(encoding="utf-8")
                                         for n in ("requirements.md", "acceptance_criteria.md", "specification.md"))
    ej = await llamar_fase(5, {"REQUISITOS_Y_CRITERIOS": especificacion, "CODIGO_A_PROBAR": _codigo(raiz)})
    suite = _suite_generada(ej["resultado"]["contenido"] or "")
    if suite is None:
        return ej, False
    destino = raiz / "tests" / "sdd" / "test_req_aut_03_generadas.py"
    destino.write_text("# Regenerada por la fase de Testing (Kimi K3) desde SPEC-AUT-03 v1.1.0 (demostración).\n"
                       + suite.rstrip() + "\n", encoding="utf-8")
    return ej, True


async def validar_requisito(texto: str, contexto: str) -> dict:
    async with httpx.AsyncClient(base_url="http://localhost:8000", timeout=60) as c:
        r = await c.post("/api/requirements", json={"requirement": texto, "project_context": contexto})
        r.raise_for_status()
        aid, t0, fallos = r.json()["id"], time.monotonic(), 0
        while True:
            try:
                a = (await c.get(f"/api/requirements/{aid}")).json()
                fallos = 0
            except httpx.TransportError:
                # Un corte momentáneo al consultar el estado no debe perder el análisis
                # (mismo caso que en scripts/casos_requisitos.py).
                fallos += 1
                if fallos > 5:
                    raise
                await asyncio.sleep(5)
                continue
            if a["status"] in ("COMPLETED", "ERROR", "NEEDS_CLARIFICATION") or time.monotonic() - t0 > 900:
                return a
            await asyncio.sleep(5)


def metricas_de(g: dict) -> str:
    problemas = f": {'; '.join(g['trazabilidad'])}" if g["trazabilidad"] else ""
    return (f"- Pruebas de tests/sdd: {g['pytest_resumen']}.\n"
            f"- Pruebas fallidas: {', '.join(g['pruebas_fallidas']) or 'ninguna'}.\n"
            f"- Verificador de trazabilidad: {len(g['trazabilidad'])} problemas{problemas}.")


def especificacion_v1_1(raiz: Path) -> tuple[str, str]:
    """Nueva versión de la especificación: bloqueo de 30 minutos. Devuelve (huella v1, huella v1.1)."""
    ruta = raiz / "specs" / "specification.json"
    h_v1 = huella(ruta)
    texto = ruta.read_text(encoding="utf-8").replace("15 minutos", "30 minutos")
    spec = json.loads(texto)
    spec["version"] = "1.1.0"
    spec["parametros"]["bloqueo_minutos"] = 30
    Especificacion.model_validate(spec)
    ruta.write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _en_copia(raiz, "-m", "sdd.render")
    return h_v1, huella(ruta)


def sellar(raiz: Path) -> None:
    _en_copia(raiz, "-m", "sdd.trazabilidad", "--sellar")


def resumen(etiqueta: str, g: dict) -> None:
    print(f"{etiqueta}: {g['pytest_resumen']} | trazabilidad: {len(g['trazabilidad'])} problemas", flush=True)


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    SALIDA.mkdir(parents=True, exist_ok=True)
    registro: dict = {"ejecutado_utc": datetime.now(UTC).isoformat(), "cambio": "bloqueo de 15 a 30 minutos"}

    # ---- A. Instrucción temporal: el cambio va directo al código ----------------
    with tempfile.TemporaryDirectory() as d:
        raiz = Path(d)
        copiar_cadena(raiz)
        base = gates(raiz)
        resumen("A0 cadena aprobada", base)
        pedido = ("El equipo de seguridad pide que, a partir de ahora, la cuenta quede bloqueada 30 minutos "
                  "en lugar de 15 tras los intentos fallidos. Hacer el cambio en el código.")
        a = await mantenimiento(raiz, pedido, metricas_de(base))
        parche = aplicar_diff(raiz, a["resultado"]["contenido"])
        cambiados = sorted({h.split(":")[0] for h in parche["aplicados"]})
        g = gates(raiz)
        resumen(f"A1 cambio del modelo aplicado en {cambiados or 'ningún archivo'}", g)
        registro["A_instruccion_temporal"] = {
            "pedido": pedido, "mantenimiento": a, "archivos_cambiados": cambiados, "parche": parche, "gates_antes": base,
            "el_modelo_reescribio_el_sello": _reescribe_sello(a),
            "gates_despues": g, "especificacion_cambiada": False,
            "diff_codigo": _diff(RAIZ / "src" / "auth_lockout", raiz / "src" / "auth_lockout")}

    # ---- B. Especificación primero ---------------------------------------------
    with tempfile.TemporaryDirectory() as d:
        raiz = Path(d)
        copiar_cadena(raiz)
        req_v1 = bloque(RAIZ / "specs" / "requirements.md", "requisito")
        contexto = bloque(RAIZ / "specs" / "requirements.md", "contexto")
        req_v2 = req_v1.replace("15 minutos", "30 minutos")
        assert req_v2.count("30 minutos") == 3 and "15" not in req_v2, req_v2
        # B1. El requisito nuevo pasa por el motor de requisitos, como cualquier requisito.
        analisis = await validar_requisito(req_v2, contexto)
        ev = next((e for e in analisis.get("evaluations", []) if e.get("stage") == "original"), {})
        print(f"B1 REQ-AUT-03 v2 validado: estado={analisis['status']} puntaje={ev.get('global_score')} "
              f"alta_calidad={ev.get('is_high_quality')}", flush=True)
        # B2. Nueva versión del requisito y de la especificación; los documentos se regeneran.
        req_md = raiz / "specs" / "requirements.md"
        req_md.write_text(req_md.read_text(encoding="utf-8").replace(req_v1, req_v2), encoding="utf-8")
        h_v1, h_v11 = especificacion_v1_1(raiz)
        g_spec = gates(raiz)
        resumen(f"B2 especificación v1.1.0 (huella {h_v1} → {h_v11})", g_spec)
        # B3. El cambio del código se deriva de la diferencia de la especificación.
        incidencia = ("CHG-AUT-03-01: la especificación SPEC-AUT-03 pasó de v1.0.1 a v1.1.0 porque el requisito "
                      "REQ-AUT-03 v2 (validado) fija el bloqueo en 30 minutos. Único cambio de la especificación: "
                      "parametros.bloqueo_minutos 15 → 30 (y los textos de RB-3, RB-6 y AC-AUT-03-01/02/03 que lo "
                      "mencionan). Adecuar el código a la especificación v1.1.0 (componente ARCH-03 PolicyConfiguration).")
        b = await mantenimiento(raiz, incidencia, metricas_de(g_spec))
        parche = aplicar_diff(raiz, b["resultado"]["contenido"])
        cambiados = sorted({h.split(":")[0] for h in parche["aplicados"]})
        g_codigo = gates(raiz)
        resumen(f"B3 código adecuado en {cambiados or 'ningún archivo'} (antes de sellar)", g_codigo)
        # B3b. Las pruebas también derivan de la especificación: la fase 5 las regenera desde v1.1.0.
        p, reemplazada = await regenerar_pruebas(raiz)
        g_pruebas = gates(raiz)
        resumen(f"B3b pruebas regeneradas desde v1.1.0 ({'suite reemplazada' if reemplazada else 'SIN suite'})",
                g_pruebas)
        # B4. Revisión humana: si todas las pruebas pasan, se sella contra la especificación nueva.
        sellado = not g_pruebas["pruebas_fallidas"]
        if sellado:
            sellar(raiz)
        g_final = gates(raiz)
        resumen(f"B4 {'sellado' if sellado else 'NO sellado (pruebas fallidas)'}", g_final)
        registro["B_especificacion_primero"] = {
            "requisito_v2": req_v2, "validacion_requisito_v2": analisis, "huella_v1_0_1": h_v1, "huella_v1_1_0": h_v11,
            "gates_tras_cambiar_la_especificacion": g_spec, "mantenimiento": b, "archivos_cambiados": cambiados, "parche": parche,
            "el_modelo_reescribio_el_sello": _reescribe_sello(b),
            "gates_tras_adecuar_el_codigo": g_codigo, "pruebas_regeneradas": p, "suite_reemplazada": reemplazada,
            "gates_tras_regenerar_pruebas": g_pruebas, "sellado": sellado, "gates_tras_sellar": g_final,
            "diff_codigo": _diff(RAIZ / "src" / "auth_lockout", raiz / "src" / "auth_lockout")}

    (SALIDA / "demostracion.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"evidencia en {SALIDA.relative_to(RAIZ).as_posix()}/demostracion.json")


if __name__ == "__main__":
    asyncio.run(main())
