"""Tests de la auto-iteración (workflow.advance_auto_iterate) contra
PostgreSQL real, con optimize_prompt/audit_prompt mockeados (sin llamadas
a NVIDIA). Cubre las dos condiciones de parada: meta alcanzada e
intentos agotados, y que nunca aprueba/ejecuta por sí sola.
"""

import pytest

from backend.database import SessionLocal
from backend.models import HumanDecision, Iteration, Run
from backend.schemas.auditor import GATE_PROPERTIES, AuditorResponse
from backend.schemas.optimizer import OptimizerResponse
from backend.services.prompt_auditor import AuditorResult
from backend.services.prompt_optimizer import OptimizerResult
from backend.services.workflow import (
    DEFAULT_AUTO_ITERATE_MAX_ATTEMPTS,
    InvalidTransitionError,
    advance_auto_iterate,
    create_run,
    ensure_can_start_iteration,
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


def _gate_completo(gate: str) -> dict:
    return {
        "gate": gate,
        "status": "PASS",
        "justification": "justificación de prueba",
        "properties": [
            {"property_id": pid, "property_name": nombre, "score": 7, "observation": "ok"}
            for pid, nombre in GATE_PROPERTIES[gate].items()
        ],
    }


def _auditor_result_con_score(total_score: int) -> AuditorResult:
    ar = AuditorResponse.model_validate(
        {
            "gates": [_gate_completo(g) for g in GATE_PROPERTIES],
            "total_score": total_score,
            "recommendations": [f"recomendación para llegar a {total_score + 5}"],
        }
    )
    passed, failed, na = ar.gate_counts()
    return AuditorResult(
        audit_response=ar,
        raw_response={"mock": "auditor", "total_score": total_score},
        model="mock-auditor",
        prompt_tokens=10,
        completion_tokens=10,
        total_tokens=20,
        gates_passed=passed,
        gates_failed=failed,
        gates_not_applicable=na,
        gates_score=ar.gates_score(),
    )


def _optimizer_result(improved_prompt: str) -> OptimizerResult:
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


def _secuencia_optimizer(prompts: list[str]):
    resultados = [_optimizer_result(p) for p in prompts]

    async def _fn(*args, **kwargs):
        return resultados.pop(0)

    return _fn


def _secuencia_auditor(scores: list[int]):
    resultados = [_auditor_result_con_score(s) for s in scores]

    async def _fn(*args, **kwargs):
        return resultados.pop(0)

    return _fn


@pytest.mark.asyncio
async def test_se_detiene_al_alcanzar_target_score(db, monkeypatch):
    # primera auditoría (dentro de create_run): 62. Luego, dentro del
    # auto-iterate: 75, después 92 (>= target=90): debe parar ahí, sin
    # gastar el tercer intento disponible.
    monkeypatch.setattr(
        "backend.services.workflow.optimize_prompt",
        _secuencia_optimizer(["v1", "v2", "v3"]),
    )
    monkeypatch.setattr(
        "backend.services.workflow.audit_prompt",
        _secuencia_auditor([62, 75, 92]),
    )

    run = await create_run(db, "prompt de prueba")
    try:
        await advance_auto_iterate(db, run, target_score=90, max_attempts=5)

        assert run.status == "WAITING_HUMAN"
        iteraciones = (
            db.query(Iteration).filter(Iteration.run_id == run.id).order_by(Iteration.iteration_number).all()
        )
        assert len(iteraciones) == 3  # 1 inicial + 2 auto (se detuvo al llegar a 92, no usó el 3er intento)
        assert iteraciones[-1].audits[0].total_score == 92

        decisiones_auto = [
            hd
            for it in iteraciones
            for hd in it.human_decisions
            if hd.decision == "iterate" and hd.feedback and hd.feedback.startswith("[AUTO-ITERACIÓN")
        ]
        assert len(decisiones_auto) == 2
        assert decisiones_auto[0].feedback.startswith("[AUTO-ITERACIÓN 1/5]")
        assert decisiones_auto[1].feedback.startswith("[AUTO-ITERACIÓN 2/5]")
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_agota_intentos_sin_alcanzar_target_y_no_rompe(db, monkeypatch):
    # nunca llega a 90: con max_attempts=2 debe hacer exactamente 2
    # vueltas automáticas y quedar en WAITING_HUMAN con el último score real.
    monkeypatch.setattr(
        "backend.services.workflow.optimize_prompt",
        _secuencia_optimizer(["v1", "v2", "v3"]),
    )
    monkeypatch.setattr(
        "backend.services.workflow.audit_prompt",
        _secuencia_auditor([60, 70, 78]),
    )

    run = await create_run(db, "prompt de prueba")
    try:
        await advance_auto_iterate(db, run, target_score=90, max_attempts=2)

        assert run.status == "WAITING_HUMAN"  # nunca ERROR solo por no llegar a la meta
        iteraciones = (
            db.query(Iteration).filter(Iteration.run_id == run.id).order_by(Iteration.iteration_number).all()
        )
        assert len(iteraciones) == 3  # 1 inicial + exactamente 2 (max_attempts), ni una más
        assert iteraciones[-1].audits[0].total_score == 78  # score real, no inflado a 90
    finally:
        _borrar(db, run)


@pytest.mark.asyncio
async def test_no_itera_si_ya_alcanzo_la_meta(db, monkeypatch):
    monkeypatch.setattr("backend.services.workflow.optimize_prompt", _secuencia_optimizer(["v1"]))
    monkeypatch.setattr("backend.services.workflow.audit_prompt", _secuencia_auditor([95]))

    run = await create_run(db, "prompt de prueba")
    try:
        await advance_auto_iterate(db, run, target_score=90, max_attempts=DEFAULT_AUTO_ITERATE_MAX_ATTEMPTS)

        iteraciones = db.query(Iteration).filter(Iteration.run_id == run.id).all()
        assert len(iteraciones) == 1  # no gastó ningún intento automático: ya estaba en la meta
        assert run.status == "WAITING_HUMAN"
    finally:
        _borrar(db, run)


def test_ensure_can_start_iteration_rechaza_fuera_de_waiting_human(db):
    run = Run(
        status="APPROVED",
        original_prompt="prompt de prueba",
        optimizer_model="mock",
        auditor_model="mock",
        executor_model="mock",
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    try:
        with pytest.raises(InvalidTransitionError):
            ensure_can_start_iteration(run)
    finally:
        _borrar(db, run)
