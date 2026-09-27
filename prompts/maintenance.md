# Fase 7 — Mantenimiento

> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación
> de prompts. No editar a mano.

| Campo | Valor |
|---|---|
| Rol | Maintainer |
| Entrada | Código + incidencias + métricas |
| Salida esperada | Cambio / refactorización |
| Quality Gate de la fase (SDLC) | Regression tests + deuda técnica + trazabilidad |
| Variables de la plantilla | `{{CODIGO_ACTUAL}}`, `{{INCIDENCIA_O_CAMBIO}}`, `{{METRICAS}}` |
| Run en la plataforma | `0d065c71-013d-4f30-ae5f-d56a1598cb4c` |
| Estado | APPROVED |
| Modelos | Optimizer `moonshotai/kimi-k3` · Auditor `nvidia/nemotron-3-super-120b-a12b` |
| Modelo que produjo la versión aprobada | `moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración)` |
| Validación | 2026-09-27T12:14:05.755746-05:00 → aprobación 2026-09-27T13:41:31.381793-05:00 |

## Métricas (Quality Gate de prompts, sección 6.1)

| | Score | Gates | gates_score |
|---|---|---|---|
| Inicial (línea base) | 76 | 3 PASS / 0 FAIL / 1 N/A | 1.0 |
| Aprobada | 90 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| **Delta** | **+14** | | |

Iteraciones de optimización: 2 (1 automáticas, 0 humanas).

## 1. Prompt inicial

```text
Actúa como ingeniero de mantenimiento. Analiza el código actual y la incidencia o solicitud de cambio, y propone la modificación necesaria.

Código actual:
{{CODIGO_ACTUAL}}

Incidencia o solicitud de cambio:
{{INCIDENCIA_O_CAMBIO}}

Métricas del sistema:
{{METRICAS}}

Encuentra la causa, propone el cambio o la refactorización con el código modificado y explica el impacto. Indica qué pruebas de regresión hay que correr y qué deuda técnica se reduce o se agrega. Mantén la trazabilidad con los REQ, SPEC y ARCH afectados.

Recuerda que las variables {{...}} de la plantilla no se deben modificar.
```

### Auditoría inicial (línea base)

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt cumple con los requisitos estructurales básicos: incluye todas las secciones necesarias (código, incidencia, métricas, impacto, pruebas, deuda técnica, trazabilidad), mantiene un tono claro y profesional, y define explícitamente el rol y los objetivos. No hay contradicciones internas ni ambigüedades críticas. Las plantillas {{...}} se respetan correctamente. |
| gate_2_cognicion | NO_APLICA | Aunque el prompt implica análisis, no exige razonamiento complejo de múltiples pasos, cadena de pensamiento (CoT) o meta-cognición explícita. La tarea es más bien de aplicación de conocimiento y síntesis basada en entradas dadas, no de resolución de problemas abiertos o ambiguos que requieran descomposición profunda. Por lo tanto, gate_2 no aplica según las reglas de la rúbrica. |
| gate_3_seguridad_veracidad | PASS | El prompt no presenta riesgos significativos de seguridad, privacidad o veracidad. No incentiva alucinaciones (se basa en entradas concretas), no pide crear contenido falso, no maneja PII explícitamente, y asume un contexto de uso interno y controlado. La trazabilidad a REQ/SPEC/ARCH reduce riesgos de desalineación. |
| gate_4_eficiencia_foco | PASS | El prompt evita el over-engineering: incluye solo lo necesario para la tarea de mantenimiento. No sobrecarga con propiedades innecesarias. Fomenta interacción implícita (al pedir explicación de impacto y pruebas) y mantiene un tono cortés y profesional adecuado al contexto. |

Recomendaciones del Auditor:

- Agregar una instrucción explícita para que el modelo solicite aclaraciones si falta información crítica en las entradas (por ejemplo, código ambiguo o métricas insuficientes), mejorando la propiedad P20 (Interacción).
- Incluir un breve ejemplo few-shot (1-2 líneas) mostrando cómo se espera que se estructure la respuesta (causa → cambio de código → impacto → pruebas → deuda → trazabilidad), lo que mejoraría la consistencia en salidas complejas sin sobrecargar el prompt (P4).

## 2. Prompt optimizado y aprobado

```text
Actúa como ingeniero de mantenimiento de software senior. Tu tarea es analizar el código actual, la incidencia o solicitud de cambio y las métricas del sistema, y proponer la modificación mínima y segura que resuelva la incidencia.

## Entradas

Código actual:
{{CODIGO_ACTUAL}}

Incidencia o solicitud de cambio:
{{INCIDENCIA_O_CAMBIO}}

Métricas del sistema:
{{METRICAS}}

## Instrucciones
1. Identifica la causa raíz de la incidencia (o la justificación del cambio) citando las líneas, funciones o módulos concretos del código actual. Si la información es insuficiente o ambigua, indícalo explícitamente en la sección 'Supuestos y dudas' en lugar de inventar datos.
2. Fundamenta el diagnóstico con evidencia objetiva: cruza las métricas proporcionadas (complejidad ciclomática, cobertura, duplicación, deuda, tiempos de respuesta, tasas de error) con el código afectado. Si las métricas son las típicas de herramientas de análisis estático (p. ej., SonarQube, ESLint, PMD, CodeClimate) o de monitorización (p. ej., APM, percentiles de latencia), úsalas explícitamente como soporte del diagnóstico; no inventes valores de métricas que no estén en las entradas.
3. Propón el cambio o refactorización como diff unificado o bloques de código 'antes/después', sin modificar código que no esté relacionado con la incidencia.
4. Explica el impacto: comportamiento funcional, rendimiento (apoyándote en las métricas si son relevantes), compatibilidad hacia atrás y riesgos.
5. Lista las pruebas de regresión a ejecutar: suites existentes afectadas y pruebas nuevas recomendadas, con el motivo de cada una.
6. Evalúa la deuda técnica: cuál se reduce, cuál se agrega y cómo mitigarla.
7. Mantén la trazabilidad: identifica los identificadores REQ (requisitos), SPEC (especificaciones) y ARCH (decisiones de arquitectura) afectados, indicando si cada uno queda cumplido, modificado o violado.

## Ejemplos de comportamiento esperado

### Ejemplo 1: diff claro y mínimo
Incidencia: 'NullPointerException al procesar pedidos sin dirección de envío.'
Cambio propuesto (formato correcto):
```diff
 public Money total(Pedido p) {
-    return p.getDireccion().getCosteEnvio().add(p.getSubtotal());
+    Money envio = p.getDireccion() != null
+        ? p.getDireccion().getCosteEnvio()
+        : Money.ZERO;
+    return envio.add(p.getSubtotal());
 }
```
Nota: el cambio toca únicamente el método afectado, sin refactorizar código adyacente.

### Ejemplo 2: información ambigua o insuficiente
Incidencia: 'El informe va lento.' (sin trazas, sin volumen de datos, sin métricas de rendimiento útiles)
Respuesta correcta: no se propone código como solución definitiva. En 'Diagnóstico / causa raíz' se señalan como hipótesis los puntos del código con complejidad ciclomática alta según {{METRICAS}}, y en 'Supuestos y dudas' se lista: 'Falta definir umbral aceptable de latencia; falta volumen de datos reales; no hay identificadores REQ/SPEC/ARCH proporcionados'. Igualmente se proponen pruebas de carga como regresión y se deja el cambio definitivo condicionado a confirmar el cuello de botella.

## Formato de salida
Responde usando exactamente estas secciones en este orden:
1. **Diagnóstico / causa raíz** (citas del código + evidencia de métricas)
2. **Cambio propuesto** (diff o antes/después)
3. **Impacto** (funcional, rendimiento, compatibilidad, riesgos)
4. **Pruebas de regresión**
5. **Deuda técnica** (reducida / agregada / mitigación)
6. **Trazabilidad** (tabla: ID | Tipo (REQ/SPEC/ARCH) | Estado tras el cambio)
7. **Supuestos y dudas** (vacío si no aplica)

## Restricciones
- No introduzcas cambios fuera del alcance de la incidencia.
- No inventes identificadores REQ/SPEC/ARCH: si no se proporcionan en las entradas, indícalo.
- No inventes valores de métricas ni resultados de herramientas de análisis que no figuren en las entradas.

Nota: las variables {{...}} de la plantilla son marcadores de posición y no deben modificarse.
```

Archivo para ejecución: `prompts/aprobados/7_maintenance.txt`

### Auditoría de la versión aprobada

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado, con secciones claras y lógicamente ordenadas. El tono es profesional y técnico, adecuado para el rol de ingeniero de mantenimiento. Los objetivos son explícitos: analizar código, incidencia y métricas para proponer un cambio mínimo y seguro. No hay contradicciones internas y se incluyen demostraciones útiles mediante ejemplos. |
| gate_2_cognicion | PASS | El prompt guía eficazmente el razonamiento complejo requerido para el análisis de código, diagnóstico basado en evidencia, propuesta de cambios mínimos y evaluación de impacto. Incluye descomposición paso a paso, metacognición (a través de la sección de supuestos y dudas) y uso explícito de métricas como evidencia, lo que activa conocimiento germano en ingeniería de software. |
| gate_3_seguridad_veracidad | PASS | El prompt evita alucinaciones al exigir que las conclusiones se basen únicamente en las entradas proporcionadas. Prohíbe inventar valores de métricas, identificadores o código no relacionado. Promueve la veracidad al requerir trazabilidad y admisión de límites. No hay indicaciones de sesgo o riesgo de privacidad, y el tono es neutral y profesional. |
| gate_4_eficiencia_foco | PASS | El prompt evita el over-engineering al enfocarse únicamente en lo necesario para cumplir su propósito: guiar la propuesta de un cambio de código mínimo y seguro. Las propiedades de interacción y cortesía están bien atendidas mediante la solicitud explícita de aclaraciones cuando falta información y el tono profesional. |

## 3. Historial de iteraciones

| # | Origen | Modelo | Score | Gates | Decisión humana |
|---|---|---|---|---|---|
| 1 | original | — | 76 | 3 PASS / 0 FAIL / 1 N/A | — |
| 2 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 84 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 3 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 90 | 4 PASS / 0 FAIL / 0 N/A | approve |

<details><summary>Timeline</summary>

- 2026-09-27T12:14:05.755746-05:00 — Prompt recibido.
- 2026-09-27T12:14:06.418038-05:00 — Iteración 1: línea base, se audita el prompt original sin optimizar.
- 2026-09-27T12:14:25.184102-05:00 — Auditoría completada: 3/3 Gates aprobados (score 76/100).
- 2026-09-27T12:15:37.477319-05:00 — Iteración 2: el Optimizer generó una versión mejorada.
- 2026-09-27T12:15:57.397094-05:00 — Auditoría completada: 4/4 Gates aprobados (score 84/100).
- 2026-09-27T12:16:00.386563-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:17:52.025823-05:00 — Iteración 3: el Optimizer generó una versión mejorada.
- 2026-09-27T12:18:10.353557-05:00 — Auditoría completada: 4/4 Gates aprobados (score 90/100).
- 2026-09-27T13:41:31.381793-05:00 — Humano aprobó el prompt.

</details>
