"""Tests de los schemas Pydantic del Optimizer (IA 1) y del Executor (IA 3)."""

import pytest
from pydantic import ValidationError

from backend.schemas.executor import ExecutorResponse
from backend.schemas.optimizer import OptimizerResponse


def test_optimizer_response_valido():
    payload = {
        "original_prompt": "resume esto",
        "analysis": "el prompt es ambiguo",
        "improved_prompt": "Resume el siguiente texto en 3 frases: {texto}",
        "changes": ["se añadió restricción de longitud"],
        "reasoning_summary": "se acotó el formato de salida",
    }
    optimizado = OptimizerResponse.model_validate(payload)
    assert optimizado.changes == ["se añadió restricción de longitud"]


def test_optimizer_response_sin_improved_prompt_falla():
    payload = {
        "original_prompt": "resume esto",
        "analysis": "el prompt es ambiguo",
        "changes": [],
        "reasoning_summary": "sin cambios",
    }
    with pytest.raises(ValidationError):
        OptimizerResponse.model_validate(payload)


def test_executor_response_valido():
    ejecucion = ExecutorResponse.model_validate({"response": "respuesta final del modelo"})
    assert ejecucion.response == "respuesta final del modelo"


def test_executor_response_vacio_falla():
    with pytest.raises(ValidationError):
        ExecutorResponse.model_validate({})
