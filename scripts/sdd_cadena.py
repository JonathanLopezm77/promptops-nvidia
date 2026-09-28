"""Cadena SDD del punto 8 (Componente 5): un requisito validado se convierte,
paso a paso, en especificación, contrato de arquitectura, código y pruebas.

    python scripts/sdd_cadena.py requisito        # 1. valida REQ-AUT-03 con el motor de requisitos (API local)
    python scripts/sdd_cadena.py especificacion   # 2. prompt aprobado de la fase 2 (Kimi K3)
    python scripts/sdd_cadena.py arquitectura     # 3. prompt aprobado de la fase 3 (Nemotron 3 Super)
    python scripts/sdd_cadena.py implementacion   # 4. prompt aprobado de la fase 4 (Kimi K3)
    python scripts/sdd_cadena.py pruebas          # 5. prompt aprobado de la fase 5 (Kimi K3)

Cada paso lee como entrada el artefacto APROBADO del paso anterior, que vive
en /specs, /src o /tests (no en la conversación con el modelo), y guarda la
ejecución completa (prompt, salida cruda, tokens, tiempos) en
evidence/punto8_sdd/ejecuciones/. El paso siguiente solo se habilita cuando el
artefacto anterior pasó su Quality Gate y fue aprobado (evidence/punto8_sdd/DECISIONES.md).
Modelos: la selección del punto 7 (benchmarks/seleccion_por_fase.json).
"""

import argparse
import asyncio
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx
from dotenv import dotenv_values

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from benchmarks.proveedores import generar_con_reintentos
from scripts.benchmark import cargar_modelos

SPECS, SRC, TESTS = RAIZ / "specs", RAIZ / "src", RAIZ / "tests" / "sdd"
EVIDENCIA = RAIZ / "evidence" / "punto8_sdd" / "ejecuciones"
RESTRICCIONES = RAIZ / "context" / "sdd_restricciones_tecnicas.md"
STACK = ("Python 3.12, solo biblioteca estándar. Paquete src/auth_lockout/ (un módulo por componente ARCH "
         "más __init__.py que exporte la API pública). Type hints en todas las firmas públicas. Lint con ruff "
         "(configuración por defecto). Pruebas con pytest: las escribe la fase de Testing, no esta fase. "
         "Sin dependencias externas, sin acceso a red, disco ni base de datos.")
SELECCION = json.loads((RAIZ / "benchmarks" / "seleccion_por_fase.json").read_text(encoding="utf-8"))


def bloque(ruta: Path, etiqueta: str) -> str:
    """Contenido del bloque ```<etiqueta> de un artefacto Markdown de /specs."""
    m = re.search(rf"```{etiqueta}\n(.*?)```", ruta.read_text(encoding="utf-8"), re.DOTALL)
    if not m:
        raise SystemExit(f"{ruta.relative_to(RAIZ)} no tiene un bloque ```{etiqueta}")
    return m.group(1).strip()


def prompt(fase: int, variables: dict[str, str]) -> str:
    cfg = next(f for f in SELECCION["fases"] if f["fase"] == fase)
    texto = (RAIZ / cfg["prompt"]).read_text(encoding="utf-8")
    for nombre, valor in variables.items():
        texto = texto.replace("{{" + nombre + "}}", valor)
    if re.findall(r"\{\{\s*[A-Z_]+\s*\}\}", texto):
        raise ValueError(f"fase {fase}: quedaron variables sin sustituir")
    return texto


async def llamar_modelo(paso: str, fase: int, variables: dict[str, str]) -> dict:
    env = dotenv_values(RAIZ / ".env")
    modelos, params, config = cargar_modelos()
    id_modelo = next(f for f in SELECCION["fases"] if f["fase"] == fase)["modelo"]
    cfg = next(m for m in modelos if m.modelo == id_modelo)
    texto = prompt(fase, variables)
    async with httpx.AsyncClient(timeout=1800) as c:
        t0 = time.perf_counter()
        res = await generar_con_reintentos(
            cfg, [{"role": "user", "content": texto}], params, max_intentos=config["reintentos"]["max_intentos"],
            client=c, nvidia_base_url=env["NVIDIA_BASE_URL"], nvidia_api_key=env["NVIDIA_API_KEY"])
    r = res.a_dict()
    registro = {"paso": paso, "fase_sdlc": fase, "modelo": id_modelo, "parametros": config["parametros"],
                "ejecutado_utc": datetime.now(UTC).isoformat(), "variables": variables,
                "prompt_enviado": texto, "resultado": r}
    guardar(paso, registro)
    solo_razon = bool(r["razonamiento"]) and r["contenido"].strip() == r["razonamiento"].strip()
    print(f"{paso}: {'OK' if res.ok and not solo_razon else 'FALLO'} modelo={id_modelo} "
          f"finish={r['finish_reason']} tokens={r['tokens_entrada']}/{r['tokens_salida']} "
          f"total={time.perf_counter() - t0:.0f}s intentos={r['intentos']}")
    return registro


def guardar(paso: str, registro: dict) -> None:
    EVIDENCIA.mkdir(parents=True, exist_ok=True)
    (EVIDENCIA / f"{paso}.json").write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pasos
# ---------------------------------------------------------------------------


async def requisito(base_url: str) -> None:
    """1. Necesidad -> Requirement: el requisito se valida con el motor de la plataforma."""
    texto, contexto = bloque(SPECS / "requirements.md", "requisito"), bloque(SPECS / "requirements.md", "contexto")
    async with httpx.AsyncClient(base_url=base_url, timeout=60) as c:
        r = await c.post("/api/requirements", json={"requirement": texto, "project_context": contexto})
        r.raise_for_status()
        analisis_id, inicio = r.json()["id"], time.monotonic()
        while True:
            a = (await c.get(f"/api/requirements/{analisis_id}")).json()
            if a["status"] in ("COMPLETED", "ERROR", "NEEDS_CLARIFICATION"):
                break
            if time.monotonic() - inicio > 900:
                raise SystemExit(f"el análisis {analisis_id} no terminó en 15 min")
            await asyncio.sleep(5)
    guardar("1_requisito", {"paso": "1_requisito", "ejecutado_utc": datetime.now(UTC).isoformat(),
                            "entrada": {"requirement": texto, "project_context": contexto}, "analisis": a})
    ev = next((e for e in a.get("evaluations", []) if e.get("stage") == "original"), None) or {}
    print(f"1_requisito: análisis {analisis_id} estado={a['status']} "
          f"puntaje={ev.get('global_score')} alta_calidad={ev.get('is_high_quality')}")


async def especificacion() -> None:
    """2. Requirement -> Acceptance Criteria + Specification."""
    await llamar_modelo("2_especificacion", 2, {"REQUISITOS_APROBADOS": bloque(SPECS / "requirements.md", "requisito")})


async def arquitectura() -> None:
    """3. Specification -> Architecture Contract."""
    await llamar_modelo("3_arquitectura", 3, {
        "ESPECIFICACION_APROBADA": (SPECS / "specification.md").read_text(encoding="utf-8"),
        "RESTRICCIONES_TECNICAS": RESTRICCIONES.read_text(encoding="utf-8")})


async def implementacion() -> None:
    """4. Architecture Contract -> Implementation."""
    await llamar_modelo("4_implementacion", 4, {
        "DISENO_Y_CONTRATOS": (SPECS / "architecture_contract.md").read_text(encoding="utf-8")
        + "\n\n---\n\n" + (SPECS / "specification.md").read_text(encoding="utf-8"),
        "STACK_TECNOLOGICO": STACK})


async def pruebas() -> None:
    """5. Implementation + Acceptance Criteria -> Tests."""
    # Cada módulo ya empieza con su línea "# File:" (la exige el prompt de implementación).
    codigo = "\n\n".join(p.read_text(encoding="utf-8") for p in sorted((SRC / "auth_lockout").glob("*.py")))
    await llamar_modelo("5_pruebas", 5, {
        "REQUISITOS_Y_CRITERIOS": "\n\n---\n\n".join(
            (SPECS / n).read_text(encoding="utf-8")
            for n in ("requirements.md", "acceptance_criteria.md", "specification.md")),
        "CODIGO_A_PROBAR": codigo})


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("paso", choices=["requisito", "especificacion", "arquitectura", "implementacion", "pruebas"])
    p.add_argument("--base-url", default="http://localhost:8000")
    a = p.parse_args()
    if a.paso == "requisito":
        asyncio.run(requisito(a.base_url))
    else:
        asyncio.run({"especificacion": especificacion, "arquitectura": arquitectura,
                     "implementacion": implementacion, "pruebas": pruebas}[a.paso]())


if __name__ == "__main__":
    main()
