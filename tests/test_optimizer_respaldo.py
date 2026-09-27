"""Modelo de respaldo del Optimizer de prompts (punto 4): en la validación
de los 7 prompts del SDLC, kimi-k3 devolvió content vacío en los 3
reintentos de una auto-iteración y el run de Arquitectura terminó en ERROR."""

import pytest

from backend.config import get_settings
from backend.models import Iteration
from backend.services import workflow
from backend.services.nvidia_client import NvidiaAuthError, NvidiaEmptyResponseError
from backend.services.prompt_optimizer import OptimizerParseError
from backend.services.workflow import create_run
from tests.test_linea_base import _Registro, db  # noqa: F401  (fixture db)
from tests.test_workflow_integration import _auditor_result, _optimizer_result

_VACIA = {"choices": [{"finish_reason": "stop", "message": {"content": None, "reasoning_content": "!!!!"}}]}


def _con_modelo(resultado, modelo):
    resultado.model = modelo
    return resultado


def _iteraciones(db, run):
    return db.query(Iteration).filter(Iteration.run_id == run.id).order_by(Iteration.iteration_number).all()


async def test_si_el_optimizer_degenera_se_usa_el_de_respaldo_y_queda_registrado(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "improver_fallback_model", "modelo/respaldo")
    optimizador = _Registro(
        [NvidiaEmptyResponseError("vacío", _VACIA), _con_modelo(_optimizer_result("mejorado"), "modelo/respaldo")]
    )
    monkeypatch.setattr(workflow, "optimize_prompt", optimizador)
    monkeypatch.setattr(workflow, "audit_prompt", _Registro([_auditor_result()]))

    run = await create_run(db, "resume este texto")
    db.creados.append(run)

    assert run.status == "WAITING_HUMAN"
    assert [llamada[1]["model"] for llamada in optimizador.llamadas] == [run.optimizer_model, "modelo/respaldo"]
    (it,) = _iteraciones(db, run)
    assert it.output_prompt == "mejorado"
    assert it.model == "modelo/respaldo"
    assert it.optimizer_fallback["from_model"] == run.optimizer_model
    assert it.optimizer_fallback["raw_response"] == _VACIA


async def test_sin_respaldo_la_degeneracion_deja_error_y_guarda_el_crudo(db, monkeypatch):
    monkeypatch.setattr(workflow, "optimize_prompt", _Registro([NvidiaEmptyResponseError("vacío", _VACIA)]))
    monkeypatch.setattr(workflow, "audit_prompt", _Registro([]))

    run = await create_run(db, "resume este texto")
    db.creados.append(run)

    assert run.status == "ERROR"
    (it,) = _iteraciones(db, run)
    assert it.output_prompt is None and it.optimizer_raw == _VACIA


async def test_si_tambien_falla_el_respaldo_queda_error_con_ambos_motivos(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "improver_fallback_model", "modelo/respaldo")
    monkeypatch.setattr(
        workflow,
        "optimize_prompt",
        _Registro([NvidiaEmptyResponseError("vacío", _VACIA), OptimizerParseError("JSON inválido", {"r": 2})]),
    )
    monkeypatch.setattr(workflow, "audit_prompt", _Registro([]))

    run = await create_run(db, "resume este texto")
    db.creados.append(run)

    assert run.status == "ERROR"
    assert "principal" in run.error_message and "respaldo" in run.error_message
    (it,) = _iteraciones(db, run)
    assert it.optimizer_raw == {"r": 2}
    assert it.optimizer_fallback["raw_response"] == _VACIA


async def test_un_401_no_usa_el_respaldo(db, monkeypatch):
    monkeypatch.setattr(get_settings(), "improver_fallback_model", "modelo/respaldo")
    optimizador = _Registro([NvidiaAuthError("401")])
    monkeypatch.setattr(workflow, "optimize_prompt", optimizador)

    run = await create_run(db, "resume este texto")
    db.creados.append(run)

    assert run.status == "ERROR"
    assert len(optimizador.llamadas) == 1


async def test_la_iteracion_normal_registra_el_modelo_que_la_produjo(db, monkeypatch):
    monkeypatch.setattr(
        workflow, "optimize_prompt", _Registro([_con_modelo(_optimizer_result(), "moonshotai/kimi-k3")])
    )
    monkeypatch.setattr(workflow, "audit_prompt", _Registro([_auditor_result()]))

    run = await create_run(db, "resume este texto")
    db.creados.append(run)

    (it,) = _iteraciones(db, run)
    assert it.model == "moonshotai/kimi-k3" and it.optimizer_fallback is None
