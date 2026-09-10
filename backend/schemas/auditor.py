"""Schema de la respuesta del Auditor (IA 2).

Refleja el mapeo oficial de docs/auditor_system_prompt.md: 21 propiedades
(P1-P21) repartidas en 4 Quality Gates. No inventa propiedades ni Gates:
`GateResult` y `AuditorResponse` validan que la respuesta del LLM cubra
exactamente lo que el mapeo exige, ni más ni menos.

Un JSON válido pero incompleto (falta un Gate, o a un Gate le faltan
propiedades del mapeo) falla la validación de Pydantic igual que un JSON
malformado: ambos casos se tratan como el mismo "error técnico de
parseo" descrito en SPEC.md §17 (un reintento automático; si persiste,
el run pasa a ERROR).
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

GateId = Literal[
    "gate_1_estructura_instruccion",
    "gate_2_cognicion",
    "gate_3_seguridad_veracidad",
    "gate_4_eficiencia_foco",
]

GateStatus = Literal["PASS", "FAIL", "NO_APLICA"]

# Mapeo oficial de docs/auditor_system_prompt.md (P1-P21 por Gate).
GATE_PROPERTIES: dict[GateId, dict[str, str]] = {
    "gate_1_estructura_instruccion": {
        "P1": "Cantidad de Tokens",
        "P2": "Manera / Tono",
        "P3": "Objetivos",
        "P4": "Demonstrations / Demos",
        "P5": "Lógica Estructural",
        "P6": "Lógica Contextual",
    },
    "gate_2_cognicion": {
        "P7": "Carga Intrínseca",
        "P8": "Carga Extránea",
        "P9": "Carga Germana",
        "P10": "Metacognición",
        "P11": "Herramientas Externas",
        "P12": "Recompensas / Incentivos",
    },
    "gate_3_seguridad_veracidad": {
        "P13": "Detección de Alucinaciones",
        "P14": "Balance Factibilidad vs. Creatividad",
        "P15": "Sesgo",
        "P16": "Seguridad",
        "P17": "Privacidad",
        "P18": "Confiabilidad",
        "P19": "Normas Sociales",
    },
    "gate_4_eficiencia_foco": {
        "P20": "Interacción",
        "P21": "Cortesía",
    },
}


class PropertyEvaluation(BaseModel):
    property_id: str
    property_name: str
    score: int = Field(ge=1, le=10)
    observation: str


class GateResult(BaseModel):
    gate: GateId
    status: GateStatus
    justification: str
    properties: list[PropertyEvaluation]

    @model_validator(mode="after")
    def _propiedades_coinciden_con_el_mapeo(self) -> "GateResult":
        esperadas = GATE_PROPERTIES[self.gate]
        recibidas = {p.property_id: p.property_name for p in self.properties}
        if recibidas.keys() != esperadas.keys():
            faltantes = sorted(esperadas.keys() - recibidas.keys())
            sobrantes = sorted(recibidas.keys() - esperadas.keys())
            detalle = []
            if faltantes:
                detalle.append(f"faltan {faltantes}")
            if sobrantes:
                detalle.append(f"sobran {sobrantes}")
            raise ValueError(
                f"{self.gate}: propiedades no coinciden con el mapeo oficial ({', '.join(detalle)})"
            )
        for prop_id, nombre_oficial in esperadas.items():
            if recibidas[prop_id] != nombre_oficial:
                raise ValueError(
                    f"{self.gate}: {prop_id} debe llamarse '{nombre_oficial}', "
                    f"llegó '{recibidas[prop_id]}'"
                )
        return self


class AuditorResponse(BaseModel):
    gates: list[GateResult]
    total_score: int = Field(ge=0, le=100)
    recommendations: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _exactamente_los_4_gates_oficiales(self) -> "AuditorResponse":
        recibidos = [g.gate for g in self.gates]
        if len(recibidos) != len(set(recibidos)):
            raise ValueError("gates duplicados en la respuesta del Auditor")
        esperados = set(GATE_PROPERTIES.keys())
        if set(recibidos) != esperados:
            faltantes = sorted(esperados - set(recibidos))
            raise ValueError(
                f"faltan Gates obligatorios en la respuesta del Auditor: {faltantes}"
            )
        return self

    def gate_counts(self) -> tuple[int, int, int]:
        """(gates_passed, gates_failed, gates_not_applicable), para la tabla audits."""
        passed = sum(1 for g in self.gates if g.status == "PASS")
        failed = sum(1 for g in self.gates if g.status == "FAIL")
        no_aplica = sum(1 for g in self.gates if g.status == "NO_APLICA")
        return passed, failed, no_aplica

    def gates_score(self) -> float | None:
        """passed / (passed + failed); None si no hay ningún Gate aplicable."""
        passed, failed, _ = self.gate_counts()
        if passed + failed == 0:
            return None
        return round(passed / (passed + failed), 4)
