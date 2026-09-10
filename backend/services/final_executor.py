"""Servicio Executor final (IA 3): ejecuta el prompt ya aprobado por el
humano y produce la respuesta a la tarea original.

Recibe EXCLUSIVAMENTE el prompt aprobado — sin contexto de auditoría ni
de iteraciones anteriores (separación de roles, invariante #6 de
CLAUDE.md): el Executor no sabe que existió un Optimizer o un Auditor.

Mismo patrón de reintento que Optimizer/Auditor: un reintento ante JSON
inválido; si vuelve a fallar, lanza `ExecutorParseError` con el
raw_response para que el llamador (workflow.py) decida — este servicio
no toca la base de datos.
"""

import json
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from backend.config import get_settings
from backend.schemas.executor import ExecutorResponse
from backend.services.json_extraction import extract_json_block
from backend.services.nvidia_client import NvidiaChatResult, chat_completion
from backend.services.prompts.executor_system_prompt import EXECUTOR_SYSTEM_PROMPT


class ExecutorParseError(Exception):
    """El Executor no devolvió JSON válido ni siquiera tras el reintento."""

    def __init__(self, message: str, raw_response: dict[str, Any]):
        super().__init__(message)
        self.raw_response = raw_response


@dataclass
class ExecutorResult:
    executor_response: ExecutorResponse
    raw_response: dict[str, Any]
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


async def execute_prompt(approved_prompt: str) -> ExecutorResult:
    settings = get_settings()
    messages = [
        {"role": "system", "content": EXECUTOR_SYSTEM_PROMPT},
        {"role": "user", "content": approved_prompt},
    ]

    resultado_llm = await chat_completion(model=settings.executor_model, messages=messages)

    try:
        return _a_resultado(resultado_llm, settings.executor_model)
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
        resultado_llm = await chat_completion(model=settings.executor_model, messages=messages)
        try:
            return _a_resultado(resultado_llm, settings.executor_model)
        except (ValueError, ValidationError) as segundo_error:
            raise ExecutorParseError(
                f"El Executor no devolvió JSON válido tras reintentar: {segundo_error}",
                raw_response=resultado_llm.raw_response,
            ) from segundo_error


def _a_resultado(resultado_llm: NvidiaChatResult, model: str) -> ExecutorResult:
    bloque = extract_json_block(resultado_llm.content)
    datos = json.loads(bloque)

    # Algunos modelos (visto con mistral-nemotron) anidan la respuesta en un
    # objeto en vez de aplanarla a texto como pide el system prompt, p. ej.
    # {"response": {"ejemplo_basico": {...}, "ejemplo_avanzado": {...}}}.
    # El contenido sigue siendo válido y útil: se aplana a texto legible en
    # vez de descartar una respuesta real por no calzar el tipo exacto.
    if isinstance(datos, dict) and isinstance(datos.get("response"), (dict, list)):
        datos["response"] = json.dumps(datos["response"], indent=2, ensure_ascii=False)

    executor_response = ExecutorResponse.model_validate(datos)
    return ExecutorResult(
        executor_response=executor_response,
        raw_response=resultado_llm.raw_response,
        model=model,
        prompt_tokens=resultado_llm.prompt_tokens,
        completion_tokens=resultado_llm.completion_tokens,
        total_tokens=resultado_llm.total_tokens,
    )
