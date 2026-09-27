"""Servicio Evaluador de requisitos: califica un requisito con los 10
criterios de calidad del Parcial 1 (ver schemas/requirements.py). Nunca
reescribe el requisito; eso lo hace requirements_improver.py (separación de
roles, igual que Auditor y Optimizer).

Usa AUDITOR_MODEL, con el mismo `thinking: False` que el Auditor para
obtener JSON limpio. Si el JSON no valida, reintenta UNA vez con el error
como contexto; si vuelve a fallar lanza `EvaluatorParseError` con la
respuesta cruda. No toca la base de datos: eso es requirements_workflow.py.
"""

import time
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from backend.config import get_settings
from backend.schemas.requirements import RequirementEvaluationResponse
from backend.services.json_extraction import extract_json_block
from backend.services.nvidia_client import NvidiaChatResult, chat_completion
from backend.services.prompts.requirements_evaluator_system_prompt import (
    REQUIREMENTS_EVALUATOR_SYSTEM_PROMPT,
)

_EXTRA_PAYLOAD = {"chat_template_kwargs": {"thinking": False}}


class EvaluatorParseError(Exception):
    """El Evaluador no devolvió JSON válido ni siquiera tras el reintento."""

    def __init__(self, message: str, raw_response: dict[str, Any], model: str, latency_ms: int):
        super().__init__(message)
        self.raw_response = raw_response
        self.model = model
        self.latency_ms = latency_ms


@dataclass
class EvaluatorResult:
    evaluation: RequirementEvaluationResponse
    raw_response: dict[str, Any]
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int


async def evaluate_requirement(
    requirement: str,
    *,
    project_context: str | None = None,
    clarifications: str | None = None,
    model: str | None = None,
) -> EvaluatorResult:
    """`model` permite comparar modelos (benchmark); por defecto AUDITOR_MODEL."""
    settings = get_settings()
    model = model or settings.auditor_model
    extra_payload = dict(_EXTRA_PAYLOAD)
    if settings.json_mode_for(model):
        extra_payload["response_format"] = {"type": "json_object"}
    messages = [
        {"role": "system", "content": REQUIREMENTS_EVALUATOR_SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_message(requirement, project_context, clarifications)},
    ]
    inicio = time.perf_counter()

    resultado_llm = await chat_completion(model=model, messages=messages, extra_payload=extra_payload)
    try:
        return _a_resultado(resultado_llm, model, inicio)
    except (ValueError, ValidationError) as primer_error:
        messages.append({"role": "assistant", "content": resultado_llm.content})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Tu respuesta anterior no es un JSON válido según el esquema pedido. "
                    f"Error de validación: {primer_error}. "
                    "Devuelve EXCLUSIVAMENTE el JSON corregido, con los 10 criterios "
                    "obligatorios, sin texto adicional."
                ),
            }
        )
        resultado_llm = await chat_completion(model=model, messages=messages, extra_payload=extra_payload)
        try:
            return _a_resultado(resultado_llm, model, inicio)
        except (ValueError, ValidationError) as segundo_error:
            raise EvaluatorParseError(
                f"El Evaluador no devolvió JSON válido tras reintentar: {segundo_error}",
                raw_response=resultado_llm.raw_response,
                model=model,
                latency_ms=_ms_desde(inicio),
            ) from segundo_error


def _a_resultado(resultado_llm: NvidiaChatResult, model: str, inicio: float) -> EvaluatorResult:
    evaluation = RequirementEvaluationResponse.model_validate_json(
        extract_json_block(resultado_llm.content)
    )
    return EvaluatorResult(
        evaluation=evaluation,
        raw_response=resultado_llm.raw_response,
        model=model,
        prompt_tokens=resultado_llm.prompt_tokens,
        completion_tokens=resultado_llm.completion_tokens,
        latency_ms=_ms_desde(inicio),
    )


def _ms_desde(inicio: float) -> int:
    return round((time.perf_counter() - inicio) * 1000)


def _build_user_message(
    requirement: str, project_context: str | None, clarifications: str | None
) -> str:
    partes = [f"REQUISITO A EVALUAR:\n{requirement}"]
    if project_context:
        partes.append(f"CONTEXTO DEL PROYECTO:\n{project_context}")
    if clarifications:
        partes.append(f"ACLARACIONES DEL STAKEHOLDER:\n{clarifications}")
    return "\n\n".join(partes)
