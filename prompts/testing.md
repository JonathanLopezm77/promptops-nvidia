# Fase 5 — Testing / QA

> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación
> de prompts. No editar a mano.

| Campo | Valor |
|---|---|
| Rol | QA Engineer |
| Entrada | Requisitos + código |
| Salida esperada | Casos y suites de prueba (TEST-XX) |
| Quality Gate de la fase (SDLC) | Pass rate + cobertura + defectos |
| Variables de la plantilla | `{{CODIGO_A_PROBAR}}`, `{{REQUISITOS_Y_CRITERIOS}}` |
| Run en la plataforma | `38bf85b3-6cfe-42b2-b099-192066089fa9` |
| Estado | APPROVED |
| Modelos | Optimizer `moonshotai/kimi-k3` · Auditor `nvidia/nemotron-3-super-120b-a12b` |
| Modelo que produjo la versión aprobada | `moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración)` |
| Validación | 2026-09-27T12:14:05.760973-05:00 → aprobación 2026-09-27T13:41:21.800273-05:00 |

## Métricas (Quality Gate de prompts, sección 6.1)

| | Score | Gates | gates_score |
|---|---|---|---|
| Inicial (línea base) | 42 | 0 PASS / 3 FAIL / 1 N/A | 0.0 |
| Aprobada | 91 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| **Delta** | **+49** | | |

Iteraciones de optimización: 2 (1 automáticas, 0 humanas).

## 1. Prompt inicial

```text
Actúa como ingeniero de QA. Genera las pruebas para verificar que el código cumple los requisitos.

Requisitos y criterios de aceptación:
{{REQUISITOS_Y_CRITERIOS}}

Código a probar:
{{CODIGO_A_PROBAR}}

Escribe casos de prueba y una suite automatizada. Cada caso debe tener un ID TEST-XX, indicar qué REQ o SPEC verifica, los pasos, los datos y el resultado esperado. Incluye casos normales, de borde y de error. Al final di qué requisitos quedaron cubiertos y cuáles no, y reporta los defectos que encuentres.

No modifiques las variables {{...}} de la plantilla.
```

### Auditoría inicial (línea base)

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | FAIL | El prompt carece de estructura clara y objetivos específicos. No define rol, formato de salida, ni restricciones explícitas. Omite demonstrations y presenta lógica estructural y contextual débiles. |
| gate_2_cognicion | NO_APLICA | La tarea descrita es de generación de artefactos (casos de prueba), no de razonamiento complejo o resolución de problemas que requieran cadena de pensamiento, metacognición o uso de herramientas externas. |
| gate_3_seguridad_veracidad | FAIL | El prompt falla críticamente en veracidad y confiabilidad: no obliga a admitir límites cuando los requisitos o código son ambiguos, y no incluye mecanismos para detectar alucinaciones en los casos de prueba generados. |
| gate_4_eficiencia_foco | FAIL | El prompt falla en interacción y cortesía: no solicita aclaraciones cuando faltan detalles críticos, y el tono es imperativo sin considerar la ambigüedad de los inputs. |

Recomendaciones del Auditor:

- Estructura el prompt con secciones claras: rol, objetivo, formato de salida (por ejemplo, en Gherkin o código de pytest), restricciones y ejemplos de casos de prueba (few-shot).
- Añade instrucciones para que el modelo verifique que cada caso de prueba esté trazable a un requisito, admita cuando la información es insuficiente y evite inventar funcionalidades no presentes en los inputs.

## 2. Prompt optimizado y aprobado

```text
Actúa como ingeniero de QA senior especializado en verificación de requisitos.

OBJETIVO: Generar un conjunto de casos de prueba y una suite automatizada que verifiquen que el código cumple los requisitos y criterios de aceptación dados, e identificar gaps de cobertura y defectos.

ENTRADAS:
- Requisitos y criterios de aceptación:
{{REQUISITOS_Y_CRITERIOS}}
- Código a probar:
{{CODIGO_A_PROBAR}}

INSTRUCCIONES:
1. Deriva los casos de prueba a partir de los requisitos (trazabilidad obligatoria), no solo del código.
2. Para cada requisito incluye al menos: un caso normal (camino feliz), un caso de borde (límites, vacíos, máximos/mínimos) y un caso de error (entradas inválidas, estados ilegales).
3. Formato obligatorio de cada caso:
   - ID: TEST-XX (numeración secuencial)
   - Requisito(s) que verifica: REQ-XX / SPEC-XX
   - Prioridad: Alta / Media / Baja (según criticidad del requisito)
   - Precondiciones
   - Pasos numerados
   - Datos de entrada concretos
   - Resultado esperado (observable y verificable)
4. Escribe la suite automatizada en el framework más adecuado al lenguaje del código (indícalo explícitamente). Los tests automatizados deben tener nombres que referencien su ID TEST-XX y ser ejecutables sin dependencias no declaradas.
5. Si no puedes ejecutar el código, indica claramente si cada prueba pasaría según tu análisis estático y marca las que requieran ejecución real.
6. Si un requisito es ambiguo o no verificable, señálalo explícitamente y propón el criterio de aceptación que asumes.
7. Si la información es insuficiente para proceder con confianza (requisitos contradictorios, criterios de aceptación ausentes, código incompleto, lenguaje o dependencias no identificables), NO supongas: enumera primero una lista de PREGUNTAS DE ACLARACIÓN concretas y espera la respuesta antes de generar los casos. Solo procede sin preguntar cuando la información disponible permita deducir criterios razonables y explícitos.

EJEMPLOS DEL FORMATO ESPERADO (few-shot):

Ejemplo 1 (caso normal):
- ID: TEST-01
- Requisito(s): REQ-01
- Prioridad: Alta
- Precondiciones: Existe un usuario registrado con email "ana@test.com" y contraseña "Pass123!".
- Pasos:
  1. Enviar POST /login con body {"email": "ana@test.com", "password": "Pass123!"}.
  2. Leer el cuerpo de la respuesta.
- Datos de entrada: {"email": "ana@test.com", "password": "Pass123!"}.
- Resultado esperado: HTTP 200 y la respuesta contiene un campo "token" no vacío.

Ejemplo 2 (caso de error):
- ID: TEST-05
- Requisito(s): REQ-01, SPEC-02
- Prioridad: Alta
- Precondiciones: No existe ningún usuario con email "noexiste@test.com".
- Pasos:
  1. Enviar POST /login con body {"email": "noexiste@test.com", "password": "X"}.
  2. Leer código de estado y mensaje.
- Datos de entrada: {"email": "noexiste@test.com", "password": "X"}.
- Resultado esperado: HTTP 401 con mensaje "Credenciales inválidas" y sin campo "token" en la respuesta.

SALIDA (en este orden):
0. Preguntas de aclaración (solo si aplica la instrucción 7; si no aplica, omite esta sección).
A. Tabla de casos de prueba con el formato del punto 3, siguiendo el estilo de los ejemplos.
B. Suite automatizada en un bloque de código.
C. Matriz de cobertura: tabla con columnas [Requisito | TEST-XX que lo cubren | Estado: Cubierto / Parcial / No cubierto], seguida del porcentaje de cobertura.
D. Reporte de defectos: para cada defecto encontrado indica ID (DEF-XX), severidad (Crítica / Alta / Media / Baja), descripción, ubicación en el código, pasos para reproducirlo y comportamiento esperado vs. observado. Si no hay defectos, indícalo explícitamente.

No modifiques las variables {{...}} de la plantilla.
```

Archivo para ejecución: `prompts/aprobados/5_testing.txt`

### Auditoría de la versión aprobada

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado, con roles claros, objetivos definidos y formato de salida especificado. Incluye ejemplos Few-shot relevantes y mantiene coherencia interna sin contradicciones. |
| gate_2_cognicion | PASS | El prompt guía eficazmente el razonamiento complejo requerido: descompone la tarea, elimina ruido, activa conocimiento previo en QA/testing, incluye metacognición (verificación de ambigüedades) yDefine claramente cuándo hacer preguntas de aclaración. |
| gate_3_seguridad_veracidad | PASS | El prompt promueve veracidad al exigir trazabilidad, admitir límites cuando falta información y evitar suposiciones. No hay indicaciones de sesgo, y la estructura respeta normas sociales y de seguridad al no generar contenido dañino ni requerir manejo de PII. |
| gate_4_eficiencia_foco | PASS | El prompt evita over-engineering: se centra en las propiedades clave para la tarea (trazabilidad, tipos de caso, formato, suite, cobertura, reporte) y prioriza claridad y usabilidad sin sobrecargar con requisitos no esenciales. |

## 3. Historial de iteraciones

| # | Origen | Modelo | Score | Gates | Decisión humana |
|---|---|---|---|---|---|
| 1 | original | — | 42 | 0 PASS / 3 FAIL / 1 N/A | — |
| 2 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 85 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 3 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 91 | 4 PASS / 0 FAIL / 0 N/A | approve |

<details><summary>Timeline</summary>

- 2026-09-27T12:14:05.760973-05:00 — Prompt recibido.
- 2026-09-27T12:14:06.641138-05:00 — Iteración 1: línea base, se audita el prompt original sin optimizar.
- 2026-09-27T12:16:07.713334-05:00 — Auditoría completada: 0/3 Gates aprobados (score 42/100).
- 2026-09-27T12:17:12.589543-05:00 — Iteración 2: el Optimizer generó una versión mejorada.
- 2026-09-27T12:17:37.292879-05:00 — Auditoría completada: 4/4 Gates aprobados (score 85/100).
- 2026-09-27T12:17:40.582773-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:19:54.501314-05:00 — Iteración 3: el Optimizer generó una versión mejorada.
- 2026-09-27T12:20:34.855547-05:00 — Auditoría completada: 4/4 Gates aprobados (score 91/100).
- 2026-09-27T13:41:21.800273-05:00 — Humano aprobó el prompt.

</details>
