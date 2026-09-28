# Requisito fuente — REQ-AUT-03

Primer eslabón de la cadena SDD (Componente 5):
**Necesidad → Requirement** → Acceptance Criteria → Specification →
Architecture Contract → Implementation → Tests.

## NEC-AUT-01 — Necesidad del stakeholder

> Como responsables de la tienda en línea queremos proteger las cuentas de los
> clientes contra intentos de adivinar su contraseña, sin dejar bloqueado de
> forma permanente a un cliente legítimo que se equivocó al escribirla.

Origen: política de seguridad de la tienda en línea. Es la necesidad de la que
salió el requisito del caso A del punto 3 (redactada por el equipo).

## REQ-AUT-03 — Requisito validado

Identificador único: **REQ-AUT-03** (dominio AUT = autenticación). Es el
requisito del caso A del punto 3, validado por el motor de requisitos de la
plataforma en 3 corridas: Requirements Quality Score 92, 100 y 100 (alta
calidad en las 3; `evidence/punto3_casos/`). En esta cadena se vuelve a
validar antes de usarlo (`evidence/punto8_sdd/ejecuciones/1_requisito.json`).

El texto exacto que se valida y que reciben las fases siguientes:

```requisito
REQ-AUT-03 (origen: política de seguridad de la tienda en línea). El sistema deberá bloquear durante 15 minutos la cuenta de un cliente registrado cuando se produzcan 5 intentos fallidos consecutivos de inicio de sesión dentro de un periodo de 10 minutos.
Criterios de aceptación:
1. Dado un cliente con 4 intentos fallidos consecutivos en los últimos 10 minutos, cuando falla el quinto intento, entonces la cuenta queda bloqueada y el sistema rechaza todo inicio de sesión de esa cuenta durante 15 minutos.
2. Dado una cuenta bloqueada hace 15 minutos o más, cuando el cliente ingresa su contraseña correcta, entonces el inicio de sesión es exitoso.
3. Dado un cliente con 4 intentos fallidos consecutivos, cuando inicia sesión correctamente, entonces el contador de intentos fallidos vuelve a 0.
```

Contexto del proyecto que recibe el motor de requisitos:

```contexto
Tienda en línea. Los clientes registrados inician sesión con correo y contraseña. La política de seguridad exige bloqueo temporal de cuentas ante intentos fallidos repetidos.
```

## Estado

| Versión | Fecha | Validación | Estado |
|---|---|---|---|
| v1 | 2026-09-27 | Revalidado en la cadena: puntaje 90, alta calidad (análisis `9d139a88`, `evidence/punto8_sdd/DECISIONES.md` §1) | **Aprobado**: origen de SPEC-AUT-03 |
