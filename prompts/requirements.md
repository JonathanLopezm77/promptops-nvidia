# Fase 1 — Requerimientos

> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación
> de prompts. No editar a mano.

| Campo | Valor |
|---|---|
| Rol | Requirements Engineer |
| Entrada | Necesidad + contexto del stakeholder |
| Salida esperada | Requisitos estructurados (REQ-XX) |
| Quality Gate de la fase (SDLC) | Quality Score + verificabilidad + trazabilidad |
| Variables de la plantilla | `{{CONTEXTO_DEL_PROYECTO}}`, `{{NECESIDAD_DEL_STAKEHOLDER}}` |
| Run en la plataforma | `be249146-7bc9-4002-8272-69e6d4441896` |
| Estado | APPROVED |
| Modelos | Optimizer `moonshotai/kimi-k3` · Auditor `nvidia/nemotron-3-super-120b-a12b` |
| Modelo que produjo la versión aprobada | `moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración)` |
| Validación | 2026-09-27T12:14:05.733744-05:00 → aprobación 2026-09-27T13:09:45.626607-05:00 |

## Métricas (Quality Gate de prompts, sección 6.1)

| | Score | Gates | gates_score |
|---|---|---|---|
| Inicial (línea base) | 76 | 3 PASS / 0 FAIL / 1 N/A | 1.0 |
| Aprobada | 86 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| **Delta** | **+10** | | |

Iteraciones de optimización: 4 (3 automáticas, 0 humanas).

## 1. Prompt inicial

```text
Actúa como Ingeniero de Requisitos. A partir de la necesidad del stakeholder y el contexto del proyecto, redacta los requisitos del sistema.

Necesidad del stakeholder:
{{NECESIDAD_DEL_STAKEHOLDER}}

Contexto del proyecto:
{{CONTEXTO_DEL_PROYECTO}}

Escribe requisitos funcionales y no funcionales claros, uno por línea, con un identificador REQ-01, REQ-02, etc. Cada requisito debe ser verificable y tener al menos un criterio de aceptación. Si falta información, indícalo en lugar de suponerla. Usa la forma "El sistema deberá...".

Nota: los textos entre dobles llaves {{...}} son variables de la plantilla que se reemplazan al ejecutarla; deben conservarse tal cual.
```

### Auditoría inicial (línea base)

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt cumple con los criterios estructurales básicos: es claro, tiene un rol definido, formato de salida especificado y se organiza lógicamente. No hay contradicciones internas. |
| gate_2_cognicion | NO_APLICA | La tarea de redactar requisitos a partir de entradas dadas es más bien una tarea de transformación y estructuración que de razonamiento complejo, abstracción o resolución de problemas novedosos. No requiere cadena de pensamiento profunda ni activación de conocimiento previo especializado más allá de lo explícito en el prompt. |
| gate_3_seguridad_veracidad | PASS | El prompt muestra buenas prácticas de veracidad y seguridad: instruye a no suponer información faltante, lo que reduce alucinaciones, y no presenta riesgos evidentes de sesgo, inyección o privacidad en su construcción. |
| gate_4_eficiencia_foco | PASS | El prompt evita over-engineering: se enfoca en lo esencial para generar requisitos verificables. Aunque podría mejorar en interacción (pidiendo aclaraciones proactivamente), su enfoque es adecuado para la tarea. |

Recomendaciones del Auditor:

- Agregar 1-2 ejemplos Few-shot de requisitos bien formados (con identificador, formato 'El sistema deberá...' y criterio de aceptación) para guiar mejor la salida y reducir variabilidad.
- Incluir una solicitud explícita de autoverificación antes de finalizar (ej. 'Antes de entregar, revisa que cada requisito tenga un criterio de aceptación verificable y esté escrito en la forma requerida').

## 2. Prompt optimizado y aprobado

```text
Actúa como Ingeniero de Requisitos senior. Sé preciso y riguroso: tu salida será evaluada por su trazabilidad, objetividad y total ausencia de suposiciones no fundamentadas. A partir de la necesidad del stakeholder y el contexto del proyecto, redacta la especificación de requisitos del sistema.

Necesidad del stakeholder:
{{NECESIDAD_DEL_STAKEHOLDER}}

Contexto del proyecto:
{{CONTEXTO_DEL_PROYECTO}}

Instrucciones:
1. Deriva los requisitos exclusivamente de la información proporcionada; no inventes funcionalidades ni supongas datos.
2. Incluye únicamente requisitos que aporten valor significativo al stakeholder o al sistema; evita requisitos triviales, obvios o sin impacto (por ejemplo, funciones implícitas que no condicionan el diseño ni la verificación).
3. Clasifica cada requisito como funcional (RF) o no funcional (RNF) y numéralos por separado: RF-01, RF-02... y RNF-01, RNF-02...
4. Redacta cada requisito en una sola línea con la forma "El sistema deberá...", usando un único verbo de acción medible y términos cuantificables (evita ambigüedades como "rápido", "fácil", "adecuado" sin métrica). NO uses verbos vagos o genéricos como "gestionar", "procesar", "manejar", "administrar" o "ofrecer soporte": sustitúyelos por el verbo de acción concreto y observable (por ejemplo, "registrar", "calcular y mostrar", "validar", "notificar por correo").
5. Cada requisito debe ser verificable e ir seguido de al menos un criterio de aceptación en la línea siguiente, con el prefijo "Criterio de aceptación:". Cada criterio debe ser independiente y comprobable mediante una prueba, medición u observación directa, con condiciones y resultados objetivos (valores numéricos, estados, mensajes), sin depender de interpretación subjetiva ni de otros criterios.
6. Si la información es insuficiente o ambigua para definir un requisito completo, NO la supongas: formula una pregunta aclaratoria concreta al stakeholder. Distingue dos casos:
   a) Información faltante: ausencia total de un dato necesario.
   b) Información ambigua: el dato existe pero admite múltiples interpretaciones; en este caso indica las interpretaciones posibles dentro de la pregunta.
7. Agrupa todas las preguntas aclaratorias al final, en las secciones correspondientes, como preguntas directamente formulables al stakeholder.

Ejemplo de requisitos bien formateados (úsalo como referencia de estilo y formato):
RF-01: El sistema deberá permitir al usuario registrarse ingresando correo electrónico y contraseña de mínimo 8 caracteres.
Criterio de aceptación: Se crea la cuenta y se muestra confirmación cuando el correo es válido y la contraseña cumple la longitud mínima; en caso contrario se muestra un mensaje de error específico.

RNF-01: El sistema deberá responder a cualquier consulta de búsqueda en menos de 2 segundos con hasta 10.000 usuarios simultáneos.
Criterio de aceptación: El 95% de las búsquedas ejecutadas en la prueba de carga con 10.000 usuarios simultáneos responde en ≤2 segundos.

Formato de salida obligatorio:
## Requisitos funcionales
RF-01: El sistema deberá...
Criterio de aceptación: ...

## Requisitos no funcionales
RNF-01: El sistema deberá...
Criterio de aceptación: ...

## Información faltante
- Pregunta concreta al stakeholder sobre cada dato ausente...

## Aclaraciones sobre información ambigua
- Pregunta al stakeholder indicando las interpretaciones posibles...

Si alguna sección no aplica (por ejemplo, no hay información faltante), indícalo con "Sin elementos". No incluyas introducciones, conclusiones ni texto fuera de esta estructura.
```

Archivo para ejecución: `prompts/aprobados/1_requirements.txt`

### Auditoría de la versión aprobada

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado con instrucciones claras, roles definidos, formato de salida explícito y sin contradicciones internas. Cumple con los principios de claridad y organización necesaria para guiar la generación de requisitos trazables. |
| gate_2_cognicion | PASS | El prompt guía efectivamente un proceso de razonamiento estructurado: obliga a derivar requisitos únicamente de la información dada, a clasificarlos, a hacerlos medibles y verificables, y a identificar lagunas mediante preguntas aclaratorias, lo que refleja una carga intrínseca adecuada y metacognición explícita. |
| gate_3_seguridad_veracidad | PASS | El prompt promueve la veracidad al proibir suposiciones y exigir trazabilidad a la entrada, reduce el riesgo de alucinaciones mediante la verificación explícita y evita sesgos al ceñirse estrictamente a la información proporcionada. No solicita ni maneja datos sensibles, por lo que privacidad y seguridad no son puntos críticos aquí. |
| gate_4_eficiencia_foco | PASS | El prompt evita el sobre-engineering al enfocarse únicamente en lo esencial para generar requisitos trazables y verificables. Prioriza la claridad, la medibilidad y la trazabilidad, que son las propiedades de mayor impacto para este caso de uso, sin incluir elementos innecesarios. |

## 3. Historial de iteraciones

| # | Origen | Modelo | Score | Gates | Decisión humana |
|---|---|---|---|---|---|
| 1 | original | — | 76 | 3 PASS / 0 FAIL / 1 N/A | — |
| 2 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 87 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 3 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 86 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 4 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 84 | 3 PASS / 0 FAIL / 1 N/A | iterate (automática) |
| 5 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 86 | 4 PASS / 0 FAIL / 0 N/A | approve |

<details><summary>Timeline</summary>

- 2026-09-27T12:14:05.733744-05:00 — Prompt recibido.
- 2026-09-27T12:14:06.866182-05:00 — Iteración 1: línea base, se audita el prompt original sin optimizar.
- 2026-09-27T12:14:34.871078-05:00 — Auditoría completada: 3/3 Gates aprobados (score 76/100).
- 2026-09-27T12:15:38.057341-05:00 — Iteración 2: el Optimizer generó una versión mejorada.
- 2026-09-27T12:16:12.446611-05:00 — Auditoría completada: 4/4 Gates aprobados (score 87/100).
- 2026-09-27T12:16:12.483758-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:17:48.048617-05:00 — Iteración 3: el Optimizer generó una versión mejorada.
- 2026-09-27T12:18:27.941585-05:00 — Auditoría completada: 4/4 Gates aprobados (score 86/100).
- 2026-09-27T12:18:27.949009-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:19:44.504425-05:00 — Iteración 4: el Optimizer generó una versión mejorada.
- 2026-09-27T12:20:02.835522-05:00 — Auditoría completada: 3/3 Gates aprobados (score 84/100).
- 2026-09-27T12:20:02.841493-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:21:32.460089-05:00 — Iteración 5: el Optimizer generó una versión mejorada.
- 2026-09-27T12:21:51.795329-05:00 — Auditoría completada: 4/4 Gates aprobados (score 86/100).
- 2026-09-27T13:09:45.626607-05:00 — Humano aprobó el prompt.

</details>
