# File: src/auth_lockout/repositorio.py
# Implements: ARCH-02, SPEC-AUT-03
# Spec: SPEC-AUT-03 v1.0.1 huella 78f967ade537 código 793887183348

"""Estado de cuenta y repositorio reemplazable para persistirlo."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol


@dataclass
class AccountState:
    """Estado de bloqueo de una cuenta.

    Attributes:
        failed_attempts: instantes UTC de los intentos fallidos dentro de la ventana.
        lock_until: fin del bloqueo vigente, o ``None`` si no hay bloqueo.
    """

    failed_attempts: list[datetime] = field(default_factory=list)
    lock_until: datetime | None = None


class AccountStateRepository(Protocol):
    """Interfaz de persistencia del estado de las cuentas."""

    def get_state(self, account_id: str) -> AccountState:
        """Devuelve el estado de la cuenta, o un estado vacío si no hay registro."""
        ...

    def save_state(self, account_id: str, state: AccountState) -> None:
        """Guarda el estado de la cuenta."""
        ...

    def delete_state(self, account_id: str) -> None:
        """Elimina el estado de la cuenta; no falla si no hay registro."""
        ...


class InMemoryAccountStateRepository:
    """Implementación en memoria de ``AccountStateRepository``.

    ``get_state`` devuelve una copia: modificar el resultado no altera lo guardado.
    """

    def __init__(self) -> None:
        self._states: dict[str, AccountState] = {}

    def get_state(self, account_id: str) -> AccountState:
        state = self._states.get(account_id)
        if state is None:
            return AccountState()
        return AccountState(
            failed_attempts=list(state.failed_attempts),
            lock_until=state.lock_until,
        )

    def save_state(self, account_id: str, state: AccountState) -> None:
        self._states[account_id] = AccountState(
            failed_attempts=list(state.failed_attempts),
            lock_until=state.lock_until,
        )

    def delete_state(self, account_id: str) -> None:
        self._states.pop(account_id, None)
