# /src

Código gobernado por especificación (Componente 5, SDD).

- `auth_lockout/`: bloqueo temporal de cuentas. Implementa SPEC-AUT-03
  (`specs/specification.json`) según el contrato `specs/architecture_contract.md`.
  Lo generó la fase de Implementación (Kimi K3) con el prompt aprobado; ver
  `evidence/punto8_sdd/DECISIONES.md`.

Cada módulo declara qué implementa (`# Implements: ARCH-xx, SPEC-AUT-03`) y
lleva el sello de su aprobación (`# Spec: ... huella ... código ...`). No se
modifica sin cambiar antes la especificación: ver `specs/README.md`.
