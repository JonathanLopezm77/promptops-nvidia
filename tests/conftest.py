"""Configuración común de los tests.

Las opciones que cambian el comportamiento del sistema y que cada
instalación define en su propio .env (modelo de respaldo, modo JSON por
modelo) se fijan aquí a un valor neutro, para que ningún test pase o falle
según la configuración local. El test que necesite otra cosa la fija
explícitamente con monkeypatch.
"""

import pytest

from backend.config import get_settings
from backend.services import requirements_workflow, workflow


@pytest.fixture(autouse=True)
def _configuracion_neutra(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "improver_fallback_model", None)
    monkeypatch.setattr(settings, "json_mode_models", frozenset())


@pytest.fixture(autouse=True)
def _sin_recuperacion_al_arrancar(monkeypatch):
    """Todo TestClient ejecuta el arranque de la app, que pasa a ERROR lo que
    esté procesándose en la BD REAL. Pasó de verdad: al correr los tests se
    cerró un run que el usuario estaba ejecutando en su servidor local. Los
    tests de la recuperación llaman a la función original importada antes
    de este parche y limitada a sus propios ids."""
    monkeypatch.setattr(requirements_workflow, "recover_interrupted", lambda db, ids=None: 0)
    monkeypatch.setattr(workflow, "recover_interrupted_runs", lambda db, ids=None: 0)
