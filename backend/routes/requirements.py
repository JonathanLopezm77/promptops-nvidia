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
    TtsPlaybackRequest,
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


def _responder_y_liberar(
    db: Session, analysis: RequirementAnalysis, background_tasks: BackgroundTasks
) -> RequirementAnalysisDetailOut:
    """Arma la respuesta, devuelve la conexión al pool y agenda el análisis.

    FastAPI cierra las dependencias con yield (get_db) DESPUÉS de las
    BackgroundTasks, así que sin este `db.close()` la conexión de la petición
    quedaba retenida los minutos que tarda la IA. Con 9 análisis simultáneos
    se agotó el pool y el servidor se bloqueó (bug encontrado en el punto 3)."""
    respuesta = RequirementAnalysisDetailOut.model_validate(analysis)
    db.close()
    background_tasks.add_task(requirements_workflow.run_analysis_background, respuesta.id)
    return respuesta


@router.post("", response_model=RequirementAnalysisDetailOut, status_code=202)
def crear_analisis(
    body: CreateRequirementRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> RequirementAnalysisDetailOut:
    analysis = requirements_workflow.start_analysis(
        db,
        body.requirement,
        project_context=body.project_context,
        input_mode=body.input_mode,
        stt_metadata=body.stt_metadata,
    )
    return _responder_y_liberar(db, analysis, background_tasks)


@router.get("", response_model=list[RequirementAnalysisOut])
def listar_analisis(db: Session = Depends(get_db)) -> list[RequirementAnalysis]:
    return db.query(RequirementAnalysis).order_by(RequirementAnalysis.created_at.desc()).all()


@router.get("/{analysis_id}", response_model=RequirementAnalysisDetailOut)
def obtener_analisis(analysis_id: uuid.UUID, db: Session = Depends(get_db)) -> RequirementAnalysis:
    return _obtener_o_404(db, analysis_id)


@router.post("/{analysis_id}/tts", response_model=RequirementAnalysisDetailOut, status_code=201)
def registrar_lectura(
    analysis_id: uuid.UUID, body: TtsPlaybackRequest, db: Session = Depends(get_db)
) -> RequirementAnalysis:
    """Registra que el resultado se leyó en voz alta (motor, voz, local o
    remota, texto leído). La síntesis ocurre en el navegador; esto solo
    deja la evidencia en la base de datos."""
    analysis = _obtener_o_404(db, analysis_id)
    requirements_workflow.register_tts_playback(db, analysis, body.model_dump())
    return analysis


@router.post("/{analysis_id}/clarify", response_model=RequirementAnalysisDetailOut, status_code=202)
def aclarar_analisis(
    analysis_id: uuid.UUID,
    body: ClarifyRequirementRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> RequirementAnalysisDetailOut:
    """Responde las preguntas de aclaración: crea un análisis nuevo ligado
    al anterior (parent_id) y lo procesa en segundo plano."""
    anterior = _obtener_o_404(db, analysis_id)
    nuevo = requirements_workflow.start_clarification(db, anterior, body.answers)
    return _responder_y_liberar(db, nuevo, background_tasks)
