"""Esquema de la especificación SDD (specs/specification.json).

La especificación es la fuente de verdad del desarrollo: de ella se generan
specs/specification.md, specs/acceptance_criteria.md y el archivo .feature, y
contra ella se verifican el código y las pruebas (sdd/trazabilidad.py). Este
modelo Pydantic es su contrato; su JSON Schema se publica en
specs/schemas/specification.schema.json.
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ID_AC = re.compile(r"^AC-[A-Z]+-\d{2}-\d{2}$")


class _Estricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Parametros(_Estricto):
    """Valores de la política, tomados literalmente del requisito validado."""

    max_intentos_fallidos: int = Field(ge=1)
    ventana_minutos: int = Field(ge=1)
    bloqueo_minutos: int = Field(ge=1)


class Campo(_Estricto):
    nombre: str
    tipo: str
    validaciones: str = ""


class Regla(_Estricto):
    id: str = Field(pattern=r"^RB-\d+$")
    texto: str = Field(min_length=1)
    origen: str = Field(min_length=1, description="Fase de especificación (modelo) o revisión humana (decisión D-xx)")


class Gherkin(_Estricto):
    dado: str = Field(min_length=1)
    cuando: str = Field(min_length=1)
    entonces: str = Field(min_length=1)


class CriterioAceptacion(_Estricto):
    id: str
    origen: str = Field(min_length=1, description="De dónde sale: criterio del requisito o fase de especificación")
    gherkin: Gherkin
    reglas: list[str] = Field(min_length=1, description="RB-x que verifica")

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not _ID_AC.match(v):
            raise ValueError(f"id de criterio inválido: {v} (formato AC-XXX-NN-NN)")
        return v


class Decision(_Estricto):
    id: str = Field(pattern=r"^D-\d{2}$")
    tema: str
    supuesto_del_modelo: str | None = None
    decision: str = Field(min_length=1)
    fundamento: str = Field(min_length=1)


class Alerta(_Estricto):
    tipo: Literal["legal", "fuera_de_alcance"]
    descripcion: str
    tratamiento: str


class Especificacion(_Estricto):
    id: str = Field(pattern=r"^SPEC-[A-Z]+-\d{2}$")
    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    estado: Literal["borrador", "aprobada"]
    necesidad: str
    requisito_origen: str = Field(pattern=r"^REQ-[A-Z]+-\d{2}$")
    generada_por: dict[str, str]
    descripcion: str = Field(min_length=1)
    alcance: str
    parametros: Parametros
    entradas: list[Campo] = Field(min_length=1)
    salidas: list[Campo] = Field(min_length=1)
    reglas_negocio: list[Regla] = Field(min_length=1)
    criterios_aceptacion: list[CriterioAceptacion] = Field(min_length=2)
    decisiones: list[Decision]
    alertas: list[Alerta]

    @model_validator(mode="after")
    def _coherencia(self) -> "Especificacion":
        dominio_num = self.id.removeprefix("SPEC-")
        if self.requisito_origen != f"REQ-{dominio_num}":
            raise ValueError("el SPEC debe conservar la numeración de su REQ de origen")
        ids_rb = [r.id for r in self.reglas_negocio]
        ids_ac = [c.id for c in self.criterios_aceptacion]
        for nombre, ids in (("reglas", ids_rb), ("criterios", ids_ac), ("decisiones", [d.id for d in self.decisiones])):
            if len(ids) != len(set(ids)):
                raise ValueError(f"{nombre} con ids repetidos")
        for c in self.criterios_aceptacion:
            if not c.id.startswith(f"AC-{dominio_num}-"):
                raise ValueError(f"{c.id} no pertenece a {self.id}")
            if faltan := set(c.reglas) - set(ids_rb):
                raise ValueError(f"{c.id} referencia reglas inexistentes: {sorted(faltan)}")
        if sin_criterio := set(ids_rb) - {r for c in self.criterios_aceptacion for r in c.reglas}:
            raise ValueError(f"reglas sin ningún criterio de aceptación que las verifique: {sorted(sin_criterio)}")
        return self


def cargar(ruta: Path) -> Especificacion:
    return Especificacion.model_validate_json(ruta.read_text(encoding="utf-8"))


def huella(ruta: Path) -> str:
    """Huella de la especificación: cambia con cualquier cambio de contenido
    (no de formato). El código aprobado la declara en su cabecera."""
    canonico = json.dumps(json.loads(ruta.read_text(encoding="utf-8")), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()[:12]
