"""Modelos SQLAlchemy de la capa de Ingeniería de Requisitos.

Mapean las dos tablas de `backend/schema_requirements.sql`, que es la
fuente de verdad de su esquema (CHECKs, índices, defaults).
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class RequirementAnalysis(Base):
    __tablename__ = "requirement_analyses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("requirement_analyses.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(Text, server_default="CREATED")
    input_mode: Mapped[str] = mapped_column(Text, server_default="text")
    stt_metadata: Mapped[dict | None] = mapped_column(JSONB, default=None)
    original_requirement: Mapped[str] = mapped_column(Text)
    project_context: Mapped[str | None] = mapped_column(Text, default=None)
    clarifications: Mapped[str | None] = mapped_column(Text, default=None)
    evaluator_model: Mapped[str] = mapped_column(Text)
    improver_model: Mapped[str] = mapped_column(Text)
    improvement_skipped: Mapped[bool] = mapped_column(server_default="false")
    improved_requirement: Mapped[str | None] = mapped_column(Text, default=None)
    improvement: Mapped[dict | None] = mapped_column(JSONB, default=None)
    improvement_raw: Mapped[dict | None] = mapped_column(JSONB, default=None)
    improvement_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    improvement_latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)
    tts_log: Mapped[list] = mapped_column(JSONB, server_default=text("'[]'::jsonb"))

    evaluations: Mapped[list["RequirementEvaluation"]] = relationship(
        back_populates="analysis",
        cascade="all, delete-orphan",
        order_by="RequirementEvaluation.created_at",
    )


class RequirementEvaluation(Base):
    __tablename__ = "requirement_evaluations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    analysis_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("requirement_analyses.id", ondelete="CASCADE")
    )
    stage: Mapped[str] = mapped_column(Text)
    evaluated_text: Mapped[str] = mapped_column(Text)
    parse_ok: Mapped[bool]
    global_score: Mapped[int | None] = mapped_column(Integer, default=None)
    is_high_quality: Mapped[bool | None] = mapped_column(default=None)
    criteria: Mapped[list | None] = mapped_column(JSONB, default=None)
    ambiguous_terms: Mapped[list | None] = mapped_column(JSONB, default=None)
    clarification_questions: Mapped[list | None] = mapped_column(JSONB, default=None)
    missing_information: Mapped[list | None] = mapped_column(JSONB, default=None)
    is_compound: Mapped[bool | None] = mapped_column(default=None)
    summary: Mapped[str | None] = mapped_column(Text, default=None)
    raw_response: Mapped[dict] = mapped_column(JSONB)
    model: Mapped[str] = mapped_column(Text)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, default=None)
    latency_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    analysis: Mapped["RequirementAnalysis"] = relationship(back_populates="evaluations")
