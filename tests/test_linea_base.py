"""Auditoría de línea base (Parcial 1, punto 4): el prompt original se
audita tal cual antes de optimizarlo, para tener métricas iniciales y
delta. Contra PostgreSQL real, con las IAs mockeadas."""

import pytest

from backend.database import SessionLocal
from backend.models import Audit, Iteration
from backend.services import workflow
from backend.services.prompt_auditor import AuditorParseError
from backend.services.workflow import approve_run, build_timeline, create_run
from tests.test_workflow_integration import _auditor_result, _optimizer_result


@pytest.fixture
def db():
    session = SessionLocal()
    creados = []
    session.creados = creados
    try:
        yield session
    finally:
        session.rollback()
        for run in creados:
            session.delete(session.merge(run))
        session.commit()
        session.close()


class _Registro:
    def __init__(self, resultados):
        self.resultados = list(resultados)
        self.llamadas = []

    async def __call__(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        siguiente = self.resultados.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


def _iteraciones(db, run):
    return db.query(Iteration).filter(Iteration.run_id == run.id).order_by(Iteration.iteration_number).all()


async def test_con_linea_base_se_audita_el_original_y_luego_el_optimizado(db, monkeypatch):
    optimizador = _Registro([_optimizer_result("prompt optimizado")])
    auditor = _Registro([_auditor_result({"gate_1_estructura_instruccion": "FAIL"}), _auditor_result()])
    monkeypatch.setattr(workflow, "optimize_prompt", optimizador)
    monkeypatch.setattr(workflow, "audit_prompt", auditor)

    run = await create_run(db, "resume este texto", baseline_audit=True)
    db.creados.append(run)

    assert run.status == "WAITING_HUMAN"
    base, optimizada = _iteraciones(db, run)
    assert (base.iteration_number, base.source) == (1, "original")
    assert base.input_prompt == base.output_prompt == "resume este texto"
    assert (optimizada.iteration_number, optimizada.source) == (2, "optimizer")
    # Se auditó primero el original y después la versión optimizada.
    assert [llamada[0][0] for llamada in auditor.llamadas] == ["resume este texto", "prompt optimizado"]
    # Es solo medición: el Optimizer no recibe la auditoría de la línea base.
    assert optimizador.llamadas[0][1]["audit_feedback"] is None
    auditorias = {i.source: db.query(Audit).filter(Audit.iteration_id == i.id).one() for i in (base, optimizada)}
    assert auditorias["original"].gates_failed == 1
    assert auditorias["optimizer"].gates_failed == 0


async def test_sin_linea_base_el_flujo_no_cambia(db, monkeypatch):
    monkeypatch.setattr(workflow, "optimize_prompt", _Registro([_optimizer_result()]))
    monkeypatch.setattr(workflow, "audit_prompt", _Registro([_auditor_result()]))

    run = await create_run(db, "resume este texto")
    db.creados.append(run)

    assert [(i.iteration_number, i.source) for i in _iteraciones(db, run)] == [(1, "optimizer")]


async def test_aprobar_con_linea_base_aprueba_la_version_optimizada(db, monkeypatch):
    monkeypatch.setattr(workflow, "optimize_prompt", _Registro([_optimizer_result("prompt optimizado")]))
    monkeypatch.setattr(workflow, "audit_prompt", _Registro([_auditor_result(), _auditor_result()]))

    run = await create_run(db, "resume este texto", baseline_audit=True)
    db.creados.append(run)
    approve_run(db, run)

    base, optimizada = _iteraciones(db, run)
    assert [d.decision for d in optimizada.human_decisions] == ["approve"]
    assert base.human_decisions == []


async def test_si_falla_la_auditoria_de_linea_base_no_se_optimiza(db, monkeypatch):
    optimizador = _Registro([_optimizer_result()])
    monkeypatch.setattr(workflow, "optimize_prompt", optimizador)
    monkeypatch.setattr(
        workflow, "audit_prompt", _Registro([AuditorParseError("JSON inválido", raw_response={"crudo": 1})])
    )

    run = await create_run(db, "resume este texto", baseline_audit=True)
    db.creados.append(run)

    assert run.status == "ERROR"
    assert optimizador.llamadas == []
    (base,) = _iteraciones(db, run)
    auditoria = db.query(Audit).filter(Audit.iteration_id == base.id).one()
    assert auditoria.parse_ok is False and auditoria.raw_response == {"crudo": 1}


async def test_el_timeline_nombra_la_linea_base(db, monkeypatch):
    monkeypatch.setattr(workflow, "optimize_prompt", _Registro([_optimizer_result()]))
    monkeypatch.setattr(workflow, "audit_prompt", _Registro([_auditor_result(), _auditor_result()]))

    run = await create_run(db, "resume este texto", baseline_audit=True)
    db.creados.append(run)
    db.refresh(run)

    descripciones = [e.description for e in build_timeline(run)]
    assert any("línea base" in d for d in descripciones)
