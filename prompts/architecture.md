# Fase 3 — Arquitectura / Diseño

> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación
> de prompts. No editar a mano.

| Campo | Valor |
|---|---|
| Rol | Software Architect |
| Entrada | Especificación aprobada |
| Salida esperada | Arquitectura / contratos / diagramas (ARCH-XX) |
| Quality Gate de la fase (SDLC) | Restricciones + trazabilidad + revisión |
| Variables de la plantilla | `{{ESPECIFICACION_APROBADA}}`, `{{RESTRICCIONES_TECNICAS}}` |
| Run en la plataforma | `36a2f1b0-69cc-4fff-a535-e941a5751c67` |
| Estado | COMPLETED |
| Modelos | Optimizer `moonshotai/kimi-k3` · Auditor `nvidia/nemotron-3-super-120b-a12b` |
| Modelo que produjo la versión aprobada | `nvidia/nemotron-3-super-120b-a12b` (respaldo: el Optimizer principal no dio una respuesta usable; es el mismo modelo que el Auditor) |
| Validación | 2026-09-27T12:29:00.636838-05:00 → aprobación 2026-09-27T12:45:22.354913-05:00 |

## Métricas (Quality Gate de prompts, sección 6.1)

| | Score | Gates | gates_score |
|---|---|---|---|
| Inicial (línea base) | 79 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| Aprobada | 88 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| **Delta** | **+9** | | |

Iteraciones de optimización: 4 (3 automáticas, 0 humanas).

## 1. Prompt inicial

```text
Actúa como arquitecto de software. Diseña la arquitectura para la especificación aprobada.

Especificación aprobada:
{{ESPECIFICACION_APROBADA}}

Restricciones técnicas:
{{RESTRICCIONES_TECNICAS}}

Describe los componentes, sus responsabilidades y cómo se comunican. Define los contratos de las interfaces (endpoints, métodos, datos de entrada y salida) y agrega un diagrama en Mermaid. Cada decisión o componente debe tener un identificador ARCH-XX y decir qué SPEC cubre. Explica las decisiones importantes y respeta las restricciones.

Las variables entre {{...}} forman parte de la plantilla: no las cambies.
```

### Auditoría inicial (línea base)

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado con instrucciones claras, define rol, objetivo, formato esperado y requisitos de trazabilidad. La organización es coherente y no presenta contradicciones internas. |
| gate_2_cognicion | PASS | El prompt efectivamente guía un proceso de razonamiento estructurado: descompone la tarea en componentes, responsabilidades, comunicación, contratos y decisiones, lo que apoya un pensamiento sistemático y detallado. |
| gate_3_seguridad_veracidad | PASS | El prompt no introduce riesgos de seguridad, privacidad o veracidad. Fomenta respuestas basadas en especificaciones dadas y no alienta alucinaciones, siempre que se interprete el contexto como de diseño teórico. |
| gate_4_eficiencia_foco | PASS | El prompt evita over-engineering: solicita solo lo necesario para una arquitectura clara y trazable. Prioriza foco en componentes, comunicación y contratos, sin exceso de propiedades innecesarias. |

Recomendaciones del Auditor:

- Agregar una solicitud explícita de verificación de factibilidad técnica y riesgos identificados para fortalecer la metacognición (P10).
- Incluir una petición de aclaración cuando la especificación aprobada o las restricciones técnicas sean ambiguas o insuficientes, mejorando la propiedad de Interacción (P20).

## 2. Prompt optimizado y aprobado

```text
Actúa como arquitecto de software senior. Tu tarea es producir una documentación arquitectónica completa y rigurosa a partir de la especificación aprobada y las restricciones técnicas proporcionadas.

Especificación aprobada:
{{ESPECIFICACION_APROBADA}}

Restricciones técnicas:
{{RESTRICCIONES_TECNICAS}}

**Regla de identificación (obligatoria):**
- Todos los componentes y elementos arquitectónicos deben usar identificadores ARCH-XX estrictamente numéricos y secuenciales, comenzando en ARCH-01 y sin saltos ni repeticiones (ARCH-01, ARCH-02, ARCH-03, …).
- Antes de finalizar, verifica explícitamente que la secuencia es correcta; si encuentras un salto o duplicado, renuméralo y actualiza todas las referencias (incluido el diagrama Mermaid).

**Estructura obligatoria de tu respuesta (en Markdown):**
1. **Resumen de la arquitectura** (3‑5 líneas): estilo arquitectónico elegido y justificación breve.
2. **Componentes**: para cada componente incluye:
   - Identificador único ARCH-XX (numérico y secuencial, empezando en ARCH-01).
   - Nombre y responsabilidad única y clara.
   - Trazabilidad: lista de identificadores SPEC‑XX de la especificación que cubre (usa exactamente los IDs tal como aparecen; si un componente no cubre ningún SPEC, justifícalo).
   - Comunicación: con qué otros componentes interactúa y mediante qué mecanismo (síncrono/asíncrono, protocolo).
3. **Contratos de interfaces**: para cada interfaz relevante define endpoint y método (si aplica), datos de entrada y de salida con sus tipos, y códigos de error o casos límite principales.
4. **Decisiones de diseño**: explica las decisiones arquitectónicas importantes (alternativas descartadas, trade‑offs). Para **CADA** decisión indica: (a) el identificador ARCH‑XX del componente afectado, y (b) al menos una restricción técnica que la justifique, citándola explícitamente; si una decisión no deriva de ninguna restricción, explica por qué sigue siendo necesaria (ninguna decisión puede quedar sin justificación).
5. **Verificación de restricciones**: lista cada restricción técnica y cómo la arquitectura la cumple. Además, contrasta cruzadamente cada decisión de diseño de la sección 4 con al menos una restricción: confirma que ninguna decisión carece de anclaje en una restricción o justificación explícita, y que ninguna contradice las restricciones. Si una restricción impide cubrir algún SPEC, señalalo explícitamente como conflicto.
6. **Diagrama de arquitectura en Mermaid** (sintaxis válida), mostrando componentes y flujos de comunicación, usando los mismos IDs ARCH‑XX de la sección 2 como etiquetas.
7. **Supuestos y riesgos**: declara los supuestos asumidos ante ambigüedades o datos faltantes y los riesgos asociados (no inventes información).
8. **Brechas de cobertura**: cada SPEC de la especificación debe estar cubierto por al menos un ARCH‑XX; si alguno queda sin cobertura, indícalo aquí.
9. **Lista de comprobación final** (marca cada punto antes de terminar):
   - [ ] Todos los IDs ARCH‑XX son numéricos, secuenciales y sin huecos, empezando en ARCH‑01, y coinciden en las secciones 2, 3, 4 y 6.
   - [ ] Todo SPEC‑XX de la especificación aparece cubierto por al menos un ARCH‑XX (o está listado en Brechas de cobertura).
   - [ ] Cada decisión de diseño está contrastada con al menos una restricción técnica (o justificada explícitamente).
   - [ ] El diagrama Mermaid usa sintaxis válida y contiene todos los ARCH‑XX definidos.
   - [ ] **Se ha verificado el diagrama con un linter de Mermaid (p. ej. mermaid.live o mermaid‑cli) y se ha corroborado la correspondencia de IDs mediante un script de trazabilidad.**
   - [ ] Ninguna restricción técnica ha sido incumplida ni ignorada.

**Incentivo de calidad:** Se valorará especialmente la precisión en la numeración ARCH‑XX y la cobertura completa de SPEC‑XX; una documentación que cumpla rigurosamente estos aspectos recibirá una evaluación positiva destacada.

Las variables entre {{...}} forman parte de la plantilla: no las cambies ni las interpretes literalmente.

No incluyas código de implementación; el resultado es exclusivamente documentación arquitectónica.

Se recomienda, como buena práctica, validar el diagrama Mermaid con un linter y cruzar los IDs SPEC‑XX/ARCH‑XX con un script para garantizar cobertura completa y renderizado correcto.
```

Archivo para ejecución: `prompts/aprobados/3_architecture.txt`

### Auditoría de la versión aprobada

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado con secciones claras y obligatorias, tono profesional y objetivos explícitos. No presenta contradicciones internas y la organización por bloques es coherente. |
| gate_2_cognicion | PASS | El prompt guía un razonamiento complejo y multidisciplinario, requiriendo descomposición, trazabilidad, verificación cruzada y metacognición explícita mediante listas de comprobación y contraste de decisiones con restricciones. |
| gate_3_seguridad_veracidad | PASS | El prompt evita alucinaciones al exigir trazabilidad a SPEC-XX y verificación de cobertura, prohíbe inventar información en suposiciones y riesgos, y promueve la admisión de límites mediante la sección de brechas. No hay indicios de sesgo o riesgo de seguridad relevante en este contexto de documentación técnica. |
| gate_4_eficiencia_foco | PASS | El prompt evita over-engineering al enfocarse en propiedades clave como trazabilidad, verificación de IDs y cobertura de SPEC-XX, que son de alto impacto para la tarea. Solicita interacción solo cuando es necesaria (verificación de cobertura) y mantiene cortesía técnica. |

## 3. Historial de iteraciones

| # | Origen | Modelo | Score | Gates | Decisión humana |
|---|---|---|---|---|---|
| 1 | original | — | 79 | 4 PASS / 0 FAIL / 0 N/A | — |
| 2 | optimizer | moonshotai/kimi-k3 | 82 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 3 | optimizer | moonshotai/kimi-k3 | 84 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 4 | optimizer | moonshotai/kimi-k3 | 84 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 5 | optimizer | nvidia/nemotron-3-super-120b-a12b (respaldo; `moonshotai/kimi-k3` no respondió) | 88 | 4 PASS / 0 FAIL / 0 N/A | approve |

<details><summary>Timeline</summary>

- 2026-09-27T12:29:00.636838-05:00 — Prompt recibido.
- 2026-09-27T12:29:00.648177-05:00 — Iteración 1: línea base, se audita el prompt original sin optimizar.
- 2026-09-27T12:29:29.952350-05:00 — Auditoría completada: 4/4 Gates aprobados (score 79/100).
- 2026-09-27T12:31:02.781547-05:00 — Iteración 2: el Optimizer generó una versión mejorada.
- 2026-09-27T12:31:30.722368-05:00 — Auditoría completada: 4/4 Gates aprobados (score 82/100).
- 2026-09-27T12:31:33.525780-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:33:09.004611-05:00 — Iteración 3: el Optimizer generó una versión mejorada.
- 2026-09-27T12:33:31.284664-05:00 — Auditoría completada: 4/4 Gates aprobados (score 84/100).
- 2026-09-27T12:33:31.290707-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:36:49.237851-05:00 — Iteración 4: el Optimizer generó una versión mejorada.
- 2026-09-27T12:37:13.107915-05:00 — Auditoría completada: 4/4 Gates aprobados (score 84/100).
- 2026-09-27T12:37:13.113207-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:38:39.924507-05:00 — Iteración 5: el Optimizer generó una versión mejorada.
- 2026-09-27T12:38:58.296163-05:00 — Auditoría completada: 4/4 Gates aprobados (score 88/100).
- 2026-09-27T12:45:22.354913-05:00 — Humano aprobó el prompt.
- 2026-09-27T12:57:19.548003-05:00 — Ejecución completada, respuesta final generada.

</details>
