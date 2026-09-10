"""Tests puros de la máquina de estados (sin BD, sin LLM): validan que
TRANSICIONES_VALIDAS coincide con el diagrama de CLAUDE.md y que las
transiciones inválidas lanzan InvalidTransitionError.
"""

import pytest

from backend.services.workflow import (
    TRANSICIONES_VALIDAS,
    InvalidTransitionError,
    _ensure_transition_allowed,
)

# Transiciones válidas según CLAUDE.md, sección "Máquina de estados".
TRANSICIONES_ESPERADAS = [
    ("CREATED", "OPTIMIZING"),
    ("OPTIMIZING", "AUDITING"),
    ("AUDITING", "GATING"),
    ("GATING", "WAITING_HUMAN"),
    ("WAITING_HUMAN", "ITERATING"),
    ("ITERATING", "OPTIMIZING"),
    ("WAITING_HUMAN", "AUDITING"),
    ("WAITING_HUMAN", "APPROVED"),
    ("APPROVED", "EXECUTING"),
    ("EXECUTING", "COMPLETED"),
    ("WAITING_HUMAN", "REJECTED"),
]

# "cualquiera -> ERROR" = todo estado activo (no los terminales).
ESTADOS_QUE_PUEDEN_IR_A_ERROR = [
    "CREATED",
    "OPTIMIZING",
    "AUDITING",
    "GATING",
    "WAITING_HUMAN",
    "ITERATING",
    "APPROVED",
    "EXECUTING",
]

ESTADOS_TERMINALES = ["COMPLETED", "REJECTED", "ERROR"]


class TestTransicionesValidas:
    @pytest.mark.parametrize("origen,destino", TRANSICIONES_ESPERADAS)
    def test_transicion_del_diagrama_es_valida(self, origen, destino):
        _ensure_transition_allowed(origen, destino)  # no debe lanzar

    @pytest.mark.parametrize("origen", ESTADOS_QUE_PUEDEN_IR_A_ERROR)
    def test_cualquier_estado_activo_puede_ir_a_error(self, origen):
        _ensure_transition_allowed(origen, "ERROR")  # no debe lanzar

    @pytest.mark.parametrize("estado", ESTADOS_TERMINALES)
    def test_estados_terminales_no_tienen_transiciones_salientes(self, estado):
        assert TRANSICIONES_VALIDAS[estado] == set()

    @pytest.mark.parametrize("estado", ESTADOS_TERMINALES)
    def test_un_terminal_no_puede_ir_a_error_de_nuevo(self, estado):
        with pytest.raises(InvalidTransitionError):
            _ensure_transition_allowed(estado, "ERROR")


class TestTransicionesInvalidas:
    def test_ejecutar_sin_aprobar(self):
        """start_execution requiere APPROVED; WAITING_HUMAN -> EXECUTING debe fallar."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            _ensure_transition_allowed("WAITING_HUMAN", "EXECUTING")
        assert exc_info.value.current_status == "WAITING_HUMAN"
        assert exc_info.value.target_status == "EXECUTING"

    def test_aprobar_dos_veces(self):
        """Tras WAITING_HUMAN -> APPROVED, un segundo APPROVED -> APPROVED debe fallar."""
        _ensure_transition_allowed("WAITING_HUMAN", "APPROVED")  # la primera vez es válida
        with pytest.raises(InvalidTransitionError):
            _ensure_transition_allowed("APPROVED", "APPROVED")  # la segunda, no

    def test_iterar_desde_completed(self):
        """COMPLETED es terminal: no puede volver a ITERATING."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            _ensure_transition_allowed("COMPLETED", "ITERATING")
        assert exc_info.value.current_status == "COMPLETED"
        assert exc_info.value.target_status == "ITERATING"

    def test_saltarse_etapas_del_pipeline(self):
        """CREATED no puede ir directo a WAITING_HUMAN, se salta Optimizer/Auditor/Gates."""
        with pytest.raises(InvalidTransitionError):
            _ensure_transition_allowed("CREATED", "WAITING_HUMAN")

    def test_reject_desde_approved(self):
        """REJECTED solo es válido desde WAITING_HUMAN, no desde APPROVED."""
        with pytest.raises(InvalidTransitionError):
            _ensure_transition_allowed("APPROVED", "REJECTED")
