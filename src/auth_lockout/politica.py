# File: src/auth_lockout/politica.py
# Implements: ARCH-03, SPEC-AUT-03
# Spec: SPEC-AUT-03 v1.0.1 huella 78f967ade537 código f2d2d82c46b1

"""Parámetros de la política de bloqueo de cuentas."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyConfiguration:
    """Parámetros inmutables de la política de bloqueo.

    Los valores predeterminados son los de SPEC-AUT-03.

    Attributes:
        max_intentos_fallidos: intentos fallidos dentro de la ventana que bloquean.
        ventana_minutos: duración de la ventana deslizante en minutos.
        bloqueo_minutos: duración del bloqueo en minutos.

    Raises:
        ValueError: si algún valor no es un ``int`` mayor o igual a 1
            (``bool`` no cuenta como ``int``).
    """

    max_intentos_fallidos: int = 5
    ventana_minutos: int = 10
    bloqueo_minutos: int = 15

    def __post_init__(self) -> None:
        for nombre, valor in (
            ("max_intentos_fallidos", self.max_intentos_fallidos),
            ("ventana_minutos", self.ventana_minutos),
            ("bloqueo_minutos", self.bloqueo_minutos),
        ):
            if isinstance(valor, bool) or not isinstance(valor, int) or valor < 1:
                msg = f"{nombre} debe ser un int >= 1, recibido: {valor!r}"
                raise ValueError(msg)
