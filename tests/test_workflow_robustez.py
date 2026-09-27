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


@pytest.fixture(autouse=True)
def _sin_recuperacion_al_arrancar(monkeypatch):
    # El arranque de la app cierra lo que esté en curso en la BD real; en
    # los tests no debe tocar lo que haga un servidor local en paralelo.
    monkeypatch.setattr(requirements_workflow, "recover_interrupted", lambda db: 0)
    monkeypatch.setattr(workflow, "recover_interrupted_runs", lambda db: 0)


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
