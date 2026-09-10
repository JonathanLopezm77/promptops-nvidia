"""Servicio Optimizer (IA 1): mejora un prompt, incorporando feedback de
iteraciones anteriores cuando existe. Nunca responde a la tarea del
prompt, solo lo reescribe (ver services/prompts/optimizer_system_prompt.py).

Si el JSON devuelto no valida, reintenta UNA vez con el error como
contexto (SPEC.md §17); si vuelve a fallar, lanza `OptimizerParseError`
con el raw_response para que el llamador lo persista y marque la
iteración como fallida, sin inventar valores por defecto.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from backend.config import get_settings
from backend.schemas.optimizer import OptimizerResponse
from backend.services.json_extraction import extract_json_block
from backend.services.nvidia_client import NvidiaChatResult, chat_completion
from backend.services.prompts.optimizer_system_prompt import OPTIMIZER_SYSTEM_PROMPT


class OptimizerParseError(Exception):
    """El Optimizer no devolvió JSON válido ni siquiera tras el reintento."""

    def __init__(self, message: str, raw_response: dict[str, Any]):
        super().__init__(message)
        self.raw_response = raw_response


@dataclass
class OptimizerResult:
    optimizer_response: OptimizerResponse
    raw_response: dict[str, Any]
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


async def optimize_prompt(
    original_prompt: str,
    *,
    previous_prompt: str | None = None,
    audit_feedback: str | None = None,
    human_feedback: str | None = None,
) -> OptimizerResult:
    settings = get_settings()
    messages = [
        {"role": "system", "content": OPTIMIZER_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": _build_user_message(
                original_prompt, previous_prompt, audit_feedback, human_feedback
            ),
        },
    ]

    resultado_llm = await chat_completion(model=settings.optimizer_model, messages=messages)

    try:
        return _a_resultado(resultado_llm, settings.optimizer_model)
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
        resultado_llm = await chat_completion(model=settings.optimizer_model, messages=messages)
        try:
            return _a_resultado(resultado_llm, settings.optimizer_model)
        except (ValueError, ValidationError) as segundo_error:
            raise OptimizerParseError(
                f"El Optimizer no devolvió JSON válido tras reintentar: {segundo_error}",
                raw_response=resultado_llm.raw_response,
            ) from segundo_error


def _a_resultado(resultado_llm: NvidiaChatResult, model: str) -> OptimizerResult:
    bloque = extract_json_block(resultado_llm.content)
    optimizer_response = OptimizerResponse.model_validate_json(bloque)
    return OptimizerResult(
        optimizer_response=optimizer_response,
        raw_response=resultado_llm.raw_response,
        model=model,
        prompt_tokens=resultado_llm.prompt_tokens,
        completion_tokens=resultado_llm.completion_tokens,
        total_tokens=resultado_llm.total_tokens,
    )


def _build_user_message(
    original_prompt: str,
    previous_prompt: str | None,
    audit_feedback: str | None,
    human_feedback: str | None,
) -> str:
    partes = [f"PROMPT A OPTIMIZAR:\n{original_prompt}"]
    if previous_prompt:
        partes.append(f"VERSIÓN DE LA ITERACIÓN ANTERIOR:\n{previous_prompt}")
    if audit_feedback:
        partes.append(f"FEEDBACK DE LA AUDITORÍA ANTERIOR:\n{audit_feedback}")
    if human_feedback:
        partes.append(f"FEEDBACK DEL HUMANO EN LA ITERACIÓN ANTERIOR:\n{human_feedback}")
    return "\n\n".join(partes)
