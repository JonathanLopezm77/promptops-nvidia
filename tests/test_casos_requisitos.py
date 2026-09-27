"""Tests de las verificaciones de scripts/casos_requisitos.py: si una
verificación estuviera mal escrita, la evidencia del punto 3 diría que el
sistema cumple (o no) sin que sea cierto."""

import copy

from backend.schemas.requirements import REQUIREMENT_CRITERIA
from scripts.casos_requisitos import verificar


def _evaluacion(stage, score=5, consistencia=None, alta=False, **extra):
    criterios = [
        {"criterion": c, "score": score, "finding": "f", "recommendation": ""} for c in REQUIREMENT_CRITERIA
    ]
    if consistencia is not None:
        next(c for c in criterios if c["criterion"] == "consistencia")["score"] = consistencia
    return {
        "stage": stage, "parse_ok": True, "global_score": score * 10, "is_high_quality": alta,
        "criteria": criterios, "ambiguous_terms": [], "clarification_questions": [],
        "missing_information": [], "summary": "s", **extra,
    }


def _analisis(**extra):
    base = {
        "id": "x", "status": "COMPLETED", "error_message": None, "input_mode": "text",
        "improvement_skipped": False, "improved_requirement": None, "improvement": None,
        "recommended_version": None, "score_delta": None, "stt_metadata": None, "tts_log": [],
        "evaluations": [],
    }
    base.update(extra)
    return base


def _fallidas(vs):
    return {v.codigo for v in vs if v.requerida and not v.ok}


def test_caso_a_cumple_solo_si_no_se_modifica():
    bueno = _analisis(improvement_skipped=True, evaluations=[_evaluacion("original", 9, alta=True)])
    assert _fallidas(verificar("A", bueno)) == set()

    modificado = copy.deepcopy(bueno)
    modificado.update(improvement_skipped=False, improved_requirement="otro texto")
    assert _fallidas(verificar("A", modificado)) == {"A2"}


def test_caso_b_exige_ambiguedad_preguntas_mejora_y_aclaracion():
    padre = _analisis(
        improved_requirement="REQ-1 ...", recommended_version="improved", score_delta=10,
        improvement={"pending_items": ["a", "b"], "unsupported_values": []},
        evaluations=[
            _evaluacion("original", 4, ambiguous_terms=[{"term": "rápida", "reason": "r"}],
                        clarification_questions=["¿cuánto?"]),
            _evaluacion("improved", 5),
        ],
    )
    hijo = _analisis(
        improved_requirement="REQ-1 ... 2 segundos", recommended_version="improved", score_delta=30,
        improvement={"pending_items": [], "unsupported_values": []},
        evaluations=[_evaluacion("original", 4), _evaluacion("improved", 8)],
    )
    assert _fallidas(verificar("B", padre, hijo)) == set()

    sin_vagos = copy.deepcopy(padre)
    sin_vagos["evaluations"][0]["ambiguous_terms"] = [{"term": "usuarios", "reason": "r"}]
    assert "B1" in _fallidas(verificar("B", sin_vagos, hijo))

    inventa = copy.deepcopy(padre)
    inventa["improvement"]["unsupported_values"] = ["30"]
    assert "B4" in _fallidas(verificar("B", inventa, hijo))

    hijo_peor = copy.deepcopy(hijo)
    hijo_peor["evaluations"][1]["global_score"] = 30  # por debajo del original del padre (40)
    assert "B5" in _fallidas(verificar("B", padre, hijo_peor))


def test_caso_c_exige_contradiccion_detectada_y_pendiente():
    bueno = _analisis(
        improved_requirement="REQ-1: [POR DEFINIR: resolver contradicción entre diario y manual]",
        recommended_version="improved",
        improvement={"pending_items": ["Resolver si es automático diario o a solicitud del gerente"],
                     "unsupported_values": []},
        evaluations=[_evaluacion("original", 3, consistencia=2, missing_information=["datos"],
                                 clarification_questions=["¿cuál?"])],
    )
    assert _fallidas(verificar("C", bueno)) == set()

    # También vale si solo el pendiente plantea la elección, sin la palabra "contradicción".
    sin_palabra = copy.deepcopy(bueno)
    sin_palabra["improved_requirement"] = "REQ-1: generar el reporte [POR DEFINIR: disparador]"
    assert _fallidas(verificar("C", sin_palabra)) == set()

    resuelve = copy.deepcopy(sin_palabra)
    resuelve["improvement"]["pending_items"] = ["Formato del reporte"]
    assert "C4" in _fallidas(verificar("C", resuelve))

    no_detecta = copy.deepcopy(bueno)
    no_detecta["evaluations"][0] = _evaluacion("original", 3, consistencia=7, missing_information=["d"],
                                               clarification_questions=["¿?"])
    assert "C1" in _fallidas(verificar("C", no_detecta))


def test_caso_d_exige_metadata_de_voz_y_lectura_registrada():
    stt = {"engine": "Web Speech API", "provider": "Google", "processing": "remote", "language": "es-CO"}
    bueno = _analisis(
        input_mode="voice", stt_metadata=stt, improved_requirement="REQ-1 ...",
        tts_log=[{"voice": "Microsoft Sabina", "processing": "local", "language": "es-MX", "played_at": "t"}],
        evaluations=[_evaluacion("original", 5)],
    )
    assert _fallidas(verificar("D", bueno)) == set()

    sin_lectura = copy.deepcopy(bueno)
    sin_lectura["tts_log"] = []
    assert _fallidas(verificar("D", sin_lectura)) == {"D3"}


def test_un_analisis_con_error_nunca_cumple():
    fallido = _analisis(status="ERROR", error_message="JSON inválido")
    assert _fallidas(verificar("A", fallido)) == {"G1", "G2"}
