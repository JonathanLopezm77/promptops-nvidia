"""Schemas de la capa de Ingeniería de Requisitos (Parcial 1, Componente 1).

`REQUIREMENT_CRITERIA` es la lista cerrada de los 10 criterios mínimos del
enunciado (sección 4.2, basada en ISO/IEC/IEEE 29148). El Evaluador debe
devolver exactamente esos 10, ni más ni menos, igual que el Auditor con
sus 21 propiedades.

El puntaje global NO lo decide el LLM: se calcula aquí a partir de los
10 puntajes individuales, con la fórmula acordada por el equipo:

- global_score = promedio de los 10 criterios (1-10) x 10, redondeado (0-100)
- alta calidad  = global_score >= 80 y ningún criterio por debajo de 6
"""

import re
import unicodedata

from pydantic import BaseModel, Field, field_validator, model_validator

_NUMERO = re.compile(r"\d+(?:[.,]\d+)?")
_POR_DEFINIR = re.compile(r"\[POR DEFINIR[^\]]*\]", re.IGNORECASE)
# Numeración de sub-requisitos (REQ-1, REQ-2.1) que exige el Mejorador.
_NUMERACION_REQ = re.compile(r"\bREQ-[\d.]+", re.IGNORECASE)

# Clave -> (nombre visible, pregunta de control del enunciado).
REQUIREMENT_CRITERIA: dict[str, tuple[str, str]] = {
    "claridad": (
        "Claridad",
        "El requisito se comprende sin interpretaciones contradictorias.",
    ),
    "especificidad": (
        "Especificidad",
        "Expresa comportamiento, condición o resultado con suficiente precisión.",
    ),
    "atomicidad": (
        "Atomicidad",
        "Evita mezclar varios requisitos independientes en una sola oración.",
    ),
    "completitud": (
        "Completitud",
        "Incluye la información necesaria para comprender y desarrollar el comportamiento solicitado.",
    ),
    "consistencia": (
        "Consistencia",
        "No contradice otros requisitos o reglas conocidas.",
    ),
    "factibilidad": (
        "Factibilidad",
        "Puede implementarse razonablemente dadas las restricciones declaradas.",
    ),
    "verificabilidad": (
        "Verificabilidad",
        "Permite comprobar objetivamente si el requisito se cumple.",
    ),
    "trazabilidad": (
        "Trazabilidad",
        "Puede identificarse y relacionarse con necesidad, diseño, implementación y prueba.",
    ),
    "ausencia_ambiguedad": (
        "Ausencia de ambigüedad",
        "Detecta términos subjetivos o vagos como rápido, fácil, adecuado, intuitivo, suficiente, etc.",
    ),
    "criterios_aceptacion": (
        "Criterios de aceptación",
        "Permite determinar de forma verificable cuándo el requisito está satisfecho.",
    ),
}

HIGH_QUALITY_MIN_GLOBAL = 80
HIGH_QUALITY_MIN_CRITERION = 6


def _normalizar(texto: str) -> str:
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c)
    )
    clave = re.sub(r"[^a-z0-9]+", "_", sin_tildes.lower()).strip("_")
    return clave.replace("_de_", "_")


# Variantes aceptadas -> clave oficial. Solo cambia la escritura (tildes,
# mayúsculas, espacios, "de"), nunca el criterio: uno inventado sigue fallando.
_ALIAS_CRITERIOS: dict[str, str] = {}
for _clave, (_nombre, _) in REQUIREMENT_CRITERIA.items():
    _ALIAS_CRITERIOS[_normalizar(_clave)] = _clave
    _ALIAS_CRITERIOS[_normalizar(_nombre)] = _clave


class CriterionEvaluation(BaseModel):
    criterion: str

    @field_validator("criterion", mode="before")
    @classmethod
    def _clave_oficial(cls, valor: object) -> object:
        """Visto con qwen2.5-coder:7b: devolvió "criterios_aceptación" (con
        tilde) en vez de "criterios_aceptacion"."""
        if isinstance(valor, str):
            return _ALIAS_CRITERIOS.get(_normalizar(valor), valor)
        return valor

    score: int = Field(ge=1, le=10)
    # Puede venir vacío cuando el criterio se cumple y no hay nada que
    # señalar (verificado con qwen2.5-coder:7b en una corrida real).
    finding: str
    recommendation: str


class AmbiguousTerm(BaseModel):
    term: str = Field(min_length=1)
    reason: str


class RequirementEvaluationResponse(BaseModel):
    """Lo que devuelve el Evaluador. Nunca incluye una versión reescrita
    del requisito: evaluar y mejorar son roles separados."""

    criteria: list[CriterionEvaluation]
    ambiguous_terms: list[AmbiguousTerm] = Field(default_factory=list)
    is_compound: bool
    missing_information: list[str] = Field(default_factory=list)
    clarification_questions: list[str] = Field(default_factory=list)
    summary: str = Field(min_length=1)

    @model_validator(mode="after")
    def _exactamente_los_10_criterios(self) -> "RequirementEvaluationResponse":
        recibidos = [c.criterion for c in self.criteria]
        if len(recibidos) != len(set(recibidos)):
            raise ValueError("criterios duplicados en la respuesta del Evaluador")
        esperados = set(REQUIREMENT_CRITERIA)
        if set(recibidos) != esperados:
            faltantes = sorted(esperados - set(recibidos))
            sobrantes = sorted(set(recibidos) - esperados)
            detalle = []
            if faltantes:
                detalle.append(f"faltan {faltantes}")
            if sobrantes:
                detalle.append(f"sobran {sobrantes}")
            raise ValueError(
                "los criterios no coinciden con los 10 obligatorios (" + ", ".join(detalle) + ")"
            )
        return self

    def global_score(self) -> int:
        promedio = sum(c.score for c in self.criteria) / len(self.criteria)
        return round(promedio * 10)

    def is_high_quality(self) -> bool:
        return self.global_score() >= HIGH_QUALITY_MIN_GLOBAL and all(
            c.score >= HIGH_QUALITY_MIN_CRITERION for c in self.criteria
        )


class RequirementImprovementResponse(BaseModel):
    """Lo que devuelve el Mejorador. `pending_items` lista lo que sigue
    faltando y quedó marcado como [POR DEFINIR: ...] en el texto, en vez
    de inventarlo."""

    improved_requirement: str = Field(min_length=1)
    acceptance_criteria: list[str] = Field(min_length=1)
    changes: list[str] = Field(default_factory=list)
    pending_items: list[str] = Field(default_factory=list)
    intent_preservation: str = Field(min_length=1)

    @field_validator("improved_requirement", mode="before")
    @classmethod
    def _unir_sub_requisitos(cls, valor: object) -> object:
        """Al separar un requisito compuesto (REQ-1, REQ-2, ...) algunos
        modelos devuelven una lista de strings en vez de un único texto
        (visto con qwen2.5-coder:7b). Se unen línea a línea; cualquier otra
        forma sigue fallando la validación."""
        if isinstance(valor, list) and all(isinstance(v, str) for v in valor):
            return "\n".join(valor)
        return valor

    def unsupported_values(self, *fuentes: str | None) -> list[str]:
        """Números del requisito mejorado (y sus criterios de aceptación)
        que no aparecen en ninguna fuente (requisito original, contexto,
        aclaraciones) ni dentro de un [POR DEFINIR: ...]. Son candidatos a
        datos inventados: el enunciado exige no inventar, y un valor
        numérico sin respaldo es el caso más común y más fácil de detectar
        de forma determinista."""
        texto = "\n".join([self.improved_requirement, *self.acceptance_criteria])
        texto = _POR_DEFINIR.sub(" ", texto)
        texto = _NUMERACION_REQ.sub(" ", texto)
        respaldados = set(_NUMERO.findall(" ".join(f for f in fuentes if f)))
        vistos: list[str] = []
        for valor in _NUMERO.findall(texto):
            if valor not in respaldados and valor not in vistos:
                vistos.append(valor)
        return vistos

    def text_for_evaluation(self) -> str:
        """Texto que se reevalúa: el requisito junto con sus criterios de
        aceptación, porque el criterio 'Criterios de aceptación' los exige."""
        criterios = "\n".join(f"- {c}" for c in self.acceptance_criteria)
        return f"{self.improved_requirement}\n\nCriterios de aceptación:\n{criterios}"
