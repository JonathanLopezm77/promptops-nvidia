"""Tests de integración de workflow.py contra PostgreSQL real (CLAUDE.md
prohíbe SQLite incluso para pruebas), con optimize_prompt/audit_prompt
mockeados vía monkeypatch (sin llamadas a NVIDIA). Cada test crea su
propio run y lo borra al terminar (ON DELETE CASCADE se encarga del
resto), sin dejar residuos en la base de datos.
"""

import pytest

from backend.database import SessionLocal
from backend.models import Audit, HumanDecision, Iteration, Run
from backend.schemas.auditor import GATE_PROPERTIES, AuditorResponse
from backend.schemas.optimizer import OptimizerResponse
from backend.services.prompt_auditor import AuditorParseError, AuditorResult
from backend.services.prompt_optimizer import OptimizerParseError, OptimizerResult
from backend.services.workflow import (
    InvalidTransitionError,
    approve_run,
    complete_execution,
    create_run,
    edit_run,
    iterate_run,
    reject_run,
    start_execution,
)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _borrar(db, run: Run) -> None:
    db.delete(run)
    db.commit()


def _gate_completo(gate: str, status: str = "PASS") -> dict:
    return {
        "gate": gate,
        "status": status,
        "justification": "justificación de prueba",
        "properties": [
            {"property_id": pid, "property_name": nombre, "score": 7, "observation": "ok"}
            for pid, nombre in GATE_PROPERTIES[gate].items()
        ],
    }


def _auditor_response(gates_status: dict[str, str] | None = None) -> AuditorResponse:
    gates_status = gates_status or {}
    return AuditorResponse.model_validate(
        {
            "gates": [_gate_completo(g, gates_status.get(g, "PASS")) for g in GATE_PROPERTIES],
            "total_score": 85,
            "recommendations": ["ninguna"],
        }
    )


def _optimizer_result(improved_prompt: str = "prompt mejorado de prueba") -> OptimizerResult:
    return OptimizerResult(
        optimizer_response=OptimizerResponse(
            original_prompt="prompt original",
            analysis="análisis de prueba",
            improved_prompt=improved_prompt,
            changes=["cambio de prueba"],
            reasoning_summary="resumen de prueba",
        ),
        raw_response={"mock": "optimizer"},
        model="mock-optimizer",
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
    )


def _auditor_result(gates_status: dict[str, str] | None = None) -> AuditorResult:
    ar = _auditor_response(gates_status)
    passed, failed, na = ar.gate_counts()
    return AuditorResult(
        audit_response=ar,
        raw_response={"mock": "auditor"},
        model="mock-auditor",
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        gates_passed=passed,
        gates_failed=failed,
        gates_not_applicable=na,
        gates_score=ar.gates_score(),
    )


def _stub(resultado=None, exc: Exception | None = None):
    async def _fn(*args, **kwargs):
        if exc is not None:
            raise exc
        return resultado

    return _fn


def _crear_run_minimo(db, status: str) -> Run:
    """Crea un run + 1 iteración real y luego FUERZA el estado a `status`
    para preparar el escenario de un test de guard-clause. Esta asignación
    directa de `run.status` es SOLO para arreglar la precondición del
    test: el propio test verifica que el resto del sistema nunca hace
    esto (todas las transiciones reales pasan por workflow.py)."""
    run = Run(
        status="CREATED",
        original_prompt="prompt de prueba",
        optimizer_model="mock",
        auditor_model="mock",
        executor_model="mock",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    db.add(
        Iteration(
            run_id=run.id,
            iteration_number=1,
            input_prompt="prompt de prueba",
            output_prompt="prompt mejorado de prueba",
            source="optimizer",
            optimizer_raw={"mock": True},
        )
    )
    db.commit()

    run.status = status  # ver docstring: únicamente para arreglar el escenario de prueba
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


# ---------------------------------------------------------------------------
# Pipeline feliz
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_run_llega_a_waiting_human_y_persiste_iteracion_y_auditoria(db, monkeypatch):
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(_optimizer_result()))
    monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(_auditor_result()))

    run = await create_run(db, "resume este texto")
    try:
        assert run.status == "WAITING_HUMAN"

        iteraciones = db.query(Iteration).filter(Iteration.run_id == run.id).all()
        assert len(iteraciones) == 1
        assert iteraciones[0].output_prompt == "prompt mejorado de prueba"
        assert iteraciones[0].source == "optimizer"

        audits = db.query(Audit).filter(Audit.iteration_id == iteraciones[0].id).all()
        assert len(audits) == 1
        assert audits[0].parse_ok is True
        assert (audits[0].gates_passed, audits[0].gates_failed, audits[0].gates_not_applicable) == (4, 0, 0)
        assert float(audits[0].gates_score) == 1.0
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_ciclo_completo_approve_execute_complete(db, monkeypatch):
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(_optimizer_result()))
    monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(_auditor_result()))

    run = await create_run(db, "resume este texto")
    try:
        run = approve_run(db, run)
        assert run.status == "APPROVED"

        run = start_execution(db, run)
        assert run.status == "EXECUTING"

        run = complete_execution(db, run, final_response="respuesta final de prueba", model="mock-executor")
        assert run.status == "COMPLETED"
        assert run.finished_at is not None
        assert run.result is not None
        assert run.result.final_response == "respuesta final de prueba"
        assert run.result.approved_prompt == "prompt mejorado de prueba"
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_iterate_run_crea_segunda_iteracion_con_feedback(db, monkeypatch):
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(_optimizer_result("v1")))
    monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(_auditor_result({"gate_3_seguridad_veracidad": "FAIL"})))

    run = await create_run(db, "resume este texto")
    try:
        monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(_optimizer_result("v2")))
        monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(_auditor_result()))

        run = await iterate_run(db, run, "corrige la seguridad")
        assert run.status == "WAITING_HUMAN"

        iteraciones = db.query(Iteration).filter(Iteration.run_id == run.id).order_by(Iteration.iteration_number).all()
        assert [i.iteration_number for i in iteraciones] == [1, 2]
        assert iteraciones[1].output_prompt == "v2"

        decisiones = db.query(HumanDecision).filter(HumanDecision.iteration_id == iteraciones[0].id).all()
        assert len(decisiones) == 1
        assert decisiones[0].decision == "iterate"
        assert decisiones[0].feedback == "corrige la seguridad"
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_edit_run_reaudita_sin_llamar_al_optimizer(db, monkeypatch):
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(_optimizer_result()))
    monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(_auditor_result()))

    run = await create_run(db, "resume este texto")
    try:
        async def _no_deberia_llamarse(*args, **kwargs):
            raise AssertionError("edit_run no debe llamar al Optimizer")

        monkeypatch.setattr("backend.services.workflow.optimize_prompt", _no_deberia_llamarse)
        monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(_auditor_result()))

        run = await edit_run(db, run, "prompt editado a mano")
        assert run.status == "WAITING_HUMAN"

        iteraciones = db.query(Iteration).filter(Iteration.run_id == run.id).order_by(Iteration.iteration_number).all()
        assert len(iteraciones) == 2
        assert iteraciones[1].source == "human_edit"
        assert iteraciones[1].output_prompt == "prompt editado a mano"
        assert iteraciones[1].optimizer_raw is None

        decisiones = db.query(HumanDecision).filter(HumanDecision.iteration_id == iteraciones[0].id).all()
        assert decisiones[0].decision == "edit"
        assert decisiones[0].edited_prompt == "prompt editado a mano"
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_reject_run(db, monkeypatch):
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(_optimizer_result()))
    monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(_auditor_result()))

    run = await create_run(db, "resume este texto")
    try:
        run = reject_run(db, run, feedback="no sirve para nada")
        assert run.status == "REJECTED"
        assert run.finished_at is not None
    finally:
        _borrar(db, run)


# ---------------------------------------------------------------------------
# Fallos de parseo (Optimizer / Auditor) -> ERROR
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_optimizer_parse_error_deja_iteracion_fallida_y_run_en_error(db, monkeypatch):
    error = OptimizerParseError("JSON inválido tras reintentar", raw_response={"raw": "basura"})
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(exc=error))

    run = await create_run(db, "resume este texto")
    try:
        assert run.status == "ERROR"
        assert run.error_message is not None
        assert run.finished_at is not None

        iteraciones = db.query(Iteration).filter(Iteration.run_id == run.id).all()
        assert len(iteraciones) == 1
        assert iteraciones[0].output_prompt is None
        assert iteraciones[0].optimizer_raw == {"raw": "basura"}

        audits = db.query(Audit).filter(Audit.iteration_id == iteraciones[0].id).all()
        assert len(audits) == 0  # sin output_prompt no hay nada que auditar
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_auditor_parse_error_guarda_fila_parse_ok_false_y_run_en_error(db, monkeypatch):
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _stub(_optimizer_result()))
    error = AuditorParseError("JSON inválido tras reintentar", raw_response={"raw": "basura del auditor"})
    monkeypatch.setattr("backend.services.workflow.audit_prompt", _stub(exc=error))

    run = await create_run(db, "resume este texto")
    try:
        assert run.status == "ERROR"
        assert run.error_message is not None

        iteraciones = db.query(Iteration).filter(Iteration.run_id == run.id).all()
        assert len(iteraciones) == 1
        assert iteraciones[0].output_prompt == "prompt mejorado de prueba"  # el Optimizer sí tuvo éxito

        audits = db.query(Audit).filter(Audit.iteration_id == iteraciones[0].id).all()
        assert len(audits) == 1
        assert audits[0].parse_ok is False
        assert audits[0].raw_response == {"raw": "basura del auditor"}
        assert audits[0].total_score is None
        assert (audits[0].gates_passed, audits[0].gates_failed, audits[0].gates_not_applicable) == (0, 0, 0)
    finally:
        _borrar(db, run)


# ---------------------------------------------------------------------------
# Transiciones inválidas a nivel de integración (con Run/DB reales)
# ---------------------------------------------------------------------------


def test_ejecutar_sin_aprobar(db):
    run = _crear_run_minimo(db, status="WAITING_HUMAN")
    try:
        with pytest.raises(InvalidTransitionError) as exc_info:
            start_execution(db, run)
        assert exc_info.value.current_status == "WAITING_HUMAN"
        assert exc_info.value.target_status == "EXECUTING"
        assert run.status == "WAITING_HUMAN"  # no debe haber cambiado
    finally:
        _borrar(db, run)


def test_aprobar_dos_veces(db):
    run = _crear_run_minimo(db, status="WAITING_HUMAN")
    try:
        run = approve_run(db, run)
        assert run.status == "APPROVED"

        with pytest.raises(InvalidTransitionError) as exc_info:
            approve_run(db, run)
        assert exc_info.value.current_status == "APPROVED"
        assert exc_info.value.target_status == "APPROVED"
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_iterar_desde_completed(db):
    run = _crear_run_minimo(db, status="COMPLETED")
    try:
        with pytest.raises(InvalidTransitionError) as exc_info:
            await iterate_run(db, run, "esto no debería funcionar")
        assert exc_info.value.current_status == "COMPLETED"
        assert exc_info.value.target_status == "ITERATING"
    finally:
        _borrar(db, run)
