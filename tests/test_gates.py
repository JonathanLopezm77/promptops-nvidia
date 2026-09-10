"""Tests del schema Pydantic del Auditor (AuditorResponse) frente al
mapeo oficial de las 21 propiedades a los 4 Quality Gates
(docs/auditor_system_prompt.md).
"""

import json

import pytest
from pydantic import ValidationError

from backend.schemas.auditor import GATE_PROPERTIES, AuditorResponse


def _propiedades_completas(gate: str) -> list[dict]:
    return [
        {"property_id": pid, "property_name": nombre, "score": 8, "observation": "ok"}
        for pid, nombre in GATE_PROPERTIES[gate].items()
    ]


def _gate_valido(gate: str, status: str = "PASS") -> dict:
    return {
        "gate": gate,
        "status": status,
        "justification": "justificación de prueba",
        "properties": _propiedades_completas(gate),
    }


def _respuesta_valida(overrides_por_gate: dict[str, str] | None = None) -> dict:
    overrides_por_gate = overrides_por_gate or {}
    gates = [
        _gate_valido(gate, overrides_por_gate.get(gate, "PASS")) for gate in GATE_PROPERTIES
    ]
    return {
        "gates": gates,
        "total_score": 85,
        "recommendations": ["ejemplo de recomendación"],
    }


class TestJSONCorrecto:
    def test_los_4_gates_en_pass_validan_ok(self):
        auditoria = AuditorResponse.model_validate(_respuesta_valida())
        assert len(auditoria.gates) == 4
        assert auditoria.gate_counts() == (4, 0, 0)
        assert auditoria.gates_score() == 1.0

    def test_model_validate_json_acepta_texto_json_valido(self):
        auditoria = AuditorResponse.model_validate_json(json.dumps(_respuesta_valida()))
        assert auditoria.total_score == 85


class TestGateNoAplica:
    def test_gate_2_no_aplica_no_penaliza_y_reduce_el_denominador(self):
        payload = _respuesta_valida({"gate_2_cognicion": "NO_APLICA"})
        auditoria = AuditorResponse.model_validate(payload)
        assert auditoria.gate_counts() == (3, 0, 1)
        # gates_score se calcula solo sobre gates aplicables (passed / (passed + failed))
        assert auditoria.gates_score() == 1.0

    def test_gate_no_aplica_conserva_sus_propiedades_evaluadas(self):
        payload = _respuesta_valida({"gate_2_cognicion": "NO_APLICA"})
        auditoria = AuditorResponse.model_validate(payload)
        gate_2 = next(g for g in auditoria.gates if g.gate == "gate_2_cognicion")
        assert {p.property_id for p in gate_2.properties} == set(
            GATE_PROPERTIES["gate_2_cognicion"]
        )


class TestSoloTresGates:
    def test_falta_un_gate_obligatorio_lanza_validation_error(self):
        payload = _respuesta_valida()
        payload["gates"] = payload["gates"][:3]  # elimina gate_4_eficiencia_foco
        with pytest.raises(ValidationError, match="faltan Gates obligatorios"):
            AuditorResponse.model_validate(payload)

    def test_gate_con_propiedades_incompletas_tambien_falla(self):
        # JSON válido, pero a un Gate le faltan propiedades de su mapeo (P13-P19)
        payload = _respuesta_valida()
        gate_3 = next(g for g in payload["gates"] if g["gate"] == "gate_3_seguridad_veracidad")
        gate_3["properties"] = gate_3["properties"][:5]
        with pytest.raises(ValidationError, match="no coinciden con el mapeo oficial"):
            AuditorResponse.model_validate(payload)


class TestJSONMalformado:
    def test_texto_no_json_lanza_validation_error(self):
        with pytest.raises(ValidationError):
            AuditorResponse.model_validate_json("esto no es json {{{")

    def test_json_valido_pero_con_tipos_incorrectos(self):
        payload = _respuesta_valida()
        payload["total_score"] = "muy bueno"  # debería ser int
        with pytest.raises(ValidationError):
            AuditorResponse.model_validate(payload)

    def test_score_de_propiedad_fuera_de_rango_falla(self):
        payload = _respuesta_valida()
        payload["gates"][0]["properties"][0]["score"] = 15  # fuera de 1-10
        with pytest.raises(ValidationError):
            AuditorResponse.model_validate(payload)

    def test_status_de_gate_fuera_del_enum_falla(self):
        payload = _respuesta_valida()
        payload["gates"][0]["status"] = "MAYBE"  # no es PASS/FAIL/NO_APLICA
        with pytest.raises(ValidationError):
            AuditorResponse.model_validate(payload)
