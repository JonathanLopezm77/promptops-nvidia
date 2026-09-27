"""Schemas Pydantic de request/response de la API REST (distintos de los
schemas de las tres IAs en backend/schemas/{optimizer,auditor,executor}.py,
que validan lo que devuelve el LLM). `from_attributes=True` permite
construirlos directamente desde los modelos SQLAlchemy.
"""

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class CreateRunRequest(BaseModel):
    prompt: str = Field(min_length=1)
    # Audita también el prompt original antes de optimizarlo (línea base),
    # para medir el delta de la optimización (Parcial 1, sección 6.1).
    baseline_audit: bool = False


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


# ---------------------------------------------------------------------------
# Ingeniería de Requisitos (Parcial 1, Componente 1)
# ---------------------------------------------------------------------------


class CreateRequirementRequest(BaseModel):
    requirement: str = Field(min_length=1)
    project_context: str | None = None
    input_mode: Literal["text", "voice"] = "text"
    # Solo para input_mode = "voice": motor de STT, proveedor, si es local o
    # remoto, idioma, tiempos, etc. El enunciado exige registrarlo.
    stt_metadata: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _voz_exige_metadata(self) -> "CreateRequirementRequest":
        if self.input_mode == "voice" and not self.stt_metadata:
            raise ValueError("una entrada por voz debe incluir stt_metadata (motor, proveedor, idioma...)")
        if self.input_mode == "text" and self.stt_metadata:
            raise ValueError("stt_metadata solo aplica a entradas por voz")
        return self


class ClarifyRequirementRequest(BaseModel):
    answers: str = Field(min_length=1)


class TtsPlaybackRequest(BaseModel):
    """Una lectura en voz alta del resultado (retroalimentación hablada)."""

    engine: str = Field(min_length=1)
    voice: str = Field(min_length=1)
    language: str = Field(min_length=1)
    processing: Literal["local", "remote", "desconocido"]
    script: str = Field(min_length=1)


class RequirementEvaluationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    stage: str
    evaluated_text: str
    parse_ok: bool
    global_score: int | None
    is_high_quality: bool | None
    criteria: list[dict[str, Any]] | None
    ambiguous_terms: list[dict[str, Any]] | None
    clarification_questions: list[str] | None
    missing_information: list[str] | None
    is_compound: bool | None
    summary: str | None
    raw_response: dict[str, Any]
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int | None
    created_at: datetime


class RequirementAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    parent_id: uuid.UUID | None
    status: str
    created_at: datetime
    finished_at: datetime | None
    input_mode: str
    original_requirement: str
    evaluator_model: str
    improver_model: str
    error_message: str | None


class RequirementAnalysisDetailOut(RequirementAnalysisOut):
    """GET /api/requirements/{id}: todo lo necesario para mostrar y auditar
    el análisis completo sin llamadas adicionales."""

    stt_metadata: dict[str, Any] | None
    project_context: str | None
    clarifications: str | None
    improvement_skipped: bool
    improved_requirement: str | None
    improvement: dict[str, Any] | None
    improvement_raw: dict[str, Any] | None
    improvement_tokens: int | None
    improvement_latency_ms: int | None
    tts_log: list[dict[str, Any]] = []
    evaluations: list[RequirementEvaluationOut] = []

    @computed_field
    @property
    def score_delta(self) -> int | None:
        """Puntaje del mejorado menos el del original (delta antes/después)."""
        por_etapa = {e.stage: e for e in self.evaluations if e.parse_ok}
        if "original" not in por_etapa or "improved" not in por_etapa:
            return None
        return por_etapa["improved"].global_score - por_etapa["original"].global_score

    @computed_field
    @property
    def recommended_version(self) -> Literal["original", "improved"] | None:
        """La mejora solo se recomienda si subió el puntaje: una versión
        "mejorada" que puntúa igual o peor no debe reemplazar al original."""
        if self.status != "COMPLETED":
            return None
        if self.score_delta is None or self.score_delta <= 0:
            return "original"
        return "improved"
