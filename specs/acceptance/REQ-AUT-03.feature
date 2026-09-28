# language: es
# Generado desde specs/specification.json (huella 78f967ade537). No editar a mano.
Característica: SPEC-AUT-03 — bloqueo temporal de cuenta (REQ-AUT-03)

  @AC-AUT-03-01 @RB-1 @RB-2 @RB-3
  Escenario: AC-AUT-03-01
    Dado un cliente registrado con 4 intentos fallidos consecutivos en los últimos 10 minutos
    Cuando falla el quinto intento de inicio de sesión
    Entonces la cuenta queda bloqueada durante 15 minutos y el sistema devuelve CUENTA_BLOQUEADA con la fecha-hora de fin de bloqueo en formato ISO 8601

  @AC-AUT-03-02 @RB-4
  Escenario: AC-AUT-03-02
    Dado una cuenta bloqueada
    Cuando el cliente intenta iniciar sesión con su contraseña correcta antes de que transcurran los 15 minutos de bloqueo
    Entonces el sistema rechaza el inicio de sesión y devuelve CUENTA_BLOQUEADA

  @AC-AUT-03-03 @RB-6
  Escenario: AC-AUT-03-03
    Dado una cuenta cuyo bloqueo se inició hace 15 minutos o más
    Cuando el cliente ingresa su contraseña correcta
    Entonces el inicio de sesión es exitoso y el contador de intentos fallidos queda en 0

  @AC-AUT-03-04 @RB-5
  Escenario: AC-AUT-03-04
    Dado un cliente con 4 intentos fallidos consecutivos dentro de la ventana de 10 minutos
    Cuando inicia sesión correctamente
    Entonces el contador de intentos fallidos vuelve a 0 y la cuenta no se bloquea

  @AC-AUT-03-05 @RB-2
  Escenario: AC-AUT-03-05
    Dado un cliente con 4 intentos fallidos donde el más antiguo ocurrió hace más de 10 minutos
    Cuando falla un nuevo intento
    Entonces el intento antiguo se descarta de la ventana, el contador efectivo es menor a 5 y la cuenta no se bloquea

  @AC-AUT-03-06 @RB-7
  Escenario: AC-AUT-03-06
    Dado la cuenta A bloqueada por 5 intentos fallidos consecutivos
    Cuando el cliente de la cuenta B inicia sesión con su contraseña correcta
    Entonces el inicio de sesión de la cuenta B es exitoso y los intentos de la cuenta A no afectan a la cuenta B

  @AC-AUT-03-07 @RB-4 @RB-8
  Escenario: AC-AUT-03-07
    Dado una cuenta bloqueada hace 5 minutos
    Cuando el cliente falla otro intento de inicio de sesión
    Entonces el sistema devuelve CUENTA_BLOQUEADA, la fecha-hora de fin de bloqueo no cambia y, al expirar el bloqueo, el contador de intentos fallidos está en 0
