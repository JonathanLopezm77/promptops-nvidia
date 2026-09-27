"""Flujo de la capa de Ingeniería de Requisitos (Parcial 1, sección 4.1):

    requisito original -> Evaluador -> diagnóstico + métricas + preguntas
    -> Mejorador -> requisito mejorado -> Evaluador (reevaluación) -> delta

Es el ÚNICO módulo que asigna `RequirementAnalysis.status`, igual que
workflow.py con `run.status`. Estados:

    CREATED -> EVALUATING -> IMPROVING -> REEVALUATING -> COMPLETED
    EVALUATING -> COMPLETED      (el original ya es de alta calidad: no se toca)
    cualquier estado activo -> ERROR

No hay estado de espera humana: este flujo no ejecuta nada, solo
diagnostica y propone. El humano interviene respondiendo las preguntas de
aclaración, lo que crea un análisis NUEVO ligado al anterior (`parent_id`),
que queda intacto como evidencia.
"""

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import SessionLocal
from backend.models import RequirementAnalysis, RequirementEvaluation
from backend.services.nvidia_client import NvidiaClientError
from backend.services.requirements_evaluator import (
    EvaluatorParseError,
    EvaluatorResult,
    evaluate_requirement,
)
from backend.services.requirements_improver import ImproverParseError, improve_requirement
from backend.services.workflow import InvalidTransitionError

logger = logging.getLogger("promptops.requirements")

_ESTADOS_ACTIVOS = ("CREATED", "EVALUATING", "IMPROVING", "REEVALUATING")
_ESTADOS_TERMINALES = ("COMPLETED", "ERROR")

_TRANSICIONES_BASE: dict[str, set[str]] = {
    "CREATED": {"EVALUATING"},
    "EVALUATING": {"IMPROVING", "COMPLETED"},
    "IMPROVING": {"REEVALUATING"},
    "REEVALUATING": {"COMPLETED"},
    "COMPLETED": set(),
    "ERROR": set(),
}

TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    estado: (destinos | {"ERROR"} if estado in _ESTADOS_ACTIVOS else set(destinos))
    for estado, destinos in _TRANSICIONES_BASE.items()
}


def _set_status(db: Session, analysis: RequirementAnalysis, target_status: str) -> None:
    """Único lugar que escribe `analysis.status`."""
    if target_status not in TRANSICIONES_VALIDAS.get(analysis.status, set()):
        raise InvalidTransitionError(analysis.status, target_status)
    analysis.status = target_status
    if target_status in _ESTADOS_TERMINALES:
        analysis.finished_at = datetime.now(timezone.utc)
    db.add(analysis)
    db.commit()
    db.refresh(analysis)


def fail_analysis(db: Session, analysis: RequirementAnalysis, error_message: str) -> None:
    analysis.error_message = error_message
    _set_status(db, analysis, "ERROR")


# ---------------------------------------------------------------------------
# Persistencia de evaluaciones
# ---------------------------------------------------------------------------


def _guardar_evaluacion(
    db: Session, analysis: RequirementAnalysis, stage: str, texto: str, r: EvaluatorResult
) -> RequirementEvaluation:
    e = r.evaluation
    evaluacion = RequirementEvaluation(
        analysis_id=analysis.id,
        stage=stage,
        evaluated_text=texto,
        parse_ok=True,
        global_score=e.global_score(),
        is_high_quality=e.is_high_quality(),
        criteria=[c.model_dump() for c in e.criteria],
        ambiguous_terms=[t.model_dump() for t in e.ambiguous_terms],
        clarification_questions=e.clarification_questions,
        missing_information=e.missing_information,
        is_compound=e.is_compound,
        summary=e.summary,
        raw_response=r.raw_response,
        model=r.model,
        prompt_tokens=r.prompt_tokens,
        completion_tokens=r.completion_tokens,
        latency_ms=r.latency_ms,
    )
    db.add(evaluacion)
    db.commit()
    return evaluacion


def _guardar_evaluacion_fallida(
    db: Session, analysis: RequirementAnalysis, stage: str, texto: str, err: EvaluatorParseError
) -> None:
    db.add(
        RequirementEvaluation(
            analysis_id=analysis.id,
            stage=stage,
            evaluated_text=texto,
            parse_ok=False,
            raw_response=err.raw_response,
            model=err.model,
            latency_ms=err.latency_ms,
        )
    )
    db.commit()


async def _evaluar(
    db: Session, analysis: RequirementAnalysis, stage: str, texto: str
) -> EvaluatorResult | None:
    """Evalúa y persiste. Devuelve None si falló (el análisis ya queda en ERROR)."""
    try:
        resultado = await evaluate_requirement(
            texto,
            project_context=analysis.project_context,
            clarifications=analysis.clarifications,
        )
    except EvaluatorParseError as e:
        _guardar_evaluacion_fallida(db, analysis, stage, texto, e)
        fail_analysis(db, analysis, str(e))
        return None
    except NvidiaClientError as e:
        fail_analysis(db, analysis, f"Error del Evaluador al llamar a NVIDIA: {e}")
        return None
    _guardar_evaluacion(db, analysis, stage, texto, resultado)
    return resultado


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


def start_analysis(
    db: Session,
    requirement: str,
    *,
    project_context: str | None = None,
    clarifications: str | None = None,
    input_mode: str = "text",
    stt_metadata: dict | None = None,
    parent_id: uuid.UUID | None = None,
) -> RequirementAnalysis:
    """Crea el análisis en CREATED (solo el INSERT). El trabajo con las IAs
    lo hace `advance_analysis`, normalmente en segundo plano."""
    settings = get_settings()
    analysis = RequirementAnalysis(
        status="CREATED",
        parent_id=parent_id,
        input_mode=input_mode,
        stt_metadata=stt_metadata,
        original_requirement=requirement,
        project_context=project_context or None,
        clarifications=clarifications or None,
        evaluator_model=settings.auditor_model,
        improver_model=settings.optimizer_model,
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


async def advance_analysis(db: Session, analysis: RequirementAnalysis) -> None:
    """CREATED -> ... -> COMPLETED/ERROR."""
    _set_status(db, analysis, "EVALUATING")
    original = await _evaluar(db, analysis, "original", analysis.original_requirement)
    if original is None:
        return

    if original.evaluation.is_high_quality():
        analysis.improvement_skipped = True
        _set_status(db, analysis, "COMPLETED")
        return

    _set_status(db, analysis, "IMPROVING")
    try:
        mejora = await improve_requirement(
            analysis.original_requirement,
            original.evaluation,
            project_context=analysis.project_context,
            clarifications=analysis.clarifications,
        )
    except ImproverParseError as e:
        analysis.improvement_raw = e.raw_response
        analysis.improvement_latency_ms = e.latency_ms
        fail_analysis(db, analysis, str(e))
        return
    except NvidiaClientError as e:
        fail_analysis(db, analysis, f"Error del Mejorador al llamar a NVIDIA: {e}")
        return

    m = mejora.improvement
    analysis.improved_requirement = m.improved_requirement
    analysis.improvement = {
        "acceptance_criteria": m.acceptance_criteria,
        "changes": m.changes,
        "pending_items": m.pending_items,
        "intent_preservation": m.intent_preservation,
        "unsupported_values": mejora.unsupported_values,
        "unsupported_retry": mejora.unsupported_retry,
    }
    analysis.improvement_raw = mejora.raw_response
    analysis.improvement_tokens = mejora.total_tokens
    analysis.improvement_latency_ms = mejora.latency_ms
    _set_status(db, analysis, "REEVALUATING")

    if await _evaluar(db, analysis, "improved", m.text_for_evaluation()) is None:
        return
    _set_status(db, analysis, "COMPLETED")


async def run_analysis_background(analysis_id: uuid.UUID) -> None:
    """Para FastAPI BackgroundTasks: abre su PROPIA sesión de BD."""
    db = SessionLocal()
    try:
        analysis = db.get(RequirementAnalysis, analysis_id)
        if analysis is None:
            return
        try:
            await advance_analysis(db, analysis)
        except Exception as exc:  # última red de seguridad: nunca dejarlo colgado
            logger.exception("Error inesperado en el análisis de requisito %s", analysis_id)
            db.rollback()
            fail_analysis(db, analysis, f"Error inesperado: {exc}")
    finally:
        db.close()


def register_tts_playback(db: Session, analysis: RequirementAnalysis, event: dict) -> None:
    """Registra una lectura en voz alta del resultado. Solo sobre análisis
    terminados: antes no hay resultado que leer."""
    if analysis.status not in _ESTADOS_TERMINALES:
        raise InvalidTransitionError(analysis.status, "TTS")
    registro = {**event, "played_at": datetime.now(timezone.utc).isoformat()}
    # Lista nueva (no .append) para que SQLAlchemy detecte el cambio en JSONB.
    analysis.tts_log = [*(analysis.tts_log or []), registro]
    db.add(analysis)
    db.commit()
    db.refresh(analysis)


def start_clarification(
    db: Session, previous: RequirementAnalysis, answers: str
) -> RequirementAnalysis:
    """Crea un análisis nuevo con las respuestas del stakeholder como
    aclaraciones. Solo desde un análisis COMPLETED: uno en curso todavía
    no tiene preguntas definitivas y uno en ERROR no produjo diagnóstico."""
    if previous.status != "COMPLETED":
        raise InvalidTransitionError(previous.status, "CLARIFY")
    aclaraciones = "\n\n".join(p for p in (previous.clarifications, answers.strip()) if p)
    return start_analysis(
        db,
        previous.original_requirement,
        project_context=previous.project_context,
        clarifications=aclaraciones,
        input_mode=previous.input_mode,
        stt_metadata=previous.stt_metadata,
        parent_id=previous.id,
    )
