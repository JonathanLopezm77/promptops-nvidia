"""Configuración centralizada de la aplicación.

Este es el ÚNICO módulo del proyecto que debe leer variables de entorno
(os.environ). Ningún otro archivo debe mencionar un nombre de modelo
literal: todos deben obtenerlo a través de `get_settings()`.
"""

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

VARIABLES_OBLIGATORIAS = (
    "DATABASE_URL",
    "NVIDIA_API_KEY",
    "OPTIMIZER_MODEL",
    "AUDITOR_MODEL",
    "EXECUTOR_MODEL",
)


class Settings(BaseModel):
    """Configuración validada de la aplicación.

    Nunca expone `nvidia_api_key` en `__repr__`/`__str__` ni debe
    devolverse tal cual por la API: solo se usa internamente para
    autenticar contra NVIDIA.
    """

    database_url: str
    nvidia_api_key: str
    nvidia_base_url: str
    optimizer_model: str
    auditor_model: str
    executor_model: str
    llm_timeout_seconds: int
    llm_max_retries: int
    # Modelos a los que las IAs de requisitos piden
    # `response_format: {"type": "json_object"}` ("*" = todos). Es por
    # modelo porque depende de cada uno (medido en el punto 3): a
    # nemotron-3-super le evita JSON mal formado, pero a kimi-k3 le provoca
    # respuestas vacías.
    json_mode_models: frozenset[str] = frozenset()
    # Modelo que el Mejorador de requisitos usa si OPTIMIZER_MODEL no da una
    # respuesta usable (vacía o JSON inválido tras reintentar). Opcional.
    improver_fallback_model: str | None = None

    def json_mode_for(self, model: str) -> bool:
        return "*" in self.json_mode_models or model in self.json_mode_models

    def __repr__(self) -> str:
        return (
            "Settings("
            f"database_url='***', "
            f"nvidia_base_url={self.nvidia_base_url!r}, "
            f"optimizer_model={self.optimizer_model!r}, "
            f"auditor_model={self.auditor_model!r}, "
            f"executor_model={self.executor_model!r}, "
            f"llm_timeout_seconds={self.llm_timeout_seconds}, "
            f"llm_max_retries={self.llm_max_retries}, "
            f"json_mode_models={sorted(self.json_mode_models)}, "
            f"improver_fallback_model={self.improver_fallback_model!r})"
        )

    __str__ = __repr__


@lru_cache
def get_settings() -> Settings:
    """Carga y valida la configuración desde `.env` (una sola vez, cacheada)."""
    faltantes = [var for var in VARIABLES_OBLIGATORIAS if not os.environ.get(var)]
    if faltantes:
        raise RuntimeError(
            "Faltan variables de entorno obligatorias en .env: " + ", ".join(faltantes)
        )

    return Settings(
        database_url=os.environ["DATABASE_URL"],
        nvidia_api_key=os.environ["NVIDIA_API_KEY"],
        nvidia_base_url=os.environ.get(
            "NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"
        ),
        optimizer_model=os.environ["OPTIMIZER_MODEL"],
        auditor_model=os.environ["AUDITOR_MODEL"],
        executor_model=os.environ["EXECUTOR_MODEL"],
        llm_timeout_seconds=int(os.environ.get("LLM_TIMEOUT_SECONDS", "60")),
        llm_max_retries=int(os.environ.get("LLM_MAX_RETRIES", "2")),
        json_mode_models=_modelos_json(),
        improver_fallback_model=os.environ.get("IMPROVER_FALLBACK_MODEL", "").strip() or None,
    )


def _modelos_json() -> frozenset[str]:
    """LLM_JSON_MODE_MODELS=modelo1,modelo2 (o "*"). Se mantiene
    LLM_JSON_MODE=true como equivalente de "*" (pruebas con Ollama)."""
    modelos = {m.strip() for m in os.environ.get("LLM_JSON_MODE_MODELS", "").split(",") if m.strip()}
    if os.environ.get("LLM_JSON_MODE", "").strip().lower() in ("1", "true", "si", "sí"):
        modelos.add("*")
    return frozenset(modelos)
