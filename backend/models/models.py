"""Modelos SQLAlchemy de las cinco tablas del pipeline de PromptOps.

Estos modelos son solo la capa de mapeo ORM. El esquema real (tipos
ENUM, CHECK constraints, defaults) vive en `backend/schema.sql`, que es
la fuente de verdad y se aplica manualmente con `psql -f` (sin Alembic,
ver anti-objetivos en CLAUDE.md). Por eso los `Enum` de abajo usan
`create_type=False`: SQLAlchemy nunca debe intentar crear estos tipos,
solo reutilizar los que ya existen en la base de datos.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

RunStatus = Enum(
    "CREATED", "OPTIMIZING", "AUDITING", "GATING", "WAITING_HUMAN",
    "ITERATING", "APPROVED", "EXECUTING", "COMPLETED", "REJECTED", "ERROR",
    name="run_status", create_type=False,
)

IterationSource = Enum(
    "optimizer", "human_edit", name="iteration_source", create_type=False
)

HumanDecisionType = Enum(
    "approve", "iterate", "edit", "reject",
    name="human_decision_type", create_type=False,
)


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    status: Mapped[str] = mapped_column(RunStatus, server_default="CREATED")
    original_prompt: Mapped[str] = mapped_column(Text)
    optimizer_model: Mapped[str] = mapped_column(Text)
    auditor_model: Mapped[str] = mapped_column(Text)
    executor_model: Mapped[str] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text, default=None)

    iterations: Mapped[list["Iteration"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="Iteration.iteration_number"
    )
    result: Mapped["Result | None"] = relationship(
        back_populates="run", cascade="all, delete-orphan", uselist=False
    )


class Iteration(Base):
    __tablename__ = "iterations"
    __table_args__ = (UniqueConstraint("run_id", "iteration_number"),)

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"))
    iteration_number: Mapped[int] = mapped_column(Integer)
    input_prompt: Mapped[str] = mapped_column(Text)
    output_prompt: Mapped[str | None] = mapped_column(Text, default=None)
    source: Mapped[str] = mapped_column(IterationSource)
    optimizer_raw: Mapped[dict | None] = mapped_column(JSONB, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    run: Mapped["Run"] = relationship(back_populates="iterations")
    audits: Mapped[list["Audit"]] = relationship(
        back_populates="iteration", cascade="all, delete-orphan"
    )
    human_decisions: Mapped[list["HumanDecision"]] = relationship(
        back_populates="iteration", cascade="all, delete-orphan"
    )


class Audit(Base):
    __tablename__ = "audits"
    __table_args__ = (
        CheckConstraint(
            "parse_ok = FALSE OR (gates_passed + gates_failed + gates_not_applicable = 4)",
            name="audits_gate_count_check",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    iteration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("iterations.id", ondelete="CASCADE")
    )
    parse_ok: Mapped[bool]
    audited_prompt: Mapped[str | None] = mapped_column(Text, default=None)
    total_score: Mapped[int | None] = mapped_column(Integer, default=None)
    gates_passed: Mapped[int] = mapped_column(Integer, server_default="0")
    gates_failed: Mapped[int] = mapped_column(Integer, server_default="0")
    gates_not_applicable: Mapped[int] = mapped_column(Integer, server_default="0")
    gates_score: Mapped[float | None] = mapped_column(Numeric(5, 4), default=None)
    properties: Mapped[list | None] = mapped_column(JSONB, default=None)
    gates: Mapped[list | None] = mapped_column(JSONB, default=None)
    recommendations: Mapped[list | None] = mapped_column(JSONB, default=None)
    raw_response: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    iteration: Mapped["Iteration"] = relationship(back_populates="audits")


class HumanDecision(Base):
    __tablename__ = "human_decisions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    iteration_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("iterations.id", ondelete="CASCADE")
    )
    decision: Mapped[str] = mapped_column(HumanDecisionType)
    feedback: Mapped[str | None] = mapped_column(Text, default=None)
    edited_prompt: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    iteration: Mapped["Iteration"] = relationship(back_populates="human_decisions")


class Result(Base):
    __tablename__ = "results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("runs.id", ondelete="CASCADE"), unique=True
    )
    approved_prompt: Mapped[str] = mapped_column(Text)
    final_response: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(server_default=text("now()"))

    run: Mapped["Run"] = relationship(back_populates="result")
