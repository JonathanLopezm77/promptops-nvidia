"""Máquina de estados del pipeline de PromptOps (CLAUDE.md, sección
"Máquina de estados"). Este es el ÚNICO módulo que debe asignar
`run.status`: cualquier otro código que necesite cambiar el estado de un
run debe pasar por las funciones públicas de aquí, nunca por
`run.status = ...` directamente.

También orquesta el ciclo Optimizer -> Auditor y persiste cada etapa
(iteración, auditoría con sus contadores, decisión humana), y ofrece
`build_timeline()` para reconstruir el timeline de observabilidad a
partir de esos datos (no existe una sexta tabla de eventos: CLAUDE.md fija
"Cinco tablas", así que el timeline se deriva de runs/iterations/audits/
human_decisions/results, no se persiste aparte).

La ejecución final (Executor, IA 3) todavía no existe como servicio
(bloque posterior a Endpoints en el checklist de CLAUDE.md). Por eso
`start_execution`/`complete_execution` solo validan y persisten la
transición APPROVED -> EXECUTING -> COMPLETED; la llamada real al
Executor se conectará cuando ese servicio exista.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.database import SessionLocal
from backend.models import Audit, HumanDecision, Iteration, Result, Run
from backend.services.final_executor import ExecutorParseError, execute_prompt
from backend.services.nvidia_client import NvidiaClientError
from backend.services.prompt_auditor import AuditorParseError, audit_prompt
from backend.services.prompt_optimizer import OptimizerParseError, optimize_prompt

logger = logging.getLogger("promptops.workflow")

# ---------------------------------------------------------------------------
# Máquina de estados: única fuente de verdad de qué transiciones existen.
# ---------------------------------------------------------------------------

_ESTADOS_ACTIVOS = (
    "CREATED",
    "OPTIMIZING",
    "AUDITING",
    "GATING",
    "WAITING_HUMAN",
    "ITERATING",
    "APPROVED",
    "EXECUTING",
)
_ESTADOS_TERMINALES = ("COMPLETED", "REJECTED", "ERROR")

_TRANSICIONES_BASE: dict[str, set[str]] = {
    "CREATED": {"OPTIMIZING"},
    "OPTIMIZING": {"AUDITING"},
    "AUDITING": {"GATING"},
    "GATING": {"WAITING_HUMAN"},
    "WAITING_HUMAN": {"ITERATING", "AUDITING", "APPROVED", "REJECTED"},
    "ITERATING": {"OPTIMIZING"},
    "APPROVED": {"EXECUTING"},
    "EXECUTING": {"COMPLETED"},
    "COMPLETED": set(),
    "REJECTED": set(),
    "ERROR": set(),
}

# "cualquiera -> ERROR" (CLAUDE.md) = cualquier estado activo, no los
# terminales: un run COMPLETED/REJECTED/ERROR no vuelve a moverse.
TRANSICIONES_VALIDAS: dict[str, set[str]] = {
    estado: (destinos | {"ERROR"} if estado in _ESTADOS_ACTIVOS else set(destinos))
    for estado, destinos in _TRANSICIONES_BASE.items()
}


class InvalidTransitionError(Exception):
    """Transición de estado no permitida. Las rutas deben traducir esto a HTTP 409."""

    def __init__(self, current_status: str, target_status: str):
        self.current_status = current_status
        self.target_status = target_status
        super().__init__(f"Transición inválida: {current_status} -> {target_status}")


def _ensure_transition_allowed(current_status: str, target_status: str) -> None:
    """Único chequeo de validez de transiciones de todo el sistema."""
    permitidos = TRANSICIONES_VALIDAS.get(current_status, set())
    if target_status not in permitidos:
        raise InvalidTransitionError(current_status, target_status)


def _set_status(db: Session, run: Run, target_status: str) -> None:
    """Único lugar que escribe `run.status`."""
    _ensure_transition_allowed(run.status, target_status)
    run.status = target_status
    if target_status in _ESTADOS_TERMINALES:
        run.finished_at = datetime.now(timezone.utc)
    db.add(run)
    db.commit()
    db.refresh(run)


def fail_run(db: Session, run: Run, error_message: str) -> Run:
    """Transiciona a ERROR desde cualquier estado activo, dejando error_message."""
    run.error_message = error_message
    _set_status(db, run, "ERROR")
    return run


# ---------------------------------------------------------------------------
# Helpers de lectura
# ---------------------------------------------------------------------------


def _ultima_iteracion(db: Session, run: Run) -> Iteration:
    iteracion = (
        db.query(Iteration)
        .filter(Iteration.run_id == run.id)
        .order_by(Iteration.iteration_number.desc())
        .first()
    )
    if iteracion is None:
        raise RuntimeError(f"run {run.id} no tiene iteraciones: estado inconsistente")
    return iteracion


def _ultima_auditoria(db: Session, iteracion: Iteration) -> Audit | None:
    return (
        db.query(Audit)
        .filter(Audit.iteration_id == iteracion.id)
        .order_by(Audit.created_at.desc())
        .first()
    )


def _resumir_auditoria_para_feedback(audit: Audit | None) -> str | None:
    """Texto que se pasa al Optimizer como `audit_feedback` en la siguiente
    iteración. Una auditoría con parse_ok=false no aporta feedback útil."""
    if audit is None or not audit.parse_ok:
        return None
    partes = [
        f"{gate['gate']} FALLÓ: {gate['justification']}"
        for gate in (audit.gates or [])
        if gate.get("status") == "FAIL"
    ]
    if audit.recommendations:
        partes.append("Recomendaciones: " + "; ".join(audit.recommendations))
    return "\n".join(partes) if partes else None


# ---------------------------------------------------------------------------
# Ciclo Optimizer -> Auditor (compartido por create_run, iterate_run, edit_run)
# ---------------------------------------------------------------------------


async def _ciclo_optimizar_y_auditar(
    db: Session,
    run: Run,
    *,
    iteration_number: int,
    db_input_prompt: str,
    previous_prompt: str | None,
    audit_feedback: str | None,
    human_feedback: str | None,
) -> None:
    try:
        resultado_opt = await optimize_prompt(
            run.original_prompt,
            previous_prompt=previous_prompt,
            audit_feedback=audit_feedback,
            human_feedback=human_feedback,
        )
    except OptimizerParseError as e:
        iteracion = Iteration(
            run_id=run.id,
            iteration_number=iteration_number,
            input_prompt=db_input_prompt,
            output_prompt=None,
            source="optimizer",
            optimizer_raw=e.raw_response,
        )
        db.add(iteracion)
        db.commit()
        fail_run(db, run, f"El Optimizer no devolvió JSON válido tras reintentar: {e}")
        return
    except NvidiaClientError as e:
        fail_run(db, run, f"Error del Optimizer al llamar a NVIDIA: {e}")
        return

    iteracion = Iteration(
        run_id=run.id,
        iteration_number=iteration_number,
        input_prompt=db_input_prompt,
        output_prompt=resultado_opt.optimizer_response.improved_prompt,
        source="optimizer",
        optimizer_raw=resultado_opt.raw_response,
    )
    db.add(iteracion)
    db.commit()
    db.refresh(iteracion)

    _set_status(db, run, "AUDITING")
    await _auditar_iteracion(db, run, iteracion)


async def _auditar_iteracion(db: Session, run: Run, iteracion: Iteration) -> None:
    try:
        resultado_aud = await audit_prompt(iteracion.output_prompt)
    except AuditorParseError as e:
        audit = Audit(iteration_id=iteracion.id, parse_ok=False, raw_response=e.raw_response)
        db.add(audit)
        db.commit()
        fail_run(db, run, f"El Auditor no devolvió JSON válido tras reintentar: {e}")
        return
    except NvidiaClientError as e:
        fail_run(db, run, f"Error del Auditor al llamar a NVIDIA: {e}")
        return

    a = resultado_aud.audit_response
    audit = Audit(
        iteration_id=iteracion.id,
        parse_ok=True,
        audited_prompt=iteracion.output_prompt,
        total_score=a.total_score,
        gates_passed=resultado_aud.gates_passed,
        gates_failed=resultado_aud.gates_failed,
        gates_not_applicable=resultado_aud.gates_not_applicable,
        gates_score=resultado_aud.gates_score,
        properties=[{"gate": g.gate, **p.model_dump()} for g in a.gates for p in g.properties],
        gates=[g.model_dump() for g in a.gates],
        recommendations=a.recommendations,
        raw_response=resultado_aud.raw_response,
    )
    db.add(audit)
    db.commit()

    _set_status(db, run, "GATING")
    _set_status(db, run, "WAITING_HUMAN")


# ---------------------------------------------------------------------------
# API pública del workflow
# ---------------------------------------------------------------------------


def start_run(db: Session, original_prompt: str) -> Run:
    """Crea el run en CREATED (solo el INSERT: rápido). NO corre el ciclo
    Optimizer/Auditor todavía — eso es `advance_new_run`. Existe separado
    de `create_run` para que POST /api/runs pueda responder de inmediato
    (el ciclo real tarda ~170s con las IAs de NVIDIA) y correr el resto en
    segundo plano; ver `run_new_run_pipeline_background`."""
    settings = get_settings()
    run = Run(
        status="CREATED",
        original_prompt=original_prompt,
        optimizer_model=settings.optimizer_model,
        auditor_model=settings.auditor_model,
        executor_model=settings.executor_model,
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


async def advance_new_run(db: Session, run: Run) -> None:
    """CREATED -> OPTIMIZING -> ... -> WAITING_HUMAN/ERROR."""
    _set_status(db, run, "OPTIMIZING")
    await _ciclo_optimizar_y_auditar(
        db,
        run,
        iteration_number=1,
        db_input_prompt=run.original_prompt,
        previous_prompt=None,
        audit_feedback=None,
        human_feedback=None,
    )


async def create_run(db: Session, original_prompt: str) -> Run:
    """Versión síncrona (usada por los tests y por quien prefiera esperar
    el ciclo completo en el mismo request): crea el run y corre la
    primera iteración completa hasta WAITING_HUMAN o ERROR."""
    run = start_run(db, original_prompt)
    await advance_new_run(db, run)
    return run


async def run_new_run_pipeline_background(run_id: uuid.UUID) -> None:
    """Pensada para FastAPI BackgroundTasks: abre su PROPIA sesión de BD
    (la del request ya habrá terminado cuando esto corra) y avanza el run
    recién creado hasta WAITING_HUMAN/ERROR."""
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return
        try:
            await advance_new_run(db, run)
        except Exception as exc:  # última red de seguridad: nunca dejar el run colgado
            logger.exception("Error inesperado avanzando el run %s en segundo plano", run_id)
            fail_run(db, run, f"Error inesperado: {exc}")
    finally:
        db.close()


def start_iteration(db: Session, run: Run, human_feedback: str) -> Iteration:
    """WAITING_HUMAN -> ITERATING -> OPTIMIZING (rápido: solo la
    HumanDecision + las dos transiciones). Devuelve la iteración anterior,
    que `advance_iteration` necesita como base."""
    _ensure_transition_allowed(run.status, "ITERATING")
    ultima_iteracion = _ultima_iteracion(db, run)

    db.add(HumanDecision(iteration_id=ultima_iteracion.id, decision="iterate", feedback=human_feedback))
    db.commit()

    _set_status(db, run, "ITERATING")
    _set_status(db, run, "OPTIMIZING")
    return ultima_iteracion


async def advance_iteration(db: Session, run: Run, ultima_iteracion: Iteration, human_feedback: str) -> None:
    ultima_auditoria = _ultima_auditoria(db, ultima_iteracion)
    await _ciclo_optimizar_y_auditar(
        db,
        run,
        iteration_number=ultima_iteracion.iteration_number + 1,
        db_input_prompt=ultima_iteracion.output_prompt,
        previous_prompt=ultima_iteracion.output_prompt,
        audit_feedback=_resumir_auditoria_para_feedback(ultima_auditoria),
        human_feedback=human_feedback,
    )


async def iterate_run(db: Session, run: Run, human_feedback: str) -> Run:
    """Versión síncrona: WAITING_HUMAN -> ITERATING -> OPTIMIZING -> ...
    con el feedback humano y de auditoría como contexto."""
    ultima_iteracion = start_iteration(db, run, human_feedback)
    await advance_iteration(db, run, ultima_iteracion, human_feedback)
    return run


async def run_iteration_pipeline_background(run_id: uuid.UUID, ultima_iteracion_id: uuid.UUID, human_feedback: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        ultima_iteracion = db.get(Iteration, ultima_iteracion_id)
        if run is None or ultima_iteracion is None:
            return
        try:
            await advance_iteration(db, run, ultima_iteracion, human_feedback)
        except Exception as exc:
            logger.exception("Error inesperado avanzando la iteración del run %s en segundo plano", run_id)
            fail_run(db, run, f"Error inesperado: {exc}")
    finally:
        db.close()


DEFAULT_AUTO_ITERATE_TARGET_SCORE = 90
DEFAULT_AUTO_ITERATE_MAX_ATTEMPTS = 5


def ensure_can_start_iteration(run: Run) -> None:
    """Chequeo de solo lectura (sin tocar la BD): permite validar antes de
    agendar una tarea de fondo, para devolver 409 de inmediato si el run
    no está en WAITING_HUMAN, sin ejecutar nada."""
    _ensure_transition_allowed(run.status, "ITERATING")


async def advance_auto_iterate(db: Session, run: Run, target_score: int, max_attempts: int) -> None:
    """Repite el ciclo de NUEVA ITERACIÓN automáticamente —usando las
    recomendaciones REALES de cada auditoría como feedback, sin inventar
    ni ajustar ningún score— hasta que el Auditor real reporte
    total_score >= target_score, o se agoten max_attempts. Siempre
    termina en WAITING_HUMAN (o ERROR si algo falla de verdad): jamás
    aprueba ni ejecuta por sí mismo, eso sigue siendo decisión humana.

    Cada vuelta automática se registra en human_decisions como una
    decisión 'iterate' normal, pero con el feedback prefijado
    "[AUTO-ITERACIÓN N/M]" para que quede honestamente trazado que no fue
    un click humano (CLAUDE.md exige trazabilidad completa; no se
    disfraza como si un humano hubiera escrito ese feedback)."""
    intentos = 0
    while intentos < max_attempts:
        if run.status != "WAITING_HUMAN":
            return  # algo externo lo movió (p. ej. ERROR); no seguir

        ultima_iteracion = _ultima_iteracion(db, run)
        ultima_auditoria = _ultima_auditoria(db, ultima_iteracion)
        if (
            ultima_auditoria is not None
            and ultima_auditoria.parse_ok
            and (ultima_auditoria.total_score or 0) >= target_score
        ):
            return  # meta ya alcanzada, real, del propio Auditor

        base_feedback = _resumir_auditoria_para_feedback(ultima_auditoria) or (
            "Mejora el prompt para maximizar el cumplimiento de los Quality Gates."
        )
        feedback_auto = f"[AUTO-ITERACIÓN {intentos + 1}/{max_attempts}] {base_feedback}"

        iteracion_base = start_iteration(db, run, feedback_auto)
        await advance_iteration(db, run, iteracion_base, feedback_auto)
        intentos += 1
    # Se agotaron los intentos sin llegar a target_score: el run queda en
    # WAITING_HUMAN (o ERROR) con el mejor resultado real obtenido — nunca
    # se sube el score artificialmente para "cumplir" la meta.


async def run_auto_iterate_pipeline_background(
    run_id: uuid.UUID,
    target_score: int = DEFAULT_AUTO_ITERATE_TARGET_SCORE,
    max_attempts: int = DEFAULT_AUTO_ITERATE_MAX_ATTEMPTS,
) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return
        try:
            await advance_auto_iterate(db, run, target_score, max_attempts)
        except Exception as exc:
            logger.exception("Error inesperado en auto-iteración del run %s en segundo plano", run_id)
            fail_run(db, run, f"Error inesperado: {exc}")
    finally:
        db.close()


def start_edit(db: Session, run: Run, edited_prompt: str) -> Iteration:
    """WAITING_HUMAN -> AUDITING (rápido): registra la decisión humana y
    crea la nueva iteración editada. Devuelve la nueva iteración, que
    `advance_edit` reauditará."""
    _ensure_transition_allowed(run.status, "AUDITING")
    ultima_iteracion = _ultima_iteracion(db, run)

    db.add(HumanDecision(iteration_id=ultima_iteracion.id, decision="edit", edited_prompt=edited_prompt))
    db.commit()

    nueva_iteracion = Iteration(
        run_id=run.id,
        iteration_number=ultima_iteracion.iteration_number + 1,
        input_prompt=ultima_iteracion.output_prompt or ultima_iteracion.input_prompt,
        output_prompt=edited_prompt,
        source="human_edit",
    )
    db.add(nueva_iteracion)
    db.commit()
    db.refresh(nueva_iteracion)

    _set_status(db, run, "AUDITING")
    return nueva_iteracion


async def advance_edit(db: Session, run: Run, nueva_iteracion: Iteration) -> None:
    await _auditar_iteracion(db, run, nueva_iteracion)


async def edit_run(db: Session, run: Run, edited_prompt: str) -> Run:
    """Versión síncrona: WAITING_HUMAN -> AUDITING, reaudita directamente
    (sin pasar por el Optimizer)."""
    nueva_iteracion = start_edit(db, run, edited_prompt)
    await advance_edit(db, run, nueva_iteracion)
    return run


async def run_edit_pipeline_background(run_id: uuid.UUID, iteracion_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        iteracion = db.get(Iteration, iteracion_id)
        if run is None or iteracion is None:
            return
        try:
            await advance_edit(db, run, iteracion)
        except Exception as exc:
            logger.exception("Error inesperado auditando la edición del run %s en segundo plano", run_id)
            fail_run(db, run, f"Error inesperado: {exc}")
    finally:
        db.close()


def approve_run(db: Session, run: Run) -> Run:
    """WAITING_HUMAN -> APPROVED."""
    _ensure_transition_allowed(run.status, "APPROVED")
    ultima_iteracion = _ultima_iteracion(db, run)
    db.add(HumanDecision(iteration_id=ultima_iteracion.id, decision="approve"))
    db.commit()
    _set_status(db, run, "APPROVED")
    return run


def reject_run(db: Session, run: Run, feedback: str | None = None) -> Run:
    """WAITING_HUMAN -> REJECTED."""
    _ensure_transition_allowed(run.status, "REJECTED")
    ultima_iteracion = _ultima_iteracion(db, run)
    db.add(HumanDecision(iteration_id=ultima_iteracion.id, decision="reject", feedback=feedback))
    db.commit()
    _set_status(db, run, "REJECTED")
    return run


def start_execution(db: Session, run: Run) -> Run:
    """APPROVED -> EXECUTING (rápido). La llamada real al Executor corre
    en segundo plano; ver `advance_execution`/`run_execution_pipeline_background`."""
    _set_status(db, run, "EXECUTING")
    return run


def complete_execution(db: Session, run: Run, *, final_response: str, model: str) -> Run:
    """EXECUTING -> COMPLETED, persistiendo el Result con la respuesta ya
    obtenida del Executor."""
    _ensure_transition_allowed(run.status, "COMPLETED")
    ultima_iteracion = _ultima_iteracion(db, run)
    result = Result(
        run_id=run.id,
        approved_prompt=ultima_iteracion.output_prompt,
        final_response=final_response,
        model=model,
    )
    db.add(result)
    db.commit()
    _set_status(db, run, "COMPLETED")
    return run


async def advance_execution(db: Session, run: Run) -> None:
    """EXECUTING -> COMPLETED (o ERROR). Llama al Executor con
    EXCLUSIVAMENTE el prompt aprobado (la última iteración), sin
    contexto de auditoría ni de iteraciones anteriores."""
    ultima_iteracion = _ultima_iteracion(db, run)
    try:
        resultado = await execute_prompt(ultima_iteracion.output_prompt)
    except ExecutorParseError as e:
        fail_run(db, run, f"El Executor no devolvió JSON válido tras reintentar: {e}")
        return
    except NvidiaClientError as e:
        fail_run(db, run, f"Error del Executor al llamar a NVIDIA: {e}")
        return

    complete_execution(
        db,
        run,
        final_response=resultado.executor_response.response,
        model=resultado.model,
    )


async def run_execution_pipeline_background(run_id: uuid.UUID) -> None:
    """Pensada para FastAPI BackgroundTasks: abre su PROPIA sesión de BD
    y avanza un run ya EXECUTING hasta COMPLETED/ERROR."""
    db = SessionLocal()
    try:
        run = db.get(Run, run_id)
        if run is None:
            return
        try:
            await advance_execution(db, run)
        except Exception as exc:  # última red de seguridad: nunca dejar el run colgado
            logger.exception("Error inesperado ejecutando el run %s en segundo plano", run_id)
            fail_run(db, run, f"Error inesperado: {exc}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Timeline de observabilidad (derivado, no persistido: CLAUDE.md fija
# "Cinco tablas", no hay tabla de eventos).
# ---------------------------------------------------------------------------


@dataclass
class TimelineEvent:
    timestamp: datetime
    description: str


_ETIQUETAS_DECISION = {
    "approve": "Humano aprobó el prompt.",
    "iterate": "Humano solicitó una nueva iteración.",
    "edit": "Humano editó el prompt manualmente.",
    "reject": "Humano rechazó el prompt.",
}


def build_timeline(run: Run) -> list[TimelineEvent]:
    eventos: list[TimelineEvent] = [TimelineEvent(run.created_at, "Prompt recibido.")]

    for iteracion in run.iterations:
        if iteracion.source == "optimizer":
            if iteracion.output_prompt is not None:
                descripcion = f"Iteración {iteracion.iteration_number}: el Optimizer generó una versión mejorada."
            else:
                descripcion = f"Iteración {iteracion.iteration_number}: el Optimizer falló al generar JSON válido."
        else:
            descripcion = f"Iteración {iteracion.iteration_number}: edición manual del prompt."
        eventos.append(TimelineEvent(iteracion.created_at, descripcion))

        for audit in iteracion.audits:
            if audit.parse_ok:
                eventos.append(
                    TimelineEvent(
                        audit.created_at,
                        f"Auditoría completada: {audit.gates_passed}/"
                        f"{audit.gates_passed + audit.gates_failed} Gates aprobados "
                        f"(score {audit.total_score}/100).",
                    )
                )
            else:
                eventos.append(
                    TimelineEvent(audit.created_at, "Auditoría falló: el Auditor no devolvió JSON válido.")
                )

        for decision in iteracion.human_decisions:
            eventos.append(TimelineEvent(decision.created_at, _ETIQUETAS_DECISION[decision.decision]))

    if run.result is not None:
        eventos.append(TimelineEvent(run.result.created_at, "Ejecución completada, respuesta final generada."))

    if run.finished_at is not None and run.status == "ERROR":
        eventos.append(TimelineEvent(run.finished_at, f"Run marcado como ERROR: {run.error_message or 'sin detalle'}."))
    elif run.finished_at is not None and run.status == "REJECTED":
        eventos.append(TimelineEvent(run.finished_at, "Run rechazado por el humano."))

    eventos.sort(key=lambda e: e.timestamp)
    return eventos
