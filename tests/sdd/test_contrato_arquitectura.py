"""Pruebas del contrato de arquitectura (specs/architecture_contract.md §2) que
no corresponden a un criterio de aceptación. Las agregó la revisión del
Quality Gate de pruebas: con las otras dos suites sobrevivían 2 mutantes de la
validación de PolicyConfiguration y una rama de como_dict() no se ejecutaba.
"""

from datetime import UTC, datetime

import pytest

from auth_lockout import (
    InMemoryAccountStateRepository,
    LoginAttemptProcessor,
    PolicyConfiguration,
    ResultadoAutenticacion,
)


@pytest.mark.parametrize("campo", ["max_intentos_fallidos", "ventana_minutos", "bloqueo_minutos"])
def test_arch03_el_minimo_valido_es_1(campo):
    """ARCH-03: 'int >= 1' — 1 se acepta, 0 se rechaza."""
    assert getattr(PolicyConfiguration(**{campo: 1}), campo) == 1
    with pytest.raises(ValueError):
        PolicyConfiguration(**{campo: 0})


def test_arch01_como_dict_sin_bloqueo():
    """ARCH-01: como_dict() con cuenta_bloqueada_hasta None."""
    r = LoginAttemptProcessor(InMemoryAccountStateRepository()).procesar_intento(
        "a@x.co", True, datetime(2026, 9, 27, tzinfo=UTC))
    assert r.como_dict() == {"resultado_autenticacion": str(ResultadoAutenticacion.EXITOSO),
                             "cuenta_bloqueada_hasta": None, "contador_intentos_fallidos": 0, "mensaje": r.mensaje}


def test_arch02_get_state_devuelve_una_copia():
    """ARCH-02: modificar el estado leído no altera lo guardado."""
    repo = InMemoryAccountStateRepository()
    proc = LoginAttemptProcessor(repo)
    proc.procesar_intento("a@x.co", False, datetime(2026, 9, 27, tzinfo=UTC))
    repo.get_state("a@x.co").failed_attempts.clear()
    assert len(repo.get_state("a@x.co").failed_attempts) == 1
