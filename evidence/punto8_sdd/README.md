# Punto 8 — Primera aproximación práctica a SDD (Componente 5)

Un requisito ya validado (REQ-AUT-03, bloqueo temporal de cuenta) se
transformó paso a paso en una especificación verificable que gobierna el
desarrollo:

```
Necesidad → Requirement → Acceptance Criteria → Specification → Architecture Contract → Implementation → Tests
NEC-AUT-01   REQ-AUT-03    AC-AUT-03-01..07      SPEC-AUT-03     ARCH-01..03             src/auth_lockout  tests/sdd
```

| Lo que pide el enunciado | Dónde está |
|---|---|
| Identificar el requisito fuente con un ID único | `specs/requirements.md` (REQ-AUT-03, revalidado: 90, alta calidad) |
| Criterios de aceptación verificables | `specs/acceptance_criteria.md` y `specs/acceptance/REQ-AUT-03.feature` (7 criterios Gherkin) |
| Especificación estructurada que sirva como contrato | `specs/specification.json` (+ JSON Schema en `specs/schemas/`), vista legible en `specs/specification.md` |
| Contrato de arquitectura | `specs/architecture_contract.md` (ARCH-01..03 y contrato normativo) |
| Implementación | `src/auth_lockout/` |
| Pruebas | `tests/sdd/` (30: conformidad con la especificación, suite generada, contrato) |
| Trazabilidad especificación ↔ diseño ↔ código ↔ prueba | `specs/traceability_matrix.md`, verificada por `python -m sdd.trazabilidad` y por pytest |
| Qué cambia con la especificación como fuente de verdad | [`DEMOSTRACION.md`](DEMOSTRACION.md) |

- Registro de cada Quality Gate y decisión: [`DECISIONES.md`](DECISIONES.md).
- Ejecuciones de los modelos (prompt, salida cruda, tokens, tiempos): `ejecuciones/`.

## Cómo se generó

Cada eslabón usó el **prompt aprobado** de su fase (punto 4) con el **modelo
elegido en el punto 7**, y leyó como entrada el artefacto **aprobado** del
eslabón anterior desde `/specs` (no una conversación):

| Eslabón | Fase y modelo | Quality Gate |
|---|---|---|
| Requirement | Motor de requisitos de la plataforma | Quality Score 90 ≥ 80, ningún criterio < 6 |
| Acceptance Criteria + Specification | 2 — Kimi K3 | Estructura, numeración, Gherkin, sin valores inventados; esquema Pydantic (toda regla con un criterio) |
| Architecture Contract | 3 — Nemotron 3 Super | Calificador de arquitectura del benchmark + revisión (8 correcciones) |
| Implementation | 4 — Kimi K3 | Compila, ruff sin avisos, solo biblioteca estándar, `Implements:` en cada módulo |
| Tests | 5 — Kimi K3 | 30/30, cobertura 100 %, 17/17 mutantes detectados, cada criterio con su prueba |

Resultado final: **cadena CONFORME** (0 problemas) y código **sellado**
contra SPEC-AUT-03 v1.0.1.

## Lo que corrigieron las puertas

Las puertas encontraron 14 problemas antes de que llegaran al código aprobado,
entre ellos: 2 huecos de la especificación del modelo (una regla sin criterio y
los intentos durante el bloqueo), la afirmación falsa de verificación del
contrato de arquitectura, **2 defectos del propio contrato aprobado**
(detectados por el lint de la implementación y corregidos en la fuente, no en el
código) y un hueco de la especificación que encontró el reporte de defectos de
la fase de pruebas (v1.0.1, D-10). Detalle en `DECISIONES.md`.

## Reproducir

```bash
python scripts/sdd_cadena.py requisito        # requiere el servidor local (uvicorn)
python scripts/sdd_cadena.py especificacion
python scripts/sdd_cadena.py arquitectura
python scripts/sdd_cadena.py implementacion
python scripts/sdd_cadena.py pruebas
python -m sdd.render                          # documentos desde la especificación
python -m sdd.trazabilidad                    # verificación y matriz
python -m sdd.mutacion tests/sdd/test_*.py    # prueba de mutación
python scripts/sdd_demo_cambio.py             # demostración 15 → 30 minutos
```

Entre pasos hay revisión humana (`DECISIONES.md`): los modelos proponen; el
artefacto aprobado es el que queda en `/specs`, `/src` y `/tests`.
