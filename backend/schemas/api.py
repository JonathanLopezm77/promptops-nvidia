"""Schemas Pydantic de request/response de la API REST (distintos de los
schemas de las tres IAs en backend/schemas/{optimizer,auditor,executor}.py,
que validan lo que devuelve el LLM). `from_attributes=True` permite
construirlos directamente desde los modelos SQLAlchemy.
"""

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=1)


class IterateRequest(BaseModel):
    feedback: str = Field(min_length=1)


class EditRequest(BaseModel):
    prompt: str = Field(min_length=1)


class RejectRequest(BaseModel):
    feedback: str | None = None


class AutoIterateRequest(BaseModel):
    """No está en la lista literal de endpoints de CLAUDE.md: automatiza
    repetir NUEVA ITERACIÓN (con las recomendaciones reales del Auditor
    como feedback) hasta llegar a target_score o agotar max_attempts,
    pero siempre se detiene en WAITING_HUMAN — aprobar/ejecutar sigue
    siendo decisión humana explícita."""

    target_score: int = Field(default=90, ge=0, le=100)
    max_attempts: int = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------


class AuditOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parse_ok: bool
    audited_prompt: str | None
    total_score: int | None
    gates_passed: int
    gates_failed: int
    gates_not_applicable: int
    gates_score: float | None
    properties: list[dict[str, Any]] | None
    gates: list[dict[str, Any]] | None
    recommendations: list[str] | None
    raw_response: dict[str, Any]
    created_at: datetime


class HumanDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    decision: str
    feedback: str | None
    edited_prompt: str | None
    created_at: datetime


class IterationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    iteration_number: int
    input_prompt: str
    output_prompt: str | None
    source: str
    optimizer_raw: dict[str, Any] | None
    created_at: datetime
    audits: list[AuditOut] = []
    human_decisions: list[HumanDecisionOut] = []


class ResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    approved_prompt: str
    final_response: str
    model: str
    created_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: str
    created_at: datetime
    finished_at: datetime | None
    original_prompt: str
    optimizer_model: str
    auditor_model: str
    executor_model: str
    error_message: str | None


class RunDetailOut(RunOut):
    """GET /api/runs/{id}: todo lo necesario para reconstruir el proceso
    completo en el frontend sin llamadas adicionales."""

    iterations: list[IterationOut] = []
    result: ResultOut | None = None


class TimelineEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    description: str
