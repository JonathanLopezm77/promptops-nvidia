"""Schema de la respuesta del Prompt Optimizer (IA 1).

Contrato mínimo exigido por docs/SPEC.md sección 5.
"""

from pydantic import BaseModel, Field


class OptimizerResponse(BaseModel):
    original_prompt: str
    analysis: str
    improved_prompt: str
    changes: list[str] = Field(default_factory=list)
    reasoning_summary: str
