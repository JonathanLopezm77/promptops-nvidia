"""Servicio Mejorador de requisitos: produce una versión mejorada del
requisito a partir del diagnóstico del Evaluador, sin alterar la intención
original y sin inventar datos (usa [POR DEFINIR: ...]).

Usa OPTIMIZER_MODEL, el mismo rol de "reescritor" que el Optimizer de
prompts. No toca la base de datos. Hace como máximo dos reintentos, cada
uno una sola vez:

1. JSON inválido -> reintento con el error de validación; si vuelve a
   fallar, `ImproverParseError` con la respuesta cruda.
2. Valores numéricos sin respaldo (ver
   `RequirementImprovementResponse.unsupported_values`) -> reintento
   pidiendo reemplazarlos por [POR DEFINIR]. Si el modelo insiste, se
   acepta su respuesta pero los valores quedan en `unsupported_values`
   para que la interfaz los muestre como advertencia (no se ocultan).
"""

import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from backend.config import get_settings
from backend.schemas.requirements import (
    REQUIREMENT_CRITERIA,
    RequirementEvaluationResponse,
    RequirementImprovementResponse,
)
from backend.services.json_extraction import extract_json_block
from backend.services.nvidia_client import NvidiaChatResult, chat_completion
from backend.services.prompts.requirements_improver_system_prompt import (
    REQUIREMENTS_IMPROVER_SYSTEM_PROMPT,
)


class ImproverParseError(Exception):
    """El Mejorador no devolvió JSON válido ni siquiera tras el reintento."""

    def __init__(self, message: str, raw_response: dict[str, Any], model: str, latency_ms: int):
        super().__init__(message)
        self.raw_response = raw_response
        self.model = model
        self.latency_ms = latency_ms


@dataclass
class ImproverResult:
    improvement: RequirementImprovementResponse
    raw_response: dict[str, Any]
    model: str
    total_tokens: int | None
    latency_ms: int
    # Valores sin respaldo que siguen presentes tras el reintento de corrección.
    unsupported_values: list[str]
    # True si hubo que pedir la corrección de valores sin respaldo.
    unsupported_retry: bool = False


async def improve_requirement(
    requirement: str,
    evaluation: RequirementEvaluationResponse,
    *,
    project_context: str | None = None,
    clarifications: str | None = None,
) -> ImproverResult:
    settings = get_settings()
    model = settings.optimizer_model
    messages = [
        {"role": "system", "content": REQUIREMENTS_IMPROVER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_message(requirement, evaluation, project_context, clarifications),
        },
    ]
    extra_payload = {"response_format": {"type": "json_object"}} if settings.llm_json_mode else None
    inicio = time.perf_counter()
    tokens: list[int | None] = []

    async def llamar() -> NvidiaChatResult:
        resultado = await chat_completion(model=model, messages=messages, extra_payload=extra_payload)
        tokens.append(resultado.total_tokens)
        return resultado

    resultado_llm = await llamar()
    try:
        mejora = _parsear(resultado_llm)
    except (ValueError, ValidationError) as primer_error:
        messages.append({"role": "assistant", "content": resultado_llm.content})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Tu respuesta anterior no es un JSON válido según el esquema pedido. "
                    f"Error de validación: {primer_error}. "
                    "Devuelve EXCLUSIVAMENTE el JSON corregido, sin texto adicional."
                ),
            }
        )
        resultado_llm = await llamar()
        try:
            mejora = _parsear(resultado_llm)
        except (ValueError, ValidationError) as segundo_error:
            raise ImproverParseError(
                f"El Mejorador no devolvió JSON válido tras reintentar: {segundo_error}",
                raw_response=resultado_llm.raw_response,
                model=model,
                latency_ms=_ms_desde(inicio),
            ) from segundo_error

    fuentes = (requirement, project_context, clarifications)
    sin_respaldo = mejora.unsupported_values(*fuentes)
    reintento_valores = False
    if sin_respaldo:
        reintento_valores = True
        messages.append({"role": "assistant", "content": resultado_llm.content})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Usaste valores que no aparecen en el requisito, el contexto ni las "
                    f"aclaraciones: {', '.join(sin_respaldo)}. Eso es inventar datos. "
                    "Reemplaza cada uno por un marcador [POR DEFINIR: qué falta], agrégalo a "
                    "pending_items y devuelve EXCLUSIVAMENTE el JSON completo corregido."
                ),
            }
        )
        correccion_llm = await llamar()
        try:
            mejora = _parsear(correccion_llm)
            resultado_llm = correccion_llm
        except (ValueError, ValidationError):
            # La primera versión era válida: se conserva y queda la advertencia.
            pass
        sin_respaldo = mejora.unsupported_values(*fuentes)

    return ImproverResult(
        improvement=mejora,
        raw_response=resultado_llm.raw_response,
        model=model,
        total_tokens=sum(t for t in tokens if t is not None) if any(t is not None for t in tokens) else None,
        latency_ms=_ms_desde(inicio),
        unsupported_values=sin_respaldo,
        unsupported_retry=reintento_valores,
    )


def _parsear(resultado_llm: NvidiaChatResult) -> RequirementImprovementResponse:
    return RequirementImprovementResponse.model_validate_json(
        extract_json_block(resultado_llm.content)
    )


def _ms_desde(inicio: float) -> int:
    return round((time.perf_counter() - inicio) * 1000)


def _resumir_diagnostico(evaluation: RequirementEvaluationResponse) -> str:
    lineas = [f"Diagnóstico general: {evaluation.summary}"]
    for c in evaluation.criteria:
        nombre = REQUIREMENT_CRITERIA[c.criterion][0]
        linea = f"- {nombre}: {c.score}/10. {c.finding}"
        if c.recommendation:
            linea += f" Recomendación: {c.recommendation}"
        lineas.append(linea)
    if evaluation.ambiguous_terms:
        lineas.append(
            "Términos ambiguos: "
            + "; ".join(f"'{t.term}' ({t.reason})" for t in evaluation.ambiguous_terms)
        )
    if evaluation.is_compound:
        lineas.append("El requisito es compuesto: mezcla varios requisitos independientes.")
    if evaluation.missing_information:
        lineas.append("Información faltante: " + "; ".join(evaluation.missing_information))
    return "\n".join(lineas)


def _build_user_message(
    requirement: str,
    evaluation: RequirementEvaluationResponse,
    project_context: str | None,
    clarifications: str | None,
) -> str:
    partes = [
        f"REQUISITO ORIGINAL:\n{requirement}",
        f"DIAGNÓSTICO DEL EVALUADOR:\n{_resumir_diagnostico(evaluation)}",
    ]
    if project_context:
        partes.append(f"CONTEXTO DEL PROYECTO:\n{project_context}")
    if clarifications:
        partes.append(f"ACLARACIONES DEL STAKEHOLDER:\n{clarifications}")
    return "\n\n".join(partes)
