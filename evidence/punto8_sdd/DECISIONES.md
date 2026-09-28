# Registro de Quality Gates y decisiones de la cadena SDD

Cada eslabón pasó por un Quality Gate (automático) y una revisión humana antes
de que su artefacto se convirtiera en la entrada del siguiente. Aquí queda qué
entró, qué se encontró, qué se corrigió y qué se aprobó.

**Revisor:** Claude (asistente de código), por instrucción del usuario
("realiza el punto 8 todo completo"), el 2026-09-27/28. **Pendiente de
confirmación del equipo**: cualquier integrante puede rechazar una decisión, y
basta con cambiar la especificación para que la cadena lo refleje (así
funciona SDD).

Ejecuciones completas (prompt enviado, salida cruda, tokens, tiempos) en
`ejecuciones/`; las descartadas, en `ejecuciones/descartadas/`. Horas en UTC.

| Paso | Fase SDLC | Modelo (selección del punto 7) | Ejecutado | Tokens entrada / salida | Tiempo |
|---|---|---|---|---|---|
| 1_requisito | Requisitos (motor de la plataforma) | Evaluador: nemotron-3-super | 2026-09-27 23:36 | — | — |
| 2_especificacion | 2 Especificación | Kimi K3 | 2026-09-27 23:38 | 2363 / 1762 | 81 s |
| 3_arquitectura | 3 Arquitectura | Nemotron 3 Super | 2026-09-27 23:41 | 3976 / 3857 | 27 s |
| 4_implementacion | 4 Implementación | Kimi K3 | 2026-09-27 23:47 | 8037 / 2851 | 136 s |
| 5_pruebas | 5 Testing | Kimi K3 | 2026-09-28 01:53 | 8630 / 5453 | 234 s |

Todos con los prompts **aprobados** del punto 4 (`prompts/aprobados/`), sin
modificarlos, y los parámetros del benchmark (`temperature 0.2`, `top_p 0.95`,
`max_tokens 8192`).

## §1. Necesidad → Requirement (REQ-AUT-03)

- **Entrada:** el texto de `specs/requirements.md`, idéntico carácter por
  carácter al caso A del punto 3 (comprobado por script).
- **Gate:** Requirements Quality Score ≥ 80 y ningún criterio < 6.
- **Resultado:** análisis `9d139a88-7588-4d0d-be8f-df75ca6f1b2e`: **90**, alta
  calidad, criterios entre 8 y 10; el motor no lo modificó. Hizo una pregunta
  de alcance (¿el bloqueo aplica solo al inicio de sesión?).
- **Decisión:** aprobado sin cambios. La pregunta la responde el propio texto
  ("rechaza todo inicio de sesión"); se registra como D-09 en la especificación.

## §2. Requirement → Acceptance Criteria + Specification (SPEC-AUT-03)

- **Gate automático:** JSON con la estructura del prompt, numeración SPEC =
  REQ, ≥ 2 criterios Gherkin con al menos un caso de error o borde, sin valores
  sin respaldo. **Pasó**: SPEC-AUT-03, 7 reglas, 5 criterios (los 3 del
  requisito y 2 casos borde nuevos), una alerta legal de protección de datos y
  7 supuestos.
- **Revisión:** en SDD un contrato no puede dejar supuestos abiertos. Se
  construyó `specs/specification.json` (esquema en `specs/schemas/`) con:
  - los 7 supuestos resueltos como **decisiones D-01 a D-07** (todos aceptados,
    precisando los límites exactos de la ventana y el bloqueo);
  - **D-08 / RB-8 / AC-AUT-03-07**: hueco que el modelo no mencionó (¿los
    intentos durante el bloqueo lo extienden?), resuelto desde el texto del
    requisito ("durante 15 minutos");
  - **AC-AUT-03-06**: el esquema de la especificación exige que toda regla
    tenga un criterio que la verifique, y RB-7 (contador por cuenta) no lo tenía;
  - D-09 (alcance, §1) y la alerta legal con la ley colombiana (Ley 1581 de 2012).
- **Parámetros** (5, 10, 15): verificados contra el requisito con el detector
  de valores sin respaldo de la plataforma: ninguno inventado.
- **Decisión:** aprobada como v1.0.0 (huella `cc17024f8a0c`).

## §3. Specification → Architecture Contract

- **Gate automático** (`calificar_fase3` del benchmark sobre la salida de
  Nemotron): 9/9 secciones, SPEC cubierto, ARCH-01..03 secuenciales. **No pasó**:
  ARCH ausentes del diagrama, código de implementación dentro del diseño y una
  **afirmación de verificación no realizada** ("verificado con un linter de
  Mermaid y un script de trazabilidad", el defecto conocido del prompt aprobado).
- **Revisión:** además, el contrato recibía el instante como texto (contra R2),
  trataba un correo mal formado como credenciales inválidas (contra D-01),
  devolvía un `dict` sin tipo y no definía el contador durante el bloqueo.
- **Corrección:** `specs/architecture_contract.md` conserva los componentes,
  nombres y decisiones de Nemotron y agrega un **contrato normativo** (stub
  `pyi` con firmas, errores y algoritmo) y las correcciones C-01 a C-08. Sobre
  el documento corregido, el mismo calificador: ARCH en el diagrama, sin código
  de implementación, SPEC cubierto (el único aviso es la cita de la frase falsa
  dentro de la tabla de correcciones).
- **Decisión:** aprobado.

## §4. Architecture Contract → Implementation

- **Primera generación** (`descartadas/4_implementacion_contrato_v1.json`):
  compiló, pero ruff dio 3 avisos. **Dos eran defectos del contrato aprobado en
  §3, no del modelo**, que lo siguió al pie de la letra: una llamada como valor
  por defecto (`policy = PolicyConfiguration()`, B008) y `ValueError` para tipos
  incorrectos (TRY004).
- **Decisión:** corregir la **fuente** (contrato: C-09 y C-10) y **regenerar**
  el código desde ella, en vez de parchar el código.
- **Segunda generación:** compila y cumple el contrato; queda 1 aviso propio del
  modelo (un import sin usar), corregido con `ruff --fix` (**I-01**, único cambio
  manual del código). Gate: compila, ruff sin avisos, solo biblioteca estándar,
  cada módulo declara `Implements: ARCH-xx, SPEC-AUT-03`.
- **Decisión:** aceptado para la fase de pruebas.

## §5. Implementation → Tests

- **Primer intento** (`descartadas/5_pruebas_fallo_de_red.json`): falló el
  servicio, no el modelo (sin respuesta y luego sin conexión a internet:
  `getaddrinfo failed`). Se repitió con la conexión restablecida.
- **Suite generada** (16 pruebas, TEST-01 a TEST-16, cada una con su criterio
  AC): pasa contra el código; cobertura 99 %; detecta 15 de 17 mutantes
  (`python -m sdd.mutacion`). Único cambio: un `noqa` justificado.
- **Hallazgos:**
  - **OBS-01** del reporte de defectos de Kimi: la especificación no definía
    el contador durante el bloqueo (solo el contrato, C-07). Se llevó a la
    fuente de verdad: **especificación v1.0.1** con la decisión **D-10**, y la
    prueba de conformidad de AC-AUT-03-02 lo verifica.
  - Los 2 mutantes sobrevivientes mostraban que ninguna suite probaba el
    valor mínimo válido (1) de la política, y una rama de `como_dict()` no se
    ejecutaba: se agregó `test_contrato_arquitectura.py`.
- **Gate final:** 30 pruebas en `tests/sdd` (9 de conformidad con la
  especificación, 16 generadas, 5 del contrato), **cobertura 100 %**, **17/17
  mutantes detectados**, ruff sin avisos.
- **Decisión:** aprobado y **sellado** contra SPEC-AUT-03 v1.0.1 (huella
  `78f967ade537`, `python -m sdd.trazabilidad --sellar`). Verificador de
  trazabilidad: **CONFORME, 0 problemas** (`specs/traceability_matrix.md`).

## §6. Endurecimiento del sello (hallazgo de la demostración)

El primer sello solo registraba la versión y la huella de la especificación.
La demostración (`DEMOSTRACION.md`) mostró dos debilidades, y el sello se
reforzó antes de la corrida definitiva:

1. **Un cambio solo en el código no lo detectaba el verificador** (solo las
   pruebas). Ahora el sello incluye la huella del código del módulo.
2. **El modelo de mantenimiento reescribió su propio sello** con la versión y
   la huella de la especificación nueva (en 2 corridas;
   `demostracion/descartadas/`). En un módulo que no había cambiado, esa
   "autoaprobación" habría pasado. Ahora la huella del código se calcula
   **ligada a la huella de la especificación**, así que un sello escrito a mano
   o por un modelo no pasa la verificación.

Formato actual: `# Spec: SPEC-AUT-03 v1.0.1 huella 78f967ade537 código <12 hex>`.
Pruebas: `tests/test_sdd_trazabilidad.py` (cambio en el código, sello escrito
a mano, sello falsificado en un módulo sin cambios).

## Resumen de lo que corrigieron las puertas

| Eslabón | Lo detectó | Qué | Dónde se corrigió |
|---|---|---|---|
| Especificación | Esquema (toda regla necesita un criterio) | RB-7 sin criterio | Especificación (AC-AUT-03-06) |
| Especificación | Revisión | Intentos durante el bloqueo sin definir | Especificación (D-08, RB-8, AC-AUT-03-07) |
| Arquitectura | Calificador automático | Afirmación falsa de verificación; ARCH fuera del diagrama; código en el diseño | Contrato (C-01, C-02, C-08) |
| Arquitectura | Revisión | Tipo del instante, validación del correo, retorno sin tipo, contador durante el bloqueo | Contrato (C-03 a C-07) |
| Implementación | ruff | Dos defectos del **contrato** | Contrato (C-09, C-10) y código regenerado |
| Implementación | ruff | Import sin usar | Código (I-01) |
| Pruebas | Reporte de defectos del modelo | Contador durante el bloqueo sin definir en la especificación | Especificación v1.0.1 (D-10) |
| Pruebas | Prueba de mutación | Valor límite de la política sin probar | Pruebas del contrato |
