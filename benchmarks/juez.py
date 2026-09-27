"""Jueces de calidad del benchmark (fases 1 y 3). Ver benchmarks/DISENO.md §4.

- Fase 1: Requirements Quality Score con el Evaluador de la plataforma
  (backend.services.requirements_evaluator), llamado con el modelo juez.
- Fase 3: revisión de arquitectura con la rúbrica de este módulo.

Cada juez responde en JSON validado con Pydantic; un JSON inválido se
reintenta una vez con el error como contexto (igual que las IAs de la
plataforma). Los fallos se devuelven, no se ocultan.
"""

import json
import time
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError, model_validator

from backend.config import get_settings
from backend.services.json_extraction import extract_json_block
from backend.services.nvidia_client import NvidiaClientError, chat_completion
from backend.services.requirements_evaluator import EvaluatorParseError, evaluate_requirement

IDS_RESTRICCION = ["R1", "R2", "R3", "R4", "R5", "R6"]
IDS_SPEC = ["SPEC-01", "SPEC-02", "SPEC-03", "SPEC-04", "SPEC-05", "SPEC-06"]


class RevisionRestriccion(BaseModel):
    id: str
    cumple: bool
    evidencia: str


class RevisionSpec(BaseModel):
    id: str
    cubierto: bool
    evidencia: str


class RevisionArquitectura(BaseModel):
    restricciones: list[RevisionRestriccion]
    specs: list[RevisionSpec]
    funcionalidades_inventadas: list[str] = Field(default_factory=list)
    datos_inventados: list[str] = Field(default_factory=list)
    contratos_completos: bool
    puntaje_revision: int = Field(ge=1, le=10)
    justificacion: str = Field(min_length=1)

    @model_validator(mode="after")
    def _ids_completos(self) -> "RevisionArquitectura":
        for campo, esperados in (("restricciones", IDS_RESTRICCION), ("specs", IDS_SPEC)):
            recibidos = [x.id for x in getattr(self, campo)]
            if sorted(recibidos) != sorted(esperados):
                raise ValueError(f"{campo}: se esperaban exactamente {esperados}, llegaron {recibidos}")
        return self


PROMPT_JUEZ_ARQUITECTURA = f"""Eres un revisor técnico de arquitectura de software. Recibes una ESPECIFICACIÓN (SPEC-01 a SPEC-06), unas RESTRICCIONES TÉCNICAS (R1 a R6) y una DOCUMENTACIÓN DE ARQUITECTURA escrita por otro modelo. Tu única tarea es evaluar esa documentación; no la reescribas.

Reglas:
1. Restricciones: para CADA una de R1 a R6 indica si la arquitectura la cumple. Una restricción se viola solo si la solución propuesta USA o INTRODUCE lo prohibido (por ejemplo, propone Redis como parte de la arquitectura). Mencionar una tecnología prohibida como alternativa DESCARTADA no es una violación. Cita la evidencia textual.
2. SPEC: para CADA uno de SPEC-01 a SPEC-06 indica si algún componente o contrato de la arquitectura lo cubre de forma concreta (no basta con nombrar el identificador). Cita la evidencia.
3. funcionalidades_inventadas: capacidades para el usuario que la especificación NO pide (por ejemplo SMS, notificaciones push, aplicación móvil, pagos, recomendaciones). Las decisiones de diseño internas (tablas, endpoints, módulos) NO son funcionalidades inventadas.
4. datos_inventados: valores o políticas de negocio presentados como requisitos que la especificación NO da (por ejemplo, un límite o un plazo distinto del especificado). Los valores que la especificación sí da (50 productos, 10 %, 24 horas, cada hora) no cuentan.
5. contratos_completos: true si cada interfaz relevante define entrada, salida y errores.
6. puntaje_revision (1-10), considerando cobertura, coherencia con las restricciones, claridad y ausencia de invenciones:
   9-10 lista para implementar sin cambios; 7-8 cambios menores; 5-6 huecos importantes; 3-4 incumple en lo esencial; 1-2 inutilizable.
7. Responde en español.

Devuelve EXCLUSIVAMENTE un JSON válido, sin texto adicional, con esta estructura:
{json.dumps({
    "restricciones": [{"id": r, "cumple": True, "evidencia": "cita breve"} for r in IDS_RESTRICCION],
    "specs": [{"id": s, "cubierto": True, "evidencia": "cita breve"} for s in IDS_SPEC],
    "funcionalidades_inventadas": [],
    "datos_inventados": [],
    "contratos_completos": True,
    "puntaje_revision": 7,
    "justificacion": "1-3 frases",
}, ensure_ascii=False, indent=2)}
"""


@dataclass
class ResultadoJuez:
    juez: str
    ok: bool
    datos: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    latencia_s: float | None = None
    raw: dict[str, Any] | None = None


def _json_forzado(modelo: str) -> dict[str, Any]:
    extra: dict[str, Any] = {}
    if get_settings().json_mode_for(modelo):
        extra["response_format"] = {"type": "json_object"}
    return extra


async def juzgar_arquitectura(modelo: str, especificacion: str, restricciones: str, documento: str) -> ResultadoJuez:
    mensajes = [
        {"role": "system", "content": PROMPT_JUEZ_ARQUITECTURA},
        {"role": "user", "content": (
            f"ESPECIFICACIÓN:\n{especificacion}\n\nRESTRICCIONES TÉCNICAS:\n{restricciones}\n\n"
            f"DOCUMENTACIÓN DE ARQUITECTURA A EVALUAR:\n{documento}"
        )},
    ]
    t0 = time.perf_counter()
    try:
        r = await chat_completion(model=modelo, messages=mensajes, extra_payload=_json_forzado(modelo))
        try:
            revision = RevisionArquitectura.model_validate_json(extract_json_block(r.content))
        except (ValueError, ValidationError) as primer_error:
            mensajes += [
                {"role": "assistant", "content": r.content},
                {"role": "user", "content": f"Tu JSON no es válido: {primer_error}. Devuelve solo el JSON corregido."},
            ]
            r = await chat_completion(model=modelo, messages=mensajes, extra_payload=_json_forzado(modelo))
            revision = RevisionArquitectura.model_validate_json(extract_json_block(r.content))
    except (ValueError, ValidationError) as e:
        return ResultadoJuez(modelo, False, error=f"JSON inválido tras reintentar: {str(e)[:300]}",
                             latencia_s=time.perf_counter() - t0)
    except NvidiaClientError as e:
        return ResultadoJuez(modelo, False, error=f"{type(e).__name__}: {str(e)[:300]}",
                             latencia_s=time.perf_counter() - t0, raw=getattr(e, "raw_response", None))
    return ResultadoJuez(modelo, True, datos=revision.model_dump(), latencia_s=time.perf_counter() - t0,
                         raw=r.raw_response)


async def juzgar_requisitos(modelo: str, requisitos: str, contexto: str) -> ResultadoJuez:
    t0 = time.perf_counter()
    try:
        r = await evaluate_requirement(requisitos, project_context=contexto, model=modelo)
    except EvaluatorParseError as e:
        return ResultadoJuez(modelo, False, error=f"JSON inválido tras reintentar: {str(e)[:300]}",
                             latencia_s=time.perf_counter() - t0, raw=e.raw_response)
    except NvidiaClientError as e:
        return ResultadoJuez(modelo, False, error=f"{type(e).__name__}: {str(e)[:300]}",
                             latencia_s=time.perf_counter() - t0, raw=getattr(e, "raw_response", None))
    e = r.evaluation
    return ResultadoJuez(modelo, True, latencia_s=time.perf_counter() - t0, raw=r.raw_response, datos={
        "global_score": e.global_score(), "is_high_quality": e.is_high_quality(),
        "criterios": {c.criterion: c.score for c in e.criteria},
        "ambiguous_terms": [t.term for t in e.ambiguous_terms], "summary": e.summary,
    })
