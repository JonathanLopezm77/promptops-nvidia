# Criterios de aceptación — REQ-AUT-03 / SPEC-AUT-03

> Generado por `python -m sdd.render` desde `specs/specification.json` (huella `78f967ade537`). No editar a mano: se cambia la especificación y se regenera.

Formato Gherkin ejecutable: `specs/acceptance/REQ-AUT-03.feature`. Cada criterio tiene al menos una prueba que lo declara (`specs/traceability_matrix.md`).

## AC-AUT-03-01

- **Origen:** REQ-AUT-03, criterio 1
- **Verifica:** RB-1, RB-2, RB-3

```gherkin
Dado un cliente registrado con 4 intentos fallidos consecutivos en los últimos 10 minutos
Cuando falla el quinto intento de inicio de sesión
Entonces la cuenta queda bloqueada durante 15 minutos y el sistema devuelve CUENTA_BLOQUEADA con la fecha-hora de fin de bloqueo en formato ISO 8601
```

## AC-AUT-03-02

- **Origen:** fase de especificación (Kimi K3): explicita el 'rechaza todo inicio de sesión' del criterio 1
- **Verifica:** RB-4

```gherkin
Dado una cuenta bloqueada
Cuando el cliente intenta iniciar sesión con su contraseña correcta antes de que transcurran los 15 minutos de bloqueo
Entonces el sistema rechaza el inicio de sesión y devuelve CUENTA_BLOQUEADA
```

## AC-AUT-03-03

- **Origen:** REQ-AUT-03, criterio 2
- **Verifica:** RB-6

```gherkin
Dado una cuenta cuyo bloqueo se inició hace 15 minutos o más
Cuando el cliente ingresa su contraseña correcta
Entonces el inicio de sesión es exitoso y el contador de intentos fallidos queda en 0
```

## AC-AUT-03-04

- **Origen:** REQ-AUT-03, criterio 3
- **Verifica:** RB-5

```gherkin
Dado un cliente con 4 intentos fallidos consecutivos dentro de la ventana de 10 minutos
Cuando inicia sesión correctamente
Entonces el contador de intentos fallidos vuelve a 0 y la cuenta no se bloquea
```

## AC-AUT-03-05

- **Origen:** fase de especificación (Kimi K3): caso borde de la ventana
- **Verifica:** RB-2

```gherkin
Dado un cliente con 4 intentos fallidos donde el más antiguo ocurrió hace más de 10 minutos
Cuando falla un nuevo intento
Entonces el intento antiguo se descarta de la ventana, el contador efectivo es menor a 5 y la cuenta no se bloquea
```

## AC-AUT-03-06

- **Origen:** revisión humana: RB-7 no tenía ningún criterio que la verificara
- **Verifica:** RB-7

```gherkin
Dado la cuenta A bloqueada por 5 intentos fallidos consecutivos
Cuando el cliente de la cuenta B inicia sesión con su contraseña correcta
Entonces el inicio de sesión de la cuenta B es exitoso y los intentos de la cuenta A no afectan a la cuenta B
```

## AC-AUT-03-07

- **Origen:** revisión humana (decisión D-08): caso borde no cubierto por el modelo
- **Verifica:** RB-4, RB-8

```gherkin
Dado una cuenta bloqueada hace 5 minutos
Cuando el cliente falla otro intento de inicio de sesión
Entonces el sistema devuelve CUENTA_BLOQUEADA, la fecha-hora de fin de bloqueo no cambia y, al expirar el bloqueo, el contador de intentos fallidos está en 0
```
