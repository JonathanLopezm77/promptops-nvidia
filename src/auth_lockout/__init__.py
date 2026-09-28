# File: src/auth_lockout/__init__.py
# Implements: ARCH-01, ARCH-02, ARCH-03, SPEC-AUT-03
# Spec: SPEC-AUT-03 v1.0.1 huella 78f967ade537 código 0b7e6bb8a870

"""API pública del paquete auth_lockout (SPEC-AUT-03)."""

from auth_lockout.politica import PolicyConfiguration
from auth_lockout.procesador import (
    LoginAttemptProcessor,
    ResultadoAutenticacion,
    ResultadoIntento,
)
from auth_lockout.repositorio import (
    AccountState,
    AccountStateRepository,
    InMemoryAccountStateRepository,
)

__all__ = [
    "AccountState",
    "AccountStateRepository",
    "InMemoryAccountStateRepository",
    "LoginAttemptProcessor",
    "PolicyConfiguration",
    "ResultadoAutenticacion",
    "ResultadoIntento",
]
