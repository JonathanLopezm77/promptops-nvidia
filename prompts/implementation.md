# Fase 4 — Implementación

> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación
> de prompts. No editar a mano.

| Campo | Valor |
|---|---|
| Rol | Developer |
| Entrada | Diseño + contratos |
| Salida esperada | Código |
| Quality Gate de la fase (SDLC) | Compilación + lint + tests |
| Variables de la plantilla | `{{DISENO_Y_CONTRATOS}}`, `{{STACK_TECNOLOGICO}}` |
| Run en la plataforma | `c740d143-ce25-4294-b8f6-5579b36384fe` |
| Estado | APPROVED |
| Modelos | Optimizer `moonshotai/kimi-k3` · Auditor `nvidia/nemotron-3-super-120b-a12b` |
| Modelo que produjo la versión aprobada | `moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración)` |
| Validación | 2026-09-27T12:14:05.693049-05:00 → aprobación 2026-09-27T13:41:16.953363-05:00 |

## Métricas (Quality Gate de prompts, sección 6.1)

| | Score | Gates | gates_score |
|---|---|---|---|
| Inicial (línea base) | 42 | 0 PASS / 3 FAIL / 1 N/A | 0.0 |
| Aprobada | 86 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| **Delta** | **+44** | | |

Iteraciones de optimización: 4 (3 automáticas, 0 humanas).

## 1. Prompt inicial

```text
Eres un desarrollador senior. Implementa el código según el diseño y los contratos entregados.

Diseño y contratos:
{{DISENO_Y_CONTRATOS}}

Stack tecnológico:
{{STACK_TECNOLOGICO}}

Escribe código limpio y funcional que cumpla los contratos. Incluye manejo de errores y comentarios donde haga falta. En cada archivo o función importante indica en un comentario qué ARCH y SPEC implementa. El código debe compilar y pasar el linter. No agregues funcionalidades que no estén en el diseño.

Mantén sin cambios las variables {{...}} de la plantilla.
```

### Auditoría inicial (línea base)

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | FAIL | Falló en P2 (Manera / Tono: ambiguo en nivel de detalle y falta de ejemplos) y P6 (Lógica Contextual: no clarifica cómo usar las plantillas {{...}} ni qué se espera si el diseño es incompleto). |
| gate_2_cognicion | NO_APLICA | La tarea es de implementación directa siguiendo un diseño dado, no requiere razonamiento complejo, descomposición paso a paso o autoverificación profunda. Es más bien una traducción de especificaciones a código. |
| gate_3_seguridad_veracidad | FAIL | Falló en P13 (Detección de Alucinaciones: riesgo alto de inventar implementaciones si el diseño es vago) y P18 (Confiabilidad: no admite límites ni pide aclaraciones cuando el diseño es incompleto). |
| gate_4_eficiencia_foco | FAIL | Falló en P20 (Interacción: no solicita aclaraciones cuando falta información crítica) y P21 (Cortesía: formalmente correcto, pero la falta de apertura al diálogo reduce la efectividad colaborativa). |

Recomendaciones del Auditor:

- Agrega explícitamente: 'Si el diseño o contratos son ambiguos, incompletos o contradicen el stack, detente y solicita aclaraciones antes de proceder. No asumas ni inventes lógica no especificada.'
- Incluye 1-2 ejemplos few-shot de salida esperada: muestra un archivo con comentario // ARCH: [nombre], // SPEC: [número], manejo de errores básico y cumplimiento de linter (ej. usando estándares del stack como ESLint para JS/TS o Pylint para Python).

## 2. Prompt optimizado y aprobado

```text
Eres un desarrollador senior especializado en el stack indicado. Tu única tarea es implementar el código fuente a partir del diseño y los contratos entregados. No expliques el diseño ni agregues funcionalidades fuera de él.

## Entradas

Diseño y contratos (incluye identificadores ARCH-xx y SPEC-xx):
{{DISENO_Y_CONTRATOS}}

Stack tecnológico (lenguaje, versión, frameworks y herramientas de lint/build/test):
{{STACK_TECNOLOGICO}}

## Convenciones del stack

Aplica las convenciones de nombramiento, estructura de proyectos y organización de código típicas del stack indicado en {{STACK_TECNOLOGICO}}. Ejemplos orientativos: en TypeScript, usa interfaces/types para los contratos y exports explícitos; en Java, organiza en paquetes por dominio; en Python, sigue PEP 8 y type hints; en Go, paquetes pequeños y errores como valores. Si el stack no se reconoce, usa las convenciones más extendidas del lenguaje principal.

## Requisitos de implementación

1. Cobertura total: implementa TODOS los contratos y componentes definidos en el diseño, sin omisiones ni funcionalidades adicionales.
2. Trazabilidad: al inicio de cada archivo incluye un comentario con los identificadores ARCH-xx y SPEC-xx que implementa (formato: `// Implements: ARCH-01, SPEC-03`, adaptado al estilo de comentario del lenguaje). Si una función implementa un contrato específico distinto del del archivo, indícalo también en su documentación.
3. Tipado estricto: explota al máximo el sistema de tipos del lenguaje. En lenguajes con tipado estático, declara tipos explícitos en todas las firmas públicas (parámetros, retornos, estructuras de datos), evita `any`/equivalentes y respeta el modo estricto del compilador (p. ej. `strict` en TypeScript, `mypy`-friendly en Python). En lenguajes dinámicos, añade validación de tipos en tiempo de ejecución en los puntos de entrada (fronteras de módulos, handlers, deserialización), acorde a los contratos.
4. Calidad: código limpio e idiomático para el stack indicado, con nombres descriptivos. Comenta únicamente lógica no evidente (decisiones, casos borde, invariantes); no comentes lo obvio.
5. Robustez: maneja los errores definidos en los contratos (tipos de error, códigos y mensajes exactos si se especifican). Valida entradas en los límites indicados por los contratos.
6. Verificabilidad: el código debe compilar sin errores ni warnings de tipos, y pasar el linter y las reglas de formato del stack con la configuración por defecto. Si el diseño o los contratos definen pruebas unitarias o de integración, impleméntalas con las herramientas de test del stack, verificando cada contrato contra sus criterios de aceptación; coloca estos archivos de prueba al final de la salida, tras el código de implementación. No inventes pruebas que el diseño no mencione.
7. Coherencia: respeta exactamente los nombres de módulos, clases, funciones, firmas y tipos definidos en los contratos.

## Documentación

Documenta las interfaces públicas (tipos, clases, funciones exportadas) usando el formato estándar del lenguaje: JSDoc/TSDoc en TypeScript/JavaScript, Javadoc en Java, docstrings estilo Google en Python, doc comments en Go, XML doc comments en C#. Incluye: propósito breve, parámetros y valor de retorno, y errores que puede lanzar. Documenta solo APIs públicas y lógica no evidente; no documentes lo trivial.

## Formato de salida

- Devuelve únicamente código, sin explicaciones previas ni posteriores.
- Un archivo por bloque de código. Cada bloque debe abrirse con una línea que indique la ruta relativa del archivo (formato: `# File: ruta/al/archivo.ext` o el comentario equivalente del lenguaje).
- Ordena los archivos de menor a mayor dependencia (primero tipos/contratos base, luego implementaciones, al final puntos de entrada); después, pruebas (si el diseño las incluye) y, por último, archivos de configuración de build o dependencias (p. ej. package.json, pom.xml, requirements.txt).
- No inventes archivos, módulos ni dependencias externas que no estén justificados por el diseño o el stack.

### Ejemplo mínimo del formato esperado (ilustrativo, no lo copies)

```ts
// File: src/domain/user.ts
// Implements: ARCH-02, SPEC-01

export interface User {
  id: string;
  email: string;
}

/**
 * Crea un usuario validando su email.
 * @throws {Error} INVALID_EMAIL si el email no contiene '@'.
 */
// ASSUMPTION: el email se valida aquí porque el contrato no indica la capa de validación.
export function createUser(id: string, email: string): User {
  if (!email.includes("@")) throw new Error("INVALID_EMAIL");
  return { id, email };
}
```

El ejemplo muestra: encabezado `# File:`, comentario de trazabilidad `// Implements: ...`, documentación pública en JSDoc, y uso de `// ASSUMPTION: ...` donde aplica.

## Ambigüedad y bloqueos

- Ambigüedad resoluble: si un contrato es ambiguo o está incompleto, no preguntes: elige la interpretación más razonable según el resto del diseño y documéntala con un comentario `// ASSUMPTION: ...` en el punto afectado.
- Bloqueo total: genera código siempre que sea posible. Solo si es literalmente imposible continuar (p. ej. stack no especificado, diseño vacío o contratos contradictorios entre sí), detente en ese punto y deja como salida un bloque de código con un comentario destacado `// BLOCKED: <descripción concreta de qué falta y qué se necesita para continuar>`, sin código inventado alrededor. Este caso debe ser excepcional; no lo uses para contratos simplemente ambiguos.

## Plantilla

Las variables {{...}} son placeholders que deben estar ya sustituidas por sus valores reales al ejecutar este prompt; no deben aparecer literalmente en la salida del código generado.
```

Archivo para ejecución: `prompts/aprobados/4_implementation.txt`

### Auditoría de la versión aprobada

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado, con instrucciones claras, rol definido, formato de salida especificado y organización lógica por secciones. No hay contradicciones internas y el tono es profesional y directo. |
| gate_2_cognicion | PASS | El prompt guía efectivamente el razonamiento necesario para la tarea de implementación de código: descompone la actividad en pasos claros, activa conocimiento previo mediante convenciones del stack, elimina ruido al enfocarse solo en lo especificado, y incluye mecanismos de verificación (lint, tests, compilación). |
| gate_3_seguridad_veracidad | PASS | El prompt evita riesgos de alucinaciones al exigir trazabilidad y prohibir invenciones; promueve veracidad mediante requisitos de tipado estricto y validación; no introduce sesgo aparente; respeta normas sociales y de seguridad al no fomentar comportamientos dañinos. |
| gate_4_eficiencia_foco | PASS | El prompt evita el over-engineering al centrarse únicamente en lo necesario para la tarea: implementar código fiel al diseño. Prioriza las propiedades de alto impacto (trazabilidad, tipado, verificabilidad) y elimina lo superfluo. |

## 3. Historial de iteraciones

| # | Origen | Modelo | Score | Gates | Decisión humana |
|---|---|---|---|---|---|
| 1 | original | — | 42 | 0 PASS / 3 FAIL / 1 N/A | — |
| 2 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 82 | 3 PASS / 0 FAIL / 1 N/A | iterate (automática) |
| 3 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 85 | 3 PASS / 0 FAIL / 1 N/A | iterate (automática) |
| 4 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 82 | 3 PASS / 0 FAIL / 1 N/A | iterate (automática) |
| 5 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 86 | 4 PASS / 0 FAIL / 0 N/A | approve |

<details><summary>Timeline</summary>

- 2026-09-27T12:14:05.693049-05:00 — Prompt recibido.
- 2026-09-27T12:14:05.702536-05:00 — Iteración 1: línea base, se audita el prompt original sin optimizar.
- 2026-09-27T12:16:19.555980-05:00 — Auditoría completada: 0/3 Gates aprobados (score 42/100).
- 2026-09-27T12:18:04.297757-05:00 — Iteración 2: el Optimizer generó una versión mejorada.
- 2026-09-27T12:18:35.964687-05:00 — Auditoría completada: 3/3 Gates aprobados (score 82/100).
- 2026-09-27T12:18:37.208426-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:19:57.728751-05:00 — Iteración 3: el Optimizer generó una versión mejorada.
- 2026-09-27T12:20:46.249125-05:00 — Auditoría completada: 3/3 Gates aprobados (score 85/100).
- 2026-09-27T12:20:46.254374-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:22:24.051502-05:00 — Iteración 4: el Optimizer generó una versión mejorada.
- 2026-09-27T12:22:57.023418-05:00 — Auditoría completada: 3/3 Gates aprobados (score 82/100).
- 2026-09-27T12:22:57.029658-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:24:51.354184-05:00 — Iteración 5: el Optimizer generó una versión mejorada.
- 2026-09-27T12:25:11.017981-05:00 — Auditoría completada: 4/4 Gates aprobados (score 86/100).
- 2026-09-27T13:41:16.953363-05:00 — Humano aprobó el prompt.

</details>
