"""Robustez de la plataforma de prompts (runs) ante varios procesos
simultáneos y reinicios del servidor: los mismos defectos que se
encontraron en la capa de requisitos durante el punto 3.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.database import SessionLocal, engine
from backend.main import app
from backend.models import Run
from backend.services import requirements_workflow, workflow
from backend.services.workflow import recover_interrupted_runs as _recuperar_runs_real
from tests.test_workflow_integration import _auditor_result, _optimizer_result


def _borrar_run(run_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, uuid.UUID(run_id))
        if run is not None:
            db.delete(run)
            db.commit()
    finally:
        db.close()


def test_crear_iterar_y_editar_no_retienen_conexiones_mientras_espera_a_la_ia(monkeypatch):
    ocupadas: list[tuple[str, int]] = []

    async def optimizador(*args, **kwargs):
        ocupadas.append(("optimizer", engine.pool.checkedout()))
        return _optimizer_result()

    async def auditor(*args, **kwargs):
        ocupadas.append(("auditor", engine.pool.checkedout()))
        return _auditor_result()

    monkeypatch.setattr(workflow, "optimize_prompt", optimizador)
    monkeypatch.setattr(workflow, "audit_prompt", auditor)

    with TestClient(app) as c:
        base = engine.pool.checkedout()
        run_id = c.post("/api/runs", json={"prompt": "resume este texto"}).json()["id"]
        c.post(f"/api/runs/{run_id}/iterate", json={"feedback": "más breve"})
        c.post(f"/api/runs/{run_id}/edit", json={"prompt": "resume en 3 frases"})
        estado = c.get(f"/api/runs/{run_id}").json()["status"]

    _borrar_run(run_id)
    assert estado == "WAITING_HUMAN"
    assert [etapa for etapa, _ in ocupadas] == ["optimizer", "auditor", "optimizer", "auditor", "auditor"]
    assert [n for _, n in ocupadas] == [base] * 5


def test_un_run_cerrado_por_otro_proceso_no_se_sobrescribe_con_completed():
    """Incidente real del punto 4: el run de Arquitectura pasó a ERROR desde
    otra sesión mientras el Executor corría; al terminar, el Executor lo
    marcó COMPLETED y guardó el resultado, validando la transición contra su
    copia en memoria (EXECUTING) en lugar de contra la BD."""
    from backend.models import Result
    from backend.services.workflow import InvalidTransitionError, complete_execution, fail_run

    db = SessionLocal(expire_on_commit=False)  # como las sesiones de fondo
    try:
        run = Run(status="EXECUTING", original_prompt="p", optimizer_model="m", auditor_model="m",
                  executor_model="m")
        db.add(run)
        db.commit()
        run_id = str(run.id)

        otra = SessionLocal()
        try:
            fail_run(otra, otra.get(Run, run.id), "cerrado por otro proceso")
        finally:
            otra.close()

        with pytest.raises(InvalidTransitionError):
            complete_execution(db, run, final_response="respuesta", model="m")
        db.rollback()

        db.expire_all()
        assert db.get(Run, run.id).status == "ERROR"
        assert db.query(Result).filter(Result.run_id == run.id).count() == 0
    finally:
        db.close()
        _borrar_run(run_id)


def test_arrancar_la_app_en_los_tests_no_toca_runs_reales_en_curso():
    """Reproduce el incidente real: al correr los tests, el arranque de la
    app (TestClient) pasó a ERROR un run que el usuario estaba ejecutando en
    su servidor local. conftest.py desactiva la recuperación en los tests."""
    db = SessionLocal()
    try:
        run = Run(status="EXECUTING", original_prompt="p", optimizer_model="m", auditor_model="m",
                  executor_model="m")
        db.add(run)
        db.commit()
        run_id = str(run.id)
    finally:
        db.close()

    with TestClient(app):
        pass

    db = SessionLocal()
    try:
        assert db.get(Run, uuid.UUID(run_id)).status == "EXECUTING"
    finally:
        db.close()
        _borrar_run(run_id)


@pytest.mark.parametrize(
    ("estado", "debe_cerrarse"),
    [
        ("CREATED", True),
        ("OPTIMIZING", True),
        ("AUDITING", True),
        ("GATING", True),
        ("ITERATING", True),
        ("EXECUTING", True),
        # Estos esperan una decisión humana, no a un proceso: no se tocan.
        ("WAITING_HUMAN", False),
        ("APPROVED", False),
        ("COMPLETED", False),
    ],
)
def test_al_arrancar_se_cierran_los_runs_interrumpidos(estado, debe_cerrarse):
    db = SessionLocal()
    try:
        run = Run(status=estado, original_prompt="p", optimizer_model="m", auditor_model="m", executor_model="m")
        db.add(run)
        db.commit()
        run_id = str(run.id)

        # Limitado a este run: no toca datos reales de la BD.
        _recuperar_runs_real(db, ids=[run.id])

        db.expire_all()
        run = db.get(Run, run.id)
        if debe_cerrarse:
            assert run.status == "ERROR"
            assert run.error_message == workflow.MENSAJE_RUN_INTERRUMPIDO
        else:
            assert run.status == estado
    finally:
        db.close()
        _borrar_run(run_id)
