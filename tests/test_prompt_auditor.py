"""Tests del servicio Auditor (backend/services/prompt_auditor.py) con
`chat_completion` mockeado: verifican el camino de reintento sin depender
de la API real ni de que falle "por casualidad".
"""

import json

import pytest

from backend.schemas.auditor import GATE_PROPERTIES
from backend.services.nvidia_client import NvidiaChatResult
from backend.services.prompt_auditor import AuditorParseError, audit_prompt


def _nvidia_result(content: str, raw: dict) -> NvidiaChatResult:
    return NvidiaChatResult(
        content=content,
        reasoning_content=None,
        model="deepseek-ai/deepseek-v4-pro-0813",
        raw_response=raw,
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
    )


def _gate_completo(gate: str, status: str = "PASS") -> dict:
    return {
        "gate": gate,
        "status": status,
        "justification": "justificación de prueba",
        "properties": [
            {"property_id": pid, "property_name": nombre, "score": 7, "observation": "ok"}
            for pid, nombre in GATE_PROPERTIES[gate].items()
        ],
    }


def _auditor_response_valida_json() -> str:
    payload = {
        "gates": [_gate_completo(gate) for gate in GATE_PROPERTIES],
        "total_score": 80,
        "recommendations": ["ninguna"],
    }
    return json.dumps(payload)


class _ChatCompletionStub:
    """Sustituye a nvidia_client.chat_completion: devuelve la siguiente
    NvidiaChatResult de una lista precargada en cada llamada, sin red."""

    def __init__(self, resultados: list[NvidiaChatResult]):
        self._resultados = list(resultados)
        self.llamadas = 0

    async def __call__(self, model, messages, *, max_tokens=None, extra_payload=None):
        self.llamadas += 1
        if not self._resultados:
            raise AssertionError("chat_completion mockeado llamado más veces de las esperadas")
        return self._resultados.pop(0)


@pytest.mark.asyncio
async def test_json_invalido_en_ambos_intentos_lanza_auditor_parse_error(monkeypatch):
    primer_raw = {"marca": "primer intento"}
    segundo_raw = {"marca": "segundo intento"}
    stub = _ChatCompletionStub(
        [
            _nvidia_result("esto no es json {{{", raw=primer_raw),
            _nvidia_result("tampoco esto es json ]]]", raw=segundo_raw),
        ]
    )
    monkeypatch.setattr("backend.services.prompt_auditor.chat_completion", stub)

    with pytest.raises(AuditorParseError) as exc_info:
        await audit_prompt("cualquier prompt")

    assert stub.llamadas == 2  # exactamente un reintento, no más
    assert exc_info.value.raw_response == segundo_raw  # conserva el raw del ÚLTIMO intento, no el primero


@pytest.mark.asyncio
async def test_json_valido_pero_incompleto_en_ambos_intentos_tambien_falla(monkeypatch):
    # JSON sintácticamente válido, pero le faltan los 4 Gates del mapeo oficial
    json_incompleto = json.dumps({"gates": [], "total_score": 50, "recommendations": []})
    stub = _ChatCompletionStub(
        [
            _nvidia_result(json_incompleto, raw={"intento": 1}),
            _nvidia_result(json_incompleto, raw={"intento": 2}),
        ]
    )
    monkeypatch.setattr("backend.services.prompt_auditor.chat_completion", stub)

    with pytest.raises(AuditorParseError):
        await audit_prompt("cualquier prompt")

    assert stub.llamadas == 2


@pytest.mark.asyncio
async def test_no_reintenta_de_mas_cuando_el_primer_intento_ya_es_valido(monkeypatch):
    raw = {"choices": [{"message": {"content": "ok"}}]}
    stub = _ChatCompletionStub([_nvidia_result(_auditor_response_valida_json(), raw=raw)])
    monkeypatch.setattr("backend.services.prompt_auditor.chat_completion", stub)

    resultado = await audit_prompt("cualquier prompt")

    assert stub.llamadas == 1  # sin reintento: no debe consumir el segundo intento si no hace falta
    assert resultado.audit_response.total_score == 80
    assert resultado.gates_passed == 4


@pytest.mark.asyncio
async def test_json_invalido_en_el_primer_intento_pero_valido_en_el_reintento(monkeypatch):
    segundo_raw = {"marca": "segundo intento, válido"}
    stub = _ChatCompletionStub(
        [
            _nvidia_result("esto no es json {{{", raw={"intento": 1}),
            _nvidia_result(_auditor_response_valida_json(), raw=segundo_raw),
        ]
    )
    monkeypatch.setattr("backend.services.prompt_auditor.chat_completion", stub)

    resultado = await audit_prompt("cualquier prompt")

    assert stub.llamadas == 2
    assert resultado.audit_response.total_score == 80
    assert resultado.gates_passed == 4
    assert resultado.raw_response == segundo_raw
