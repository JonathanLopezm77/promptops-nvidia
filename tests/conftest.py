"""Configuración común de los tests.

Las opciones que cambian el comportamiento del sistema y que cada
instalación define en su propio .env (modelo de respaldo, modo JSON por
modelo) se fijan aquí a un valor neutro, para que ningún test pase o falle
según la configuración local. El test que necesite otra cosa la fija
explícitamente con monkeypatch.
"""

import pytest

from backend.config import get_settings


@pytest.fixture(autouse=True)
def _configuracion_neutra(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "improver_fallback_model", None)
    monkeypatch.setattr(settings, "json_mode_models", frozenset())
