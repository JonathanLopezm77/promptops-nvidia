"""Endpoints de la capa de Ingeniería de Requisitos (Parcial 1, Componente 1).

Misma forma que routes/runs.py: la parte rápida (crear la fila) es
síncrona y responde 202; las llamadas a las IAs corren en segundo plano y
el cliente hace polling a GET /api/requirements/{id}.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import RequirementAnalysis
from backend.schemas.api import (
    ClarifyRequirementRequest,
    CreateRequirementRequest,
    RequirementAnalysisDetailOut,
    RequirementAnalysisOut,
)
from backend.services import requirements_workflow

router = APIRouter(prefix="/requirements", tags=["requirements"])


def _obtener_o_404(db: Session, analysis_id: uuid.UUID) -> RequirementAnalysis:
    analysis = db.get(RequirementAnalysis, analysis_id)
    if analysis is None:
        raise HTTPException(
            status_code=404, detail=f"No existe un análisis de requisito con id {analysis_id}."
        )
    return analysis


@router.post("", response_model=RequirementAnalysisDetailOut, status_code=202)
def crear_analisis(
    body: CreateRequirementRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> RequirementAnalysis:
    analysis = requirements_workflow.start_analysis(
        db,
        body.requirement,
        project_context=body.project_context,
        input_mode=body.input_mode,
        stt_metadata=body.stt_metadata,
    )
    background_tasks.add_task(requirements_workflow.run_analysis_background, analysis.id)
    return analysis


@router.get("", response_model=list[RequirementAnalysisOut])
def listar_analisis(db: Session = Depends(get_db)) -> list[RequirementAnalysis]:
    return db.query(RequirementAnalysis).order_by(RequirementAnalysis.created_at.desc()).all()


@router.get("/{analysis_id}", response_model=RequirementAnalysisDetailOut)
def obtener_analisis(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> RequirementAnalysis:
    return _obtener_o_404(db, analysis_id)


@router.post("/{analysis_id}/clarify", response_model=RequirementAnalysisDetailOut, status_code=202)
def aclarar_analisis(
    analysis_id: uuid.UUID,
    body: ClarifyRequirementRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RequirementAnalysis:
    """Responde las preguntas de aclaración: crea un análisis nuevo ligado
    al anterior (parent_id) y lo procesa en segundo plano."""
    anterior = _obtener_o_404(db, analysis_id)
    nuevo = requirements_workflow.start_clarification(db, anterior, body.answers)
    background_tasks.add_task(requirements_workflow.run_analysis_background, nuevo.id)
    return nuevo
