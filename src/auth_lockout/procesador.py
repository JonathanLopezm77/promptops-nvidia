# File: src/auth_lockout/procesador.py
# Implements: ARCH-01, SPEC-AUT-03
# Spec: SPEC-AUT-03 v1.0.1 huella 78f967ade537 código 8b6fb5126270

"""Procesador de intentos de inicio de sesión con política de bloqueo."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from auth_lockout.politica import PolicyConfiguration
from auth_lockout.repositorio import AccountState, AccountStateRepository


class ResultadoAutenticacion(StrEnum):
    """Resultado posible de un intento de inicio de sesión."""

    EXITOSO = "EXITOSO"
    CREDENCIALES_INVALIDAS = "CREDENCIALES_INVALIDAS"
    CUENTA_BLOQUEADA = "CUENTA_BLOQUEADA"


@dataclass(frozen=True)
class ResultadoIntento:
    """Resultado inmutable de procesar un intento de inicio de sesión.

    Attributes:
        resultado_autenticacion: resultado del intento.
        cuenta_bloqueada_hasta: fin del bloqueo vigente, o ``None``.
        contador_intentos_fallidos: intentos fallidos efectivos en la ventana
            (``max_intentos_fallidos`` mientras la cuenta está bloqueada).
        mensaje: mensaje informativo para el cliente, nunca vacío.
    """

    resultado_autenticacion: ResultadoAutenticacion
    cuenta_bloqueada_hasta: datetime | None
    contador_intentos_fallidos: int
    mensaje: str

    def como_dict(self) -> dict[str, str | int | None]:
        """Serializa el resultado con las claves de las salidas de SPEC-AUT-03.

        Returns:
            Diccionario con ``resultado_autenticacion`` como texto y
            ``cuenta_bloqueada_hasta`` en ISO 8601 "YYYY-MM-DDTHH:MM:SSZ" (o ``None``).
        """
        if self.cuenta_bloqueada_hasta is None:
            bloqueada_hasta: str | None = None
        else:
            bloqueada_hasta = self.cuenta_bloqueada_hasta.strftime("%Y-%m-%dT%H:%M:%SZ")
        return {
            "resultado_autenticacion": str(self.resultado_autenticacion),
            "cuenta_bloqueada_hasta": bloqueada_hasta,
            "contador_intentos_fallidos": self.contador_intentos_fallidos,
            "mensaje": self.mensaje,
        }


class LoginAttemptProcessor:
    """Aplica la política de bloqueo a cada intento de inicio de sesión.

    El estado de cada cuenta es independiente del de las demás (RB-7).
    """

    def __init__(
        self,
        repository: AccountStateRepository,
        policy: PolicyConfiguration | None = None,
    ) -> None:
        """Inicializa el procesador.

        Args:
            repository: repositorio del estado de las cuentas.
            policy: política de bloqueo; ``None`` usa los valores predeterminados
                de SPEC-AUT-03.
        """
        self._repository = repository
        self._policy = policy if policy is not None else PolicyConfiguration()

    def procesar_intento(
        self,
        identificador_cuenta: str,
        contrasena_correcta: bool,
        instante: datetime,
    ) -> ResultadoIntento:
        """Procesa un intento de inicio de sesión.

        Args:
            identificador_cuenta: identificador opaco no vacío de la cuenta.
            contrasena_correcta: ``True`` si la contraseña coincide con la almacenada.
            instante: instante UTC del intento, generado por el servidor.

        Returns:
            El resultado del intento según la política de bloqueo.

        Raises:
            TypeError: si ``identificador_cuenta`` no es ``str``,
                ``contrasena_correcta`` no es ``bool`` o ``instante`` no es ``datetime``.
            ValueError: si ``identificador_cuenta`` está vacío o solo tiene espacios,
                o si ``instante`` no tiene zona horaria o su desfase no es 0 (UTC).
        """
        self._validar_entradas(identificador_cuenta, contrasena_correcta, instante)

        policy = self._policy
        state = self._repository.get_state(identificador_cuenta)

        # Bloqueo vigente: se rechaza sin modificar el estado (RB-4, RB-8, D-08).
        if state.lock_until is not None and instante < state.lock_until:
            return ResultadoIntento(
                resultado_autenticacion=ResultadoAutenticacion.CUENTA_BLOQUEADA,
                cuenta_bloqueada_hasta=state.lock_until,
                contador_intentos_fallidos=policy.max_intentos_fallidos,
                mensaje="La cuenta está bloqueada temporalmente.",
            )

        # Bloqueo vencido: el estado vuelve a vacío (RB-6, D-03, D-05).
        if state.lock_until is not None:
            state = AccountState()

        if contrasena_correcta:
            # Éxito: no queda registro de la cuenta (RB-5, D-04).
            self._repository.delete_state(identificador_cuenta)
            return ResultadoIntento(
                resultado_autenticacion=ResultadoAutenticacion.EXITOSO,
                cuenta_bloqueada_hasta=None,
                contador_intentos_fallidos=0,
                mensaje="Inicio de sesión exitoso.",
            )

        # Ventana deslizante: un intento de exactamente V minutos todavía cuenta (D-02).
        limite_ventana = instante - timedelta(minutes=policy.ventana_minutos)
        state.failed_attempts = [t for t in state.failed_attempts if t >= limite_ventana]
        state.failed_attempts.append(instante)

        if len(state.failed_attempts) >= policy.max_intentos_fallidos:
            state.lock_until = instante + timedelta(minutes=policy.bloqueo_minutos)
            self._repository.save_state(identificador_cuenta, state)
            return ResultadoIntento(
                resultado_autenticacion=ResultadoAutenticacion.CUENTA_BLOQUEADA,
                cuenta_bloqueada_hasta=state.lock_until,
                contador_intentos_fallidos=policy.max_intentos_fallidos,
                mensaje="La cuenta ha sido bloqueada temporalmente.",
            )

        self._repository.save_state(identificador_cuenta, state)
        return ResultadoIntento(
            resultado_autenticacion=ResultadoAutenticacion.CREDENCIALES_INVALIDAS,
            cuenta_bloqueada_hasta=None,
            contador_intentos_fallidos=len(state.failed_attempts),
            mensaje="Credenciales inválidas.",
        )

    @staticmethod
    def _validar_entradas(
        identificador_cuenta: str,
        contrasena_correcta: bool,
        instante: datetime,
    ) -> None:
        if not isinstance(identificador_cuenta, str):
            msg = "identificador_cuenta debe ser str"
            raise TypeError(msg)
        if not identificador_cuenta.strip():
            msg = "identificador_cuenta no puede estar vacío"
            raise ValueError(msg)
        if not isinstance(contrasena_correcta, bool):
            msg = "contrasena_correcta debe ser bool"
            raise TypeError(msg)
        if not isinstance(instante, datetime):
            msg = "instante debe ser datetime"
            raise TypeError(msg)
        if instante.tzinfo is None or instante.utcoffset() != timedelta(0):
            msg = "instante debe tener zona horaria UTC (desfase 0)"
            raise ValueError(msg)
