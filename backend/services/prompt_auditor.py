"""Servicio Auditor (IA 2): evalúa un prompt contra los 4 Quality Gates
oficiales (ver services/prompts/auditor_system_prompt.py y
schemas/auditor.py). Nunca responde a la tarea del prompt auditado ni lo
reescribe (separación de roles, invariante #6 de CLAUDE.md).

Usa AUDITOR_MODEL con `chat_template_kwargs: {"thinking": False}` para
pedir JSON limpio sin razonamiento intercalado.

Si el JSON no valida (malformado, o válido pero incompleto: falta un
Gate, o a un Gate le faltan propiedades de su mapeo), reintenta UNA vez
con el error como contexto. Si vuelve a fallar, lanza `AuditorParseError`
con el raw_response: el llamador (workflow.py, bloque posterior) es quien
decide guardar la fila con `parse_ok=false` y pasar el run a ERROR — este
servicio no toca la base de datos, igual que prompt_optimizer.py.
"""

from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from backend.config import get_settings
from backend.schemas.auditor import AuditorResponse
from backend.services.json_extraction import extract_json_block
from backend.services.nvidia_client import NvidiaChatResult, chat_completion
from backend.services.prompts.auditor_system_prompt import AUDITOR_SYSTEM_PROMPT

# Desactiva el razonamiento intercalado de deepseek-v4-pro para obtener
# JSON limpio en `content` (ver memoria nvidia-kimi-latency / verificado
# contra la API real: no altera reasoning_content, que ya viene vacío en
# este modelo, pero es un parámetro aceptado y no rompe nada).
_EXTRA_PAYLOAD = {"chat_template_kwargs": {"thinking": False}}


class AuditorParseError(Exception):
    """El Auditor no devolvió JSON válido ni siquiera tras el reintento."""

    def __init__(self, message: str, raw_response: dict[str, Any]):
        super().__init__(message)
        self.raw_response = raw_response


@dataclass
class AuditorResult:
    audit_response: AuditorResponse
    raw_response: dict[str, Any]
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    gates_passed: int
    gates_failed: int
    gates_not_applicable: int
    gates_score: float | None


async def audit_prompt(prompt_to_audit: str) -> AuditorResult:
    settings = get_settings()
    messages = [
        {"role": "system", "content": AUDITOR_SYSTEM_PROMPT},
        {"role": "user", "content": f"PROMPT A AUDITAR:\n{prompt_to_audit}"},
    ]

    resultado_llm = await chat_completion(
        model=settings.auditor_model, messages=messages, extra_payload=_EXTRA_PAYLOAD
    )

    try:
        return _a_resultado(resultado_llm, settings.auditor_model)
    except (ValueError, ValidationError) as primer_error:
        messages.append({"role": "assistant", "content": resultado_llm.content})
        messages.append(
            {
                "role": "user",
                "content": (
                    "Tu respuesta anterior no es un JSON válido según el esquema pedido. "
                    f"Error de validación: {primer_error}. "
                    "Devuelve EXCLUSIVAMENTE el JSON corregido, con los 4 Gates completos "
                    "y todas sus propiedades del mapeo, sin texto adicional."
                ),
            }
        )
        resultado_llm = await chat_completion(
            model=settings.auditor_model, messages=messages, extra_payload=_EXTRA_PAYLOAD
        )
        try:
            return _a_resultado(resultado_llm, settings.auditor_model)
        except (ValueError, ValidationError) as segundo_error:
            raise AuditorParseError(
                f"El Auditor no devolvió JSON válido tras reintentar: {segundo_error}",
                raw_response=resultado_llm.raw_response,
            ) from segundo_error


def _a_resultado(resultado_llm: NvidiaChatResult, model: str) -> AuditorResult:
    bloque = extract_json_block(resultado_llm.content)
    audit_response = AuditorResponse.model_validate_json(bloque)
    gates_passed, gates_failed, gates_not_applicable = audit_response.gate_counts()
    return AuditorResult(
        audit_response=audit_response,
        raw_response=resultado_llm.raw_response,
        model=model,
        prompt_tokens=resultado_llm.prompt_tokens,
        completion_tokens=resultado_llm.completion_tokens,
        total_tokens=resultado_llm.total_tokens,
        gates_passed=gates_passed,
        gates_failed=gates_failed,
        gates_not_applicable=gates_not_applicable,
        gates_score=audit_response.gates_score(),
    )
