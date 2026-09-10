"""Endpoints REST del pipeline de PromptOps (CLAUDE.md, sección API).

Cada endpoint es una capa fina: obtiene el `Run` (o 404), delega en
`backend.services.workflow` (el único módulo que cambia `run.status`) y
serializa la respuesta. Ningún endpoint asigna `run.status` directamente.
"""

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Run
from backend.schemas.api import (
    AutoIterateRequest,
    CreateRunRequest,
    EditRequest,
    IterateRequest,
    RejectRequest,
    RunDetailOut,
    RunOut,
    TimelineEventOut,
)
from backend.services import workflow

router = APIRouter(prefix="/runs", tags=["runs"])


def _obtener_run_o_404(db: Session, run_id: uuid.UUID) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"No existe un run con id {run_id}.")
    return run


@router.post("", response_model=RunDetailOut, status_code=202)
def crear_run(body: CreateRunRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Run:
    """Crea el run (rápido) y agenda el ciclo Optimizer+Auditor en segundo
    plano (~170s reales con NVIDIA: bloquear el request ese tiempo no es
    viable). El cliente debe hacer polling a GET /api/runs/{id} (y
    /events) hasta que status llegue a WAITING_HUMAN o ERROR."""
    run = workflow.start_run(db, body.prompt)
    background_tasks.add_task(workflow.run_new_run_pipeline_background, run.id)
    return run


@router.get("", response_model=list[RunOut])
def listar_runs(db: Session = Depends(get_db)) -> list[Run]:
    """Listado para el historial, más reciente primero."""
    return db.query(Run).order_by(Run.created_at.desc()).all()


@router.get("/{run_id}", response_model=RunDetailOut)
def obtener_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> Run:
    return _obtener_run_o_404(db, run_id)


@router.get("/{run_id}/events", response_model=list[TimelineEventOut])
def eventos_run(run_id: uuid.UUID, db: Session = Depends(get_db)):
    run = _obtener_run_o_404(db, run_id)
    return workflow.build_timeline(run)


@router.post("/{run_id}/iterate", response_model=RunDetailOut, status_code=202)
def iterar_run(
    run_id: uuid.UUID, body: IterateRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> Run:
    """Registra la decisión y transiciona a OPTIMIZING (rápido); el ciclo
    Optimizer+Auditor real corre en segundo plano, igual que en /runs."""
    run = _obtener_run_o_404(db, run_id)
    ultima_iteracion = workflow.start_iteration(db, run, body.feedback)
    background_tasks.add_task(
        workflow.run_iteration_pipeline_background, run.id, ultima_iteracion.id, body.feedback
    )
    return run


@router.post("/{run_id}/auto-iterate", response_model=RunDetailOut, status_code=202)
def auto_iterar_run(
    run_id: uuid.UUID,
    body: AutoIterateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Run:
    """Repite NUEVA ITERACIÓN automáticamente (feedback = recomendaciones
    reales del Auditor) hasta llegar a target_score o agotar
    max_attempts. Siempre se detiene en WAITING_HUMAN: no es parte de la
    lista literal de endpoints de CLAUDE.md, y aprobar/ejecutar sigue
    siendo una decisión humana explícita, nunca automática."""
    run = _obtener_run_o_404(db, run_id)
    workflow.ensure_can_start_iteration(run)
    background_tasks.add_task(
        workflow.run_auto_iterate_pipeline_background, run.id, body.target_score, body.max_attempts
    )
    return run


@router.post("/{run_id}/edit", response_model=RunDetailOut, status_code=202)
def editar_run(
    run_id: uuid.UUID, body: EditRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> Run:
    """Registra la edición y transiciona a AUDITING (rápido); la
    reauditoría real corre en segundo plano."""
    run = _obtener_run_o_404(db, run_id)
    nueva_iteracion = workflow.start_edit(db, run, body.prompt)
    background_tasks.add_task(workflow.run_edit_pipeline_background, run.id, nueva_iteracion.id)
    return run


@router.post("/{run_id}/approve", response_model=RunDetailOut)
def aprobar_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> Run:
    run = _obtener_run_o_404(db, run_id)
    return workflow.approve_run(db, run)


@router.post("/{run_id}/reject", response_model=RunDetailOut)
def rechazar_run(run_id: uuid.UUID, body: RejectRequest, db: Session = Depends(get_db)) -> Run:
    """No está en la lista literal de endpoints de CLAUDE.md, pero
    WAITING_HUMAN -> REJECTED existe en la máquina de estados y en
    human_decisions.decision desde el bloque 6: sin este endpoint ese
    estado sería inalcanzable vía API."""
    run = _obtener_run_o_404(db, run_id)
    return workflow.reject_run(db, run, body.feedback)


@router.post("/{run_id}/execute", response_model=RunDetailOut, status_code=202)
def ejecutar_run(run_id: uuid.UUID, background_tasks: BackgroundTasks, db: Session = Depends(get_db)) -> Run:
    """APPROVED -> EXECUTING (rápido); el Executor real corre en segundo
    plano y persiste el Result al completar (EXECUTING -> COMPLETED)."""
    run = _obtener_run_o_404(db, run_id)
    run = workflow.start_execution(db, run)
    background_tasks.add_task(workflow.run_execution_pipeline_background, run.id)
    return run
