"""Tests de la capa de Ingeniería de Requisitos (Parcial 1, Componente 1).

- Schemas: exactamente los 10 criterios, escala 1-10, fórmula del puntaje
  global y umbral de alta calidad.
- Evaluador: camino de reintento con chat_completion mockeado.
- Flujo: contra PostgreSQL real, con evaluate_requirement/improve_requirement
  mockeados (sin llamadas a NVIDIA). Cada test borra lo que crea.
"""

import json
import re

import pytest
from pydantic import ValidationError

from backend.database import SessionLocal
from backend.models import RequirementAnalysis, RequirementEvaluation
from backend.schemas.requirements import (
    REQUIREMENT_CRITERIA,
    RequirementEvaluationResponse,
    RequirementImprovementResponse,
)
from backend.services import requirements_workflow
from backend.services.nvidia_client import NvidiaAuthError, NvidiaChatResult, NvidiaEmptyResponseError
from backend.services.requirements_evaluator import (
    EvaluatorParseError,
    EvaluatorResult,
    evaluate_requirement,
)
from backend.services.requirements_improver import (
    ImproverParseError,
    ImproverResult,
    improve_requirement,
)
from backend.services.workflow import InvalidTransitionError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _payload_evaluacion(scores: dict[str, int] | None = None, default: int = 5, **extra) -> dict:
    scores = scores or {}
    payload = {
        "criteria": [
            {
                "criterion": clave,
                "score": scores.get(clave, default),
                "finding": "hallazgo de prueba",
                "recommendation": "",
            }
            for clave in REQUIREMENT_CRITERIA
        ],
        "ambiguous_terms": [{"term": "rápido", "reason": "no es medible"}],
        "is_compound": False,
        "missing_information": ["tiempo máximo de respuesta"],
        "clarification_questions": ["¿Cuál es el tiempo máximo aceptable?"],
        "summary": "diagnóstico de prueba",
    }
    payload.update(extra)
    return payload


def _evaluacion(default: int = 5, scores: dict[str, int] | None = None) -> RequirementEvaluationResponse:
    return RequirementEvaluationResponse.model_validate(_payload_evaluacion(scores, default))


def _evaluator_result(default: int = 5) -> EvaluatorResult:
    return EvaluatorResult(
        evaluation=_evaluacion(default),
        raw_response={"mock": "evaluator", "default": default},
        model="mock-evaluator",
        prompt_tokens=10,
        completion_tokens=20,
        latency_ms=1234,
    )


def _improver_result() -> ImproverResult:
    return ImproverResult(
        improvement=RequirementImprovementResponse(
            improved_requirement="El sistema deberá responder en [POR DEFINIR: tiempo máximo].",
            acceptance_criteria=["Dado un usuario, cuando consulta, entonces recibe respuesta."],
            changes=["Se reemplazó 'rápido' por un marcador POR DEFINIR."],
            pending_items=["tiempo máximo de respuesta"],
            intent_preservation="Se mantiene la necesidad de una respuesta oportuna.",
        ),
        raw_response={"mock": "improver"},
        model="mock-improver",
        total_tokens=50,
        latency_ms=2345,
        unsupported_values=[],
    )


class _Secuencia:
    """Devuelve (o lanza) el siguiente elemento de la lista en cada llamada."""

    def __init__(self, resultados: list):
        self._resultados = list(resultados)
        self.llamadas: list[tuple] = []

    async def __call__(self, *args, **kwargs):
        self.llamadas.append((args, kwargs))
        if not self._resultados:
            raise AssertionError("mock llamado más veces de las esperadas")
        siguiente = self._resultados.pop(0)
        if isinstance(siguiente, Exception):
            raise siguiente
        return siguiente


@pytest.fixture
def db():
    session = SessionLocal()
    creados: list[RequirementAnalysis] = []
    session.creados = creados
    try:
        yield session
    finally:
        session.rollback()
        for analysis in creados:
            session.delete(session.merge(analysis))
        session.commit()
        session.close()


def _nuevo_analisis(db, texto: str = "El sistema debe ser rápido.", **kwargs) -> RequirementAnalysis:
    analysis = requirements_workflow.start_analysis(db, texto, **kwargs)
    db.creados.append(analysis)
    return analysis


def _evaluaciones(db, analysis: RequirementAnalysis) -> dict[str, RequirementEvaluation]:
    filas = db.query(RequirementEvaluation).filter_by(analysis_id=analysis.id).all()
    return {f.stage: f for f in filas}


# ---------------------------------------------------------------------------
# Schemas y fórmula del puntaje
# ---------------------------------------------------------------------------


def test_exige_exactamente_los_10_criterios():
    payload = _payload_evaluacion()
    payload["criteria"] = payload["criteria"][:-1]
    with pytest.raises(ValidationError, match="faltan"):
        RequirementEvaluationResponse.model_validate(payload)


def test_rechaza_criterios_inventados_o_duplicados():
    payload = _payload_evaluacion()
    payload["criteria"][0]["criterion"] = "belleza"
    with pytest.raises(ValidationError, match="sobran"):
        RequirementEvaluationResponse.model_validate(payload)

    payload = _payload_evaluacion()
    payload["criteria"][1]["criterion"] = payload["criteria"][0]["criterion"]
    with pytest.raises(ValidationError, match="duplicados"):
        RequirementEvaluationResponse.model_validate(payload)


def test_acepta_variantes_de_escritura_del_mismo_criterio():
    payload = _payload_evaluacion()
    payload["criteria"][9]["criterion"] = "criterios_aceptación"  # con tilde
    payload["criteria"][8]["criterion"] = "Ausencia de ambigüedad"  # nombre visible
    evaluacion = RequirementEvaluationResponse.model_validate(payload)
    claves = {c.criterion for c in evaluacion.criteria}
    assert claves == set(REQUIREMENT_CRITERIA)


@pytest.mark.parametrize("score", [0, 11])
def test_score_fuera_de_escala_es_invalido(score):
    with pytest.raises(ValidationError):
        RequirementEvaluationResponse.model_validate(
            _payload_evaluacion({"claridad": score})
        )


def test_global_score_es_el_promedio_por_10():
    # 9 criterios en 8 y uno en 9 -> promedio 8.1 -> 81
    evaluacion = _evaluacion(default=8, scores={"claridad": 9})
    assert evaluacion.global_score() == 81


def test_alta_calidad_requiere_80_y_ningun_criterio_bajo_6():
    assert _evaluacion(default=8).is_high_quality()
    assert not _evaluacion(default=7).is_high_quality()  # 70 < 80
    # Promedio 86 (>= 80) pero un criterio en 5: no es alta calidad.
    assert _evaluacion(default=9, scores={"verificabilidad": 5}).global_score() == 86
    assert not _evaluacion(default=9, scores={"verificabilidad": 5}).is_high_quality()


def _mejora(texto: str, criterios: list[str] | None = None) -> RequirementImprovementResponse:
    return RequirementImprovementResponse(
        improved_requirement=texto,
        acceptance_criteria=criterios or ["Dado X, cuando Y, entonces Z."],
        intent_preservation="se conserva",
    )


def test_detecta_valores_numericos_sin_respaldo():
    # Caso real observado con qwen2.5-coder:7b: inventó "30 segundos" y "95%".
    mejora = _mejora(
        "El sistema deberá enviar notificaciones en un máximo de 30 segundos.",
        ["Dado un usuario, entonces el 95% completa la tarea."],
    )
    assert mejora.unsupported_values("El sistema debe ser rápido.") == ["30", "95"]


def test_no_marca_valores_respaldados_por_default_ni_la_numeracion():
    mejora = _mejora(
        "REQ-1: El sistema deberá responder en 2 segundos. "
        "REQ-2: Deberá soportar [POR DEFINIR: número de usuarios, p. ej. 500] usuarios."
    )
    assert mejora.unsupported_values("debe ser rápido", None, "Máximo 2 segundos.") == []


def test_mismo_numero_con_otra_notacion_no_es_inventado():
    mejora = _mejora("El catálogo tendrá hasta 20.000 productos y 1,500 marcas; tiempo 2,5 s.")
    fuente = "Catálogo de hasta 20000 productos, 1500 marcas y respuesta en 2.5 segundos."
    assert mejora.unsupported_values(fuente) == []
    # Un valor realmente distinto se sigue detectando.
    assert _mejora("Hasta 30.000 productos.").unsupported_values(fuente) == ["30.000"]


def test_sub_requisitos_en_lista_se_unen_en_un_texto():
    mejora = RequirementImprovementResponse.model_validate(
        {
            "improved_requirement": ["REQ-1: El sistema deberá A.", "REQ-2: El sistema deberá B."],
            "acceptance_criteria": ["Dado X, cuando Y, entonces Z."],
            "intent_preservation": "se conserva",
        }
    )
    assert mejora.improved_requirement == "REQ-1: El sistema deberá A.\nREQ-2: El sistema deberá B."


def _bloques_json(texto: str) -> list[str]:
    """Bloques que empiezan con '{' en su propia línea y terminan con '}'."""
    return re.findall(r"^\{\n.*?^\}$", texto, re.MULTILINE | re.DOTALL)


def test_las_plantillas_de_los_system_prompts_son_json_valido():
    # Un comentario "// ..." en la plantilla hizo que deepseek-v4-pro
    # devolviera JSON inválido en Render: las plantillas deben ser copiables.
    from backend.services.prompts.requirements_evaluator_system_prompt import (
        REQUIREMENTS_EVALUATOR_SYSTEM_PROMPT,
    )
    from backend.services.prompts.requirements_improver_system_prompt import (
        REQUIREMENTS_IMPROVER_SYSTEM_PROMPT,
    )

    evaluador = _bloques_json(REQUIREMENTS_EVALUATOR_SYSTEM_PROMPT)
    assert len(evaluador) == 1
    RequirementEvaluationResponse.model_validate_json(evaluador[0])

    mejorador = _bloques_json(REQUIREMENTS_IMPROVER_SYSTEM_PROMPT)
    assert len(mejorador) == 2  # el ejemplo y el formato de salida
    for bloque in mejorador:
        RequirementImprovementResponse.model_validate_json(bloque)

    for prompt in (REQUIREMENTS_EVALUATOR_SYSTEM_PROMPT, REQUIREMENTS_IMPROVER_SYSTEM_PROMPT):
        assert "//" not in prompt


def test_texto_reevaluado_incluye_los_criterios_de_aceptacion():
    texto = _improver_result().improvement.text_for_evaluation()
    assert "Criterios de aceptación:" in texto
    assert "- Dado un usuario" in texto


# ---------------------------------------------------------------------------
# Evaluador: reintento ante JSON inválido
# ---------------------------------------------------------------------------


def _nvidia(content: str, raw: dict) -> NvidiaChatResult:
    return NvidiaChatResult(
        content=content,
        reasoning_content=None,
        model="mock",
        raw_response=raw,
        prompt_tokens=1,
        completion_tokens=1,
        total_tokens=2,
    )


async def test_evaluador_reintenta_una_vez_y_luego_acepta(monkeypatch):
    stub = _Secuencia(
        [_nvidia("no es json", {"n": 1}), _nvidia(json.dumps(_payload_evaluacion()), {"n": 2})]
    )
    monkeypatch.setattr("backend.services.requirements_evaluator.chat_completion", stub)

    resultado = await evaluate_requirement("El sistema debe ser rápido.")

    assert len(stub.llamadas) == 2
    assert resultado.raw_response == {"n": 2}
    assert resultado.evaluation.global_score() == 50


async def test_modo_json_pide_response_format_solo_si_esta_activo(monkeypatch):
    from backend.config import get_settings

    llamadas = []

    async def stub(model, messages, *, max_tokens=None, extra_payload=None):
        llamadas.append(extra_payload)
        return _nvidia(json.dumps(_payload_evaluacion()), {})

    monkeypatch.setattr("backend.services.requirements_evaluator.chat_completion", stub)
    settings = get_settings()

    # Punto de partida explícito: no depende de LLM_JSON_MODE_MODELS del .env local.
    monkeypatch.setattr(settings, "json_mode_models", frozenset())
    await evaluate_requirement("req")
    monkeypatch.setattr(settings, "json_mode_models", frozenset({"modelo-con-json"}))
    await evaluate_requirement("req", model="modelo-con-json")
    await evaluate_requirement("req", model="otro-modelo")

    assert "response_format" not in llamadas[0]
    assert llamadas[1]["response_format"] == {"type": "json_object"}
    assert llamadas[1]["chat_template_kwargs"] == {"thinking": False}
    assert "response_format" not in llamadas[2]  # el modo JSON es por modelo


async def test_evaluador_falla_tras_dos_json_invalidos_y_conserva_el_raw(monkeypatch):
    stub = _Secuencia([_nvidia("{{{", {"n": 1}), _nvidia("]]]", {"n": 2})])
    monkeypatch.setattr("backend.services.requirements_evaluator.chat_completion", stub)

    with pytest.raises(EvaluatorParseError) as info:
        await evaluate_requirement("El sistema debe ser rápido.")

    assert info.value.raw_response == {"n": 2}
    assert len(stub.llamadas) == 2


def _payload_mejora(texto: str) -> str:
    return json.dumps(
        {
            "improved_requirement": texto,
            "acceptance_criteria": ["Dado X, cuando Y, entonces Z."],
            "changes": [],
            "pending_items": [],
            "intent_preservation": "se conserva",
        }
    )


async def test_mejorador_pide_corregir_valores_inventados(monkeypatch):
    stub = _Secuencia(
        [
            _nvidia(_payload_mejora("El sistema deberá responder en 30 segundos."), {"n": 1}),
            _nvidia(_payload_mejora("El sistema deberá responder en [POR DEFINIR: tiempo]."), {"n": 2}),
        ]
    )
    monkeypatch.setattr("backend.services.requirements_improver.chat_completion", stub)

    resultado = await improve_requirement("El sistema debe ser rápido.", _evaluacion())

    assert len(stub.llamadas) == 2
    assert "30" in stub.llamadas[1][1]["messages"][-1]["content"]
    assert resultado.unsupported_values == []
    assert resultado.unsupported_retry is True
    assert resultado.raw_response == {"n": 2}
    assert resultado.total_tokens == 4  # suma de las dos llamadas


async def test_mejorador_conserva_la_advertencia_si_el_modelo_insiste(monkeypatch):
    stub = _Secuencia(
        [
            _nvidia(_payload_mejora("Responder en 30 segundos."), {"n": 1}),
            _nvidia(_payload_mejora("Responder en 30 segundos, de verdad."), {"n": 2}),
        ]
    )
    monkeypatch.setattr("backend.services.requirements_improver.chat_completion", stub)

    resultado = await improve_requirement("El sistema debe ser rápido.", _evaluacion())

    assert len(stub.llamadas) == 2  # no reintenta indefinidamente
    assert resultado.unsupported_values == ["30"]


async def test_mejorador_sin_valores_inventados_no_reintenta(monkeypatch):
    stub = _Secuencia([_nvidia(_payload_mejora("Responder en [POR DEFINIR: tiempo]."), {"n": 1})])
    monkeypatch.setattr("backend.services.requirements_improver.chat_completion", stub)

    resultado = await improve_requirement("El sistema debe ser rápido.", _evaluacion())

    assert len(stub.llamadas) == 1
    assert resultado.unsupported_retry is False


# ---------------------------------------------------------------------------
# Flujo completo contra PostgreSQL real
# ---------------------------------------------------------------------------


def _mockear(
    monkeypatch, evaluaciones: list, mejoras: list, respaldo: str | None = None
) -> tuple[_Secuencia, _Secuencia]:
    """Reemplaza las IAs y fija IMPROVER_FALLBACK_MODEL (por defecto sin
    respaldo), para que ningún test dependa del .env local."""
    from backend.config import get_settings

    evaluador = _Secuencia(evaluaciones)
    mejorador = _Secuencia(mejoras)
    monkeypatch.setattr(requirements_workflow, "evaluate_requirement", evaluador)
    monkeypatch.setattr(requirements_workflow, "improve_requirement", mejorador)
    monkeypatch.setattr(get_settings(), "improver_fallback_model", respaldo)
    return evaluador, mejorador


async def test_requisito_de_baja_calidad_se_mejora_y_se_reevalua(db, monkeypatch):
    evaluador, mejorador = _mockear(
        monkeypatch, [_evaluator_result(5), _evaluator_result(8)], [_improver_result()]
    )
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "COMPLETED"
    assert analysis.finished_at is not None
    assert analysis.improvement_skipped is False
    assert "[POR DEFINIR" in analysis.improved_requirement
    assert analysis.improvement["pending_items"] == ["tiempo máximo de respuesta"]
    evals = _evaluaciones(db, analysis)
    assert evals["original"].global_score == 50
    assert evals["improved"].global_score == 80
    assert evals["original"].raw_response == {"mock": "evaluator", "default": 5}
    # Lo reevaluado es el requisito mejorado con sus criterios de aceptación.
    assert evals["improved"].evaluated_text.startswith("El sistema deberá responder")
    assert len(evaluador.llamadas) == 2 and len(mejorador.llamadas) == 1


async def test_requisito_de_alta_calidad_no_se_modifica(db, monkeypatch):
    _, mejorador = _mockear(monkeypatch, [_evaluator_result(9)], [])
    analysis = _nuevo_analisis(db, "El sistema deberá ...")

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "COMPLETED"
    assert analysis.improvement_skipped is True
    assert analysis.improved_requirement is None
    assert mejorador.llamadas == []
    assert set(_evaluaciones(db, analysis)) == {"original"}


async def test_json_invalido_del_evaluador_deja_error_y_guarda_el_raw(db, monkeypatch):
    _mockear(
        monkeypatch,
        [EvaluatorParseError("JSON inválido", raw_response={"crudo": True}, model="m", latency_ms=5)],
        [],
    )
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    assert "JSON inválido" in analysis.error_message
    fila = _evaluaciones(db, analysis)["original"]
    assert fila.parse_ok is False
    assert fila.raw_response == {"crudo": True}
    assert fila.global_score is None


async def test_json_invalido_del_mejorador_deja_error_y_guarda_el_raw(db, monkeypatch):
    _mockear(
        monkeypatch,
        [_evaluator_result(5)],
        [ImproverParseError("JSON inválido", raw_response={"crudo": 1}, model="m", latency_ms=5)],
    )
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    assert analysis.improvement_raw == {"crudo": 1}
    assert analysis.improved_requirement is None


async def test_respuesta_vacia_del_evaluador_guarda_el_cuerpo_crudo(db, monkeypatch):
    cuerpo = {"choices": [{"finish_reason": "stop", "message": {"content": ""}}]}
    _mockear(monkeypatch, [NvidiaEmptyResponseError("vacío", cuerpo)], [])
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    fila = _evaluaciones(db, analysis)["original"]
    assert fila.parse_ok is False and fila.raw_response == cuerpo


async def test_respuesta_vacia_del_mejorador_guarda_el_cuerpo_crudo(db, monkeypatch):
    cuerpo = {"choices": [{"finish_reason": "stop", "message": {"content": ""}}]}
    _mockear(monkeypatch, [_evaluator_result(5)], [NvidiaEmptyResponseError("vacío", cuerpo)])
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    assert analysis.improvement_raw == cuerpo


_DEGENERADA = {"choices": [{"finish_reason": "stop", "message": {"content": None, "reasoning_content": "!!!!"}}]}


async def test_si_el_mejorador_principal_degenera_se_usa_el_de_respaldo(db, monkeypatch):
    # Caso real del punto 3: kimi-k3 devolvió reasoning "!!!!" y content
    # vacío en los 3 reintentos; nemotron-3-super sí produjo la mejora.
    _, mejorador = _mockear(
        monkeypatch,
        [_evaluator_result(5), _evaluator_result(8)],
        [NvidiaEmptyResponseError("vacío", _DEGENERADA), _improver_result()],
        respaldo="modelo/respaldo",
    )
    analysis = _nuevo_analisis(db)
    principal = analysis.improver_model

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "COMPLETED"
    assert [llamada[1]["model"] for llamada in mejorador.llamadas] == [principal, "modelo/respaldo"]
    assert analysis.improver_model == "modelo/respaldo"  # el que realmente mejoró
    respaldo = analysis.improvement["fallback"]
    assert respaldo["from_model"] == principal
    assert respaldo["raw_response"] == _DEGENERADA  # la respuesta cruda del fallo se conserva
    assert "vacío" in respaldo["reason"]


async def test_sin_modelo_de_respaldo_la_degeneracion_deja_error(db, monkeypatch):
    _mockear(monkeypatch, [_evaluator_result(5)], [NvidiaEmptyResponseError("vacío", _DEGENERADA)])
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    assert analysis.improvement_raw == _DEGENERADA


async def test_si_tambien_falla_el_respaldo_queda_error_con_ambos_motivos(db, monkeypatch):
    _mockear(
        monkeypatch,
        [_evaluator_result(5)],
        [
            NvidiaEmptyResponseError("vacío", _DEGENERADA),
            ImproverParseError("JSON inválido", raw_response={"r": 2}, model="m", latency_ms=1),
        ],
        respaldo="modelo/respaldo",
    )
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    assert "principal" in analysis.error_message and "respaldo" in analysis.error_message
    assert analysis.improvement["fallback"]["raw_response"] == _DEGENERADA
    assert analysis.improvement_raw == {"r": 2}


async def test_otros_errores_de_nvidia_no_usan_el_respaldo(db, monkeypatch):
    # Un 401 o un 404 no se arreglan cambiando de modelo: se reportan tal cual.
    _, mejorador = _mockear(
        monkeypatch, [_evaluator_result(5)], [NvidiaAuthError("401")], respaldo="modelo/respaldo"
    )
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    assert len(mejorador.llamadas) == 1


async def test_error_de_nvidia_deja_el_analisis_en_error(db, monkeypatch):
    _mockear(monkeypatch, [NvidiaAuthError("401")], [])
    analysis = _nuevo_analisis(db)

    await requirements_workflow.advance_analysis(db, analysis)

    assert analysis.status == "ERROR"
    assert "NVIDIA" in analysis.error_message


async def test_aclaracion_crea_un_analisis_hijo_con_las_respuestas(db, monkeypatch):
    _mockear(
        monkeypatch,
        [_evaluator_result(5), _evaluator_result(8), _evaluator_result(5), _evaluator_result(9)],
        [_improver_result(), _improver_result()],
    )
    padre = _nuevo_analisis(db, project_context="App bancaria")
    await requirements_workflow.advance_analysis(db, padre)

    hijo = requirements_workflow.start_clarification(db, padre, "Máximo 2 segundos.")
    db.creados.append(hijo)
    await requirements_workflow.advance_analysis(db, hijo)

    assert hijo.parent_id == padre.id
    assert hijo.original_requirement == padre.original_requirement
    assert hijo.project_context == "App bancaria"
    assert hijo.clarifications == "Máximo 2 segundos."
    assert hijo.status == "COMPLETED"
    assert padre.status == "COMPLETED"  # el análisis anterior queda intacto


async def test_el_proceso_en_segundo_plano_no_ocupa_conexiones_mientras_espera_a_la_ia(db, monkeypatch):
    """Bug real del punto 3: con 9 análisis simultáneos se agotó el pool de
    conexiones (5 + 10), porque cada análisis retenía una conexión durante
    los minutos que tarda la IA, y el servidor se bloqueó esperando una."""
    from backend.database import engine

    analysis_id = _nuevo_analisis(db).id
    db.commit()  # la sesión del test no debe retener conexión durante la medición
    base = engine.pool.checkedout()
    ocupadas_durante_la_ia: list[int] = []

    async def evaluador(*args, **kwargs):
        ocupadas_durante_la_ia.append(engine.pool.checkedout() - base)
        return _evaluator_result(5)

    async def mejorador(*args, **kwargs):
        ocupadas_durante_la_ia.append(engine.pool.checkedout() - base)
        return _improver_result()

    monkeypatch.setattr(requirements_workflow, "evaluate_requirement", evaluador)
    monkeypatch.setattr(requirements_workflow, "improve_requirement", mejorador)

    await requirements_workflow.run_analysis_background(analysis_id)

    assert ocupadas_durante_la_ia == [0, 0, 0]
    db.expire_all()
    assert db.get(RequirementAnalysis, analysis_id).status == "COMPLETED"


def test_al_arrancar_se_cierran_los_analisis_interrumpidos(db):
    """Visto en Render: tras un reinicio, un análisis quedó "Evaluando..."
    para siempre porque su BackgroundTask murió con el proceso."""
    colgado = _nuevo_analisis(db)
    colgado.status = "EVALUATING"
    terminado = _nuevo_analisis(db)
    terminado.status = "COMPLETED"
    db.commit()

    recuperados = requirements_workflow.recover_interrupted(db)

    db.refresh(colgado)
    db.refresh(terminado)
    assert recuperados >= 1
    assert colgado.status == "ERROR"
    assert colgado.error_message == requirements_workflow.MENSAJE_INTERRUMPIDO
    assert colgado.finished_at is not None
    assert terminado.status == "COMPLETED"  # los terminados no se tocan


def test_no_se_puede_aclarar_un_analisis_sin_terminar(db):
    analysis = _nuevo_analisis(db)
    with pytest.raises(InvalidTransitionError):
        requirements_workflow.start_clarification(db, analysis, "respuesta")


@pytest.mark.parametrize(
    ("origen", "destino"),
    [("CREATED", "COMPLETED"), ("IMPROVING", "COMPLETED"), ("COMPLETED", "EVALUATING"), ("ERROR", "EVALUATING")],
)
def test_transiciones_invalidas(db, origen, destino):
    analysis = _nuevo_analisis(db)
    analysis.status = origen
    with pytest.raises(InvalidTransitionError):
        requirements_workflow._set_status(db, analysis, destino)
