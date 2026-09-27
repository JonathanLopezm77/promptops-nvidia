# Fase 2 — Análisis / Especificación

> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación
> de prompts. No editar a mano.

| Campo | Valor |
|---|---|
| Rol | Analista / especificador |
| Entrada | Requisitos aprobados |
| Salida esperada | Criterios de aceptación / especificación (SPEC-XX) |
| Quality Gate de la fase (SDLC) | Completitud + consistencia + schema |
| Variables de la plantilla | `{{REQUISITOS_APROBADOS}}` |
| Run en la plataforma | `24c5e24b-91ca-4141-96fc-7bb9f6108e84` |
| Estado | APPROVED |
| Modelos | Optimizer `moonshotai/kimi-k3` · Auditor `nvidia/nemotron-3-super-120b-a12b` |
| Modelo que produjo la versión aprobada | `moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración)` |
| Validación | 2026-09-27T12:14:05.764351-05:00 → aprobación 2026-09-27T13:41:09.752940-05:00 |

## Métricas (Quality Gate de prompts, sección 6.1)

| | Score | Gates | gates_score |
|---|---|---|---|
| Inicial (línea base) | 75 | 3 PASS / 0 FAIL / 1 N/A | 1.0 |
| Aprobada | 88 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| **Delta** | **+13** | | |

Iteraciones de optimización: 4 (3 automáticas, 0 humanas).

## 1. Prompt inicial

```text
Eres un analista de software. Toma los requisitos aprobados y conviértelos en una especificación detallada que el equipo pueda usar para diseñar y probar el sistema.

Requisitos aprobados:
{{REQUISITOS_APROBADOS}}

Para cada requisito crea una especificación SPEC-XX que diga de qué REQ viene, las entradas, salidas, reglas de negocio y los criterios de aceptación en formato Dado/Cuando/Entonces. Revisa que no haya contradicciones entre requisitos. Entrega el resultado en JSON.

Los textos entre {{...}} son variables de la plantilla y no se deben modificar.
```

### Auditoría inicial (línea base)

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado, con instrucciones claras, formato de salida especificado (JSON), y un rol definido. No presenta contradicciones internas y utiliza un tono profesional y directo. |
| gate_2_cognicion | NO_APLICA | La tarea consiste en transformación directa de requisitos a especificaciones siguiendo una plantilla fija (SPEC-XX, entradas, salidas, reglas, criterios Dado/Cuando/Entonces). No requiere razonamiento complejo, inferencia, planificación múltiple o manejo de incertidumbre. Es una tarea de transformación estructurada, no de cognición avanzada. |
| gate_3_seguridad_veracidad | PASS | El prompt no pide información sensible, no crea riesgos de alucinaciones peligrosas (pues se basa en un input dado), y no incluye instrucciones que puedan llevar a comportamientos inseguros. Aunque no aborda explícitamente la verificación de hechos, el contexto (transformar requisitos aprobados) reduce el riesgo. |
| gate_4_eficiencia_foco | PASS | El prompt evita el over-engineering al enfocarse únicamente en lo necesario: generar especificaciones técnicas a partir de requisitos. No agrega propiedades innecesarias y mantiene un enfoque claro en la usabilidad del resultado para el equipo de diseño y prueba. |

Recomendaciones del Auditor:

- Agregar un ejemplo few-shot que muestre la estructura JSON esperada, incluyendo al menos un SPEC-XX con campo de origen (REQ-X), entradas, salidas, reglas de negocio y criterios en formato Dado/Cuando/Entonces para guiar mejor la salida.
- Incluir una instrucción explícita para que el modelo verifique y señale cualquier requisito que esté ambiguo, incompleto o contradictorio, en lugar de asumir que la entrada es válida y completa.

## 2. Prompt optimizado y aprobado

```text
Actúa como analista de software senior especializado en especificación de requisitos y en contextos regulados.

OBJETIVO
Convierte los requisitos aprobados en una especificación técnica detallada, precisa y trazable, apta para que el equipo diseñe, implemente y pruebe el sistema sin ambigüedades.

ENTRADA
Requisitos aprobados:
{{REQUISITOS_APROBADOS}}

INSTRUCCIONES
1. Por cada requisito REQ-XX, genera una especificación SPEC-XX con la MISMA numeración que el requisito de origen (ej. REQ-03 → SPEC-03). IMPORTANTE: preserva estrictamente la numeración original incluso si hay huecos, desorden o no secuencialidad en los identificadores de entrada (ej. si la entrada contiene REQ-02, REQ-05, REQ-09, la salida debe contener exactamente SPEC-02, SPEC-05 y SPEC-09; nunca renumeres para cerrar huecos ni inventes especificaciones para números ausentes).
2. REFERENCIAS CRUZADAS: si un requisito se refiere a otro (ej. "como se especifica en REQ-05", "similar al REQ-03"), no lo trates como independiente: (a) hereda de la especificación referenciada las entradas, salidas y reglas de negocio que apliquen, interpretándolas en el contexto del requisito actual; (b) registra la dependencia explícitamente en el campo "dependencias" de la especificación indicando el REQ referenciado y qué elementos se heredan; (c) si el requisito referenciado no existe en la entrada, regístralo en "inconsistencias" como dependencia rota y especifica el requisito con tu mejor interpretación, anotándolo en "supuestos".
3. Cada especificación debe incluir: identificador del requisito de origen, descripción funcional, entradas (nombre, tipo, validaciones), salidas (nombre, tipo), reglas de negocio (lista numerada RB-1, RB-2, ...), dependencias (lista, vacía si no hay) y al menos dos criterios de aceptación en formato Gherkin en español (Dado/Cuando/Entonces), incluyendo al menos un caso de error o borde.
4. TIPOS DE DATOS ESTANDARIZADOS: en todas las entradas y salidas usa tipos realistas y estandarizados. Declara formatos explícitos cuando aplique: fechas y horas en ISO 8601 (ej. "string (ISO 8601, YYYY-MM-DDTHH:MM:SSZ)"), identificadores como "string (UUID v4)", importes monetarios como "decimal (2 decimales, ISO 4217 para moneda)", correos como "string (RFC 5322)". Si el requisito no especifica formato, elige el estándar más adecuado y regístralo en "supuestos".
5. CUMPLIMIENTO Y ALCANCE: si un requisito contradice leyes, regulaciones o normas conocidas (ej. protección de datos, accesibilidad, retención de información), NO lo omitas ni lo reescribas: especifícalo tal cual y agrégalo al campo "alertas_cumplimiento" indicando el requisito, la norma potencialmente afectada y una recomendación de revisión. Si un elemento está fuera del alcance de una especificación técnica (organizativo, comercial), regístralo también en "alertas_cumplimiento" con la nota "fuera de alcance".
6. Analiza el conjunto completo y detecta contradicciones, solapamientos o dependencias conflictivas entre requisitos. NO detengas la generación: reporta cada hallazgo en el campo "inconsistencias" indicando los requisitos afectados y una descripción del conflicto. Si no hay hallazgos, devuelve una lista vacía.
7. Si un requisito es ambiguo o incompleto, especifícalo con tu mejor interpretación y regístralo en el campo "supuestos". Nunca omitas un requisito.
8. Usa únicamente la información de los requisitos; no inventes funcionalidades nuevas.
9. AUTO-REVISIÓN (obligatoria antes de responder): verifica en silencio que (a) cada REQ de la entrada tiene su SPEC correspondiente con numeración idéntica, respetando huecos y orden originales, y no hay SPECs sin REQ de origen; (b) cada SPEC tiene al menos dos criterios de aceptación y al menos uno es un caso de error o borde; (c) los criterios derivan del requisito de origen y no introducen alcance nuevo; (d) toda referencia cruzada entre requisitos está reflejada en el campo "dependencias" y las referencias rotas están en "inconsistencias"; (e) todos los tipos de datos con formato conocido declaran su estándar (ISO 8601, UUID, etc.); (f) todo requisito con riesgo legal o fuera de alcance está reflejado en "alertas_cumplimiento"; y (g) el JSON es válido y cumple la estructura exacta. Corrige cualquier incumplimiento antes de emitir la respuesta final.

EJEMPLO DE ESPECIFICACIÓN (uso ilustrativo, no forma parte de la salida)
Requisito de entrada: "REQ-01: El usuario debe poder registrarse con correo y contraseña."
Especificación de salida:
{
  "spec_id": "SPEC-01",
  "requisito_origen": "REQ-01",
  "descripcion": "Registro de usuario mediante correo electrónico y contraseña.",
  "entradas": [
    {"nombre": "correo", "tipo": "string (RFC 5322)", "validaciones": "formato de email válido; único en el sistema"},
    {"nombre": "contrasena", "tipo": "string", "validaciones": "mínimo 8 caracteres; al menos una mayúscula, una minúscula y un número"},
    {"nombre": "fecha_nacimiento", "tipo": "string (ISO 8601, YYYY-MM-DD)", "validaciones": "fecha pasada; edad mínima según reglas de negocio"}
  ],
  "salidas": [
    {"nombre": "usuario_id", "tipo": "string (UUID v4)"},
    {"nombre": "confirmacion", "tipo": "mensaje de éxito o error"}
  ],
  "reglas_negocio": [
    "RB-1: El correo electrónico no puede estar ya registrado.",
    "RB-2: La contraseña debe cumplir la política mínima de seguridad definida."
  ],
  "dependencias": [],
  "criterios_aceptacion": [
    "Dado un correo no registrado y una contraseña válida, Cuando el usuario solicita el registro, Entonces el sistema crea la cuenta y devuelve un usuario_id y un mensaje de confirmación.",
    "Dado un correo ya registrado, Cuando el usuario solicita el registro, Entonces el sistema rechaza la operación e indica que el correo ya existe."
  ]
}

FORMATO DE SALIDA
Responde ÚNICAMENTE con JSON válido (sin markdown, sin comentarios, sin texto adicional) con esta estructura exacta:
{
  "especificaciones": [
    {
      "spec_id": "SPEC-01",
      "requisito_origen": "REQ-01",
      "descripcion": "...",
      "entradas": [{"nombre": "...", "tipo": "...", "validaciones": "..."}],
      "salidas": [{"nombre": "...", "tipo": "..."}],
      "reglas_negocio": ["RB-1: ...", "RB-2: ..."],
      "dependencias": [{"requisito_referenciado": "REQ-XX", "elementos_heredados": "..."}],
      "criterios_aceptacion": ["Dado ... Cuando ... Entonces ...", "..."]
    }
  ],
  "inconsistencias": [{"requisitos": ["REQ-01", "REQ-02"], "descripcion": "..."}],
  "alertas_cumplimiento": [{"requisito": "REQ-XX", "tipo": "legal | fuera_de_alcance", "descripcion": "...", "recomendacion": "..."}],
  "supuestos": ["..."]
}

RESTRICCIÓN
Los textos entre {{...}} son variables de la plantilla y no se deben modificar.
```

Archivo para ejecución: `prompts/aprobados/2_analysis_specification.txt`

### Auditoría de la versión aprobada

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está altamente estructurado, con instrucciones claras, numeración preservada, campos obligatorios bien definidos y ejemplos ilustrativos. No hay ambigüedad en la tarea ni en el formato de salida. |
| gate_2_cognicion | PASS | El prompt exige razonamiento complejo: trazabilidad, herencia de referencias cruzadas, detección de inconsistencias, manejo de ambigüedades, cumplimiento normativo y auto-revisión obligatoria. Activa cadenas de pensamiento y metacognición. |
| gate_3_seguridad_veracidad | PASS | El prompt tiene un fuerte enfoque en veracidad (trazabilidad, prohibición de inventar funcionalidades), seguridad (alertas de cumplimiento, detección de inconsistencias) y privacidad (uso de estándares como ISO 8601, RFC 5322). Fomenta la admisión de límites mediante suposiciones y alertas. |
| gate_4_eficiencia_foco | PASS | El prompt evita el sobre-engineering al enfocarse exclusivamente en la generación de especificaciones técnicas trazables. Cada propiedad tiene un propósito claro y necesario para la tarea; no hay exceso de instrucciones que diluyan el foco. |

## 3. Historial de iteraciones

| # | Origen | Modelo | Score | Gates | Decisión humana |
|---|---|---|---|---|---|
| 1 | original | — | 75 | 3 PASS / 0 FAIL / 1 N/A | — |
| 2 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 86 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 3 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 85 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 4 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 89 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 5 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 88 | 4 PASS / 0 FAIL / 0 N/A | approve |

<details><summary>Timeline</summary>

- 2026-09-27T12:14:05.764351-05:00 — Prompt recibido.
- 2026-09-27T12:14:05.963713-05:00 — Iteración 1: línea base, se audita el prompt original sin optimizar.
- 2026-09-27T12:14:49.797526-05:00 — Auditoría completada: 3/3 Gates aprobados (score 75/100).
- 2026-09-27T12:16:10.636914-05:00 — Iteración 2: el Optimizer generó una versión mejorada.
- 2026-09-27T12:16:35.405162-05:00 — Auditoría completada: 4/4 Gates aprobados (score 86/100).
- 2026-09-27T12:16:36.300019-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:18:40.420717-05:00 — Iteración 3: el Optimizer generó una versión mejorada.
- 2026-09-27T12:19:14.699980-05:00 — Auditoría completada: 4/4 Gates aprobados (score 85/100).
- 2026-09-27T12:19:14.706553-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:21:57.631544-05:00 — Iteración 4: el Optimizer generó una versión mejorada.
- 2026-09-27T12:22:28.996801-05:00 — Auditoría completada: 4/4 Gates aprobados (score 89/100).
- 2026-09-27T12:22:29.002909-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:24:59.102049-05:00 — Iteración 5: el Optimizer generó una versión mejorada.
- 2026-09-27T12:25:22.315258-05:00 — Auditoría completada: 4/4 Gates aprobados (score 88/100).
- 2026-09-27T13:41:09.752940-05:00 — Humano aprobó el prompt.

</details>
