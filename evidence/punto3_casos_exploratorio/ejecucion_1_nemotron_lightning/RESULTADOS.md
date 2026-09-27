# Punto 3 — Casos mínimos de prueba (Componente 1, sección 4.4)

> Archivo generado por `scripts/casos_requisitos.py informe` a partir de los JSON de
> `corridas/`. No editar a mano: la revisión humana está en `REVISION_MANUAL.md`.

## Condiciones de ejecución

- Ejecutado: 2026-09-27T15:34:48.326067+00:00 (UTC) contra `http://localhost:8000`
- Commit: `ecfeff46b2`
- Repeticiones por caso (A, B, C): 3
- Evaluador: `nvidia/nemotron-3.5-lightning-30b-a3b` · Mejorador: `moonshotai/kimi-k3`
- NVIDIA_BASE_URL: `https://integrate.api.nvidia.com/v1`
- LLM_TIMEOUT_SECONDS: `180`
- LLM_MAX_RETRIES: `2`
- temperatura: `no se envía: valor por defecto de cada modelo en NVIDIA`
- Fórmula: Requirements Quality Score = promedio de los 10 criterios (1-10) × 10; alta calidad = ≥ 80 y ningún criterio < 6.

## Resumen

| Caso | Tipo | Corridas que cumplen | Puntaje original | Puntaje mejorado | Delta | Latencia total (s) |
|---|---|---|---|---|---|---|
| A | Requisito claro | **2/3** | 86.0 ± 5.7 | — | — | 176.9 ± 191.4 |
| B | Requisito ambiguo | **0/3** | 32.7 ± 5.7 | 30.5 ± 4.9 | -4.5 ± 0.7 | 191.7 ± 184.1 |
| C | Requisito contradictorio o incompleto | **1/2** | 30.0 ± 2.8 | 19.0 | -9.0 | 393.8 ± 58.6 |
| D | Requisito ingresado por voz | sin ejecutar | — | — | — | — |

Valores: media ± desviación estándar entre corridas.

## Caso A — Requisito claro

**Esperado (enunciado):** Debe reconocer alta calidad y evitar modificaciones innecesarias.

**Entrada:**

```text
REQ-AUT-03 (origen: política de seguridad de la tienda en línea). El sistema deberá bloquear durante 15 minutos la cuenta de un cliente registrado cuando se produzcan 5 intentos fallidos consecutivos de inicio de sesión dentro de un periodo de 10 minutos.
Criterios de aceptación:
1. Dado un cliente con 4 intentos fallidos consecutivos en los últimos 10 minutos, cuando falla el quinto intento, entonces la cuenta queda bloqueada y el sistema rechaza todo inicio de sesión de esa cuenta durante 15 minutos.
2. Dado una cuenta bloqueada hace 15 minutos o más, cuando el cliente ingresa su contraseña correcta, entonces el inicio de sesión es exitoso.
3. Dado un cliente con 4 intentos fallidos consecutivos, cuando inicia sesión correctamente, entonces el contador de intentos fallidos vuelve a 0.
```

| Verificación | Corrida 1 | Corrida 2 | Corrida 3 |
|---|---|---|---|
| **G1** El análisis terminó sin error | ❌ El Evaluador no devolvió JSON válido tras reintentar: 1 validation error for RequirementEvaluationResponse
  Invalid JSON: expected `,` or `}` at line 54 column 88 [type=json_invalid, input_value='{\n  "criteria": [\n    ...ectos por detallar."\n}', input_type=str]
    For further information visit https://errors.pydantic.dev/2.13/v/json_invalid | ✅ COMPLETED | ✅ COMPLETED |
| **G2** La evaluación del original es válida (10 criterios) | ❌ | ✅ | ✅ |
| **A1** Reconoce alta calidad (≥ 80 y ningún criterio < 6) | — | ✅ puntaje 82, mínimo 7 | ✅ puntaje 90, mínimo 9 |
| **A2** No modifica el requisito | — | ✅ omitida | ✅ omitida |
| **A3** (informativa) No hace preguntas de aclaración | — | ❌ 1 preguntas | ✅ 0 preguntas |
| **A4** (informativa) No marca términos ambiguos | — | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 1 — análisis <code>32fb1b60-f208-4303-aaf4-cc324b48d8c4</code></summary>

</details>

<details><summary>Corrida 2 — análisis <code>017f0278-2eb0-4fa0-8047-923bbab0bd3c</code></summary>

**Diagnóstico:** El requisito REQ-AUT-03 está bien definido, es claro, específico, atómico y verificable. Cumple con los criterios de aceptación entregados y es consistente con el contexto del proyecto. Los únicos aspectos a mejorar son la definición opcional del comportamiento del contador de intentos tras el bloqueo, lo cual no afecta la implementación básica pero sí la exhaustividad del diseño.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 8 | — | El requisito especifica claramente la acción (bloquear la cuenta) y las condiciones (5 intentos fallidos consecutivos en un periodo de 10 minutos). El texto es comprensible sin interpretaciones contradictorias. |
| especificidad | 7 | — | Expresa el comportamiento, la condición (5 intentos fallidos) y el resultado (bloqueo 15 min) con precisión. Sin embargo, no define qué ocurre con los intentos previos si el bloqueo se dispara, dejando un pequeño vacio de precisión sobre el estado del contador post-bloqueo. |
| atomicidad | 8 | — | El requisito es atómico: expresa una sola condición de seguridad y una única acción de bloqueo sin mezclar requisitos independientes. |
| completitud | 7 | — | Incluye la información necesaria para comprender y desarrollar el comportamiento: cantidad de intentos, periodo de tiempo y duración del bloqueo. No especifica qué sucede con el contador de intentos tras el bloqueo (si se reinicia o se mantiene), pero el requisito básico está completo. |
| consistencia | 9 | — | El requisito es consistente con el contexto del proyecto (política de seguridad de tienda en línea). No contradice los criterios de aceptación entregados (bloqueo, rechazo de sesión, reinicio del contador tras éxito). Internamente es coherente. |
| factibilidad | 8 | — | Puede implementarse razonablemente con los sistemas de autenticación actuales. No requiere tecnologías imposibles o infraestructura inexistente. |
| verificabilidad | 9 | — | Permite comprobar objetivamente si el requisito se cumple: se pueden contar los intentos fallidos en 10 min, verificar si el bloqueo se activa a los 5 intentos y medir el tiempo de 15 min de bloqueo. |
| trazabilidad | 8 | — | El requisito tiene un identificador único (REQ-AUT-03) y declara el origen (política de seguridad de la tienda en línea), lo que permite relacionarlo con diseño, código y pruebas. Cumple con los estándares de trazabilidad basicos. |
| ausencia_ambiguedad | 8 | — | No hay términos subjetivos o vagos como "rápido" o "fácil". Los tiempos (15 minutos, 10 minutos, 5 intentos) son precisos y numéricos. El lenguaje es técnico y objetivo. |
| criterios_aceptacion | 10 | — | Los criterios de aceptación están explícitamente definidos con condiciones Dado/Cuando/Entonces y resultados medibles (bloqueo, rechazo de sesión, reinicio del contador). Permiten determinar de forma verificable cuándo el requisito está satisfecho. |

**Preguntas:**

- ¿Se reinicia el contador de intentos fallidos a 0 después de que la cuenta desbloquea, o se mantiene el conteo actual para futuros intentos?

</details>

<details><summary>Corrida 3 — análisis <code>2f3047fb-aeb4-4235-805b-94811f73cc2e</code></summary>

**Diagnóstico:** El requisito cumple plenamente con los 10 criterios ISO/IEC/IEEE 29148. Está claro, específico, atómico, completo, consistente, factible, verificable, trazable, ambiguo-gratis y con criterios de aceptación medibles.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 9 | — | El requisito especifica claramente la condición (5 intentos fallidos consecutivos en 10 minutos), la acción (bloqueo de 15 minutos) y al actor (cliente registrado). El texto es directo y sin interpretaciones contradictorias. |
| especificidad | 9 | — | Expresa con precisión el comportamiento: cantidad de intentos (5), ventana temporal (10 minutos), duración del bloqueo (15 minutos) y la condición de bloqueo tras intentos fallidos consecutivos. Los criterios de aceptación afirman el comportamiento exacto. |
| atomicidad | 9 | — | El requisito está expresado como una única condición compuesta por umbral y ventana temporal, pero cumple la regla de atomicidad al no mezclar tipos de comportamiento independientes. |
| completitud | 9 | — | El requisito incluye toda la información necesaria: umbral de intentos, ventana temporal, duración del bloqueo y comportamiento posterior. No falta ningún dato esencial para su desarrollo. |
| consistencia | 9 | — | El requisito es interno y no contradice a los tres criterios de aceptación proporcionados. No hay conflictos con reglas conocidas del proyecto. |
| factibilidad | 9 | — | El bloqueo temporal de 15 minutos y el conteo de intentos son características técnicas estándar y fácilmente implementables en cualquier sistema de autenticación. |
| verificabilidad | 9 | — | Permite comprobar objetivamente si se cumplen las condiciones: contar intentos fallidos dentro de ventana de 10 minutos, verificar bloqueo activo y contar tiempo desde bloqueo hasta liberación. |
| trazabilidad | 9 | — | El identificador REQ-AUT-03 vincula el requisito con la política de seguridad y permite relacionarlo con diseño, código y pruebas. Los criterios de aceptación facilitan su trazabilidad hacia casos de prueba. |
| ausencia_ambiguedad | 9 | — | No hay términos subjetivos ni vagos como "rápido" o "fácil". Todos los valores (5 intentos, 10 minutos, 15 minutos) son cuantificables y precisos. |
| criterios_aceptacion | 9 | — | Los tres criterios de aceptación están bien definidos con estructura Dado/Cuando/Entonces y condiciones medibles claras. Permiten determinar de forma verificable cuándo el requisito está satisfecho. |

</details>

## Caso B — Requisito ambiguo

**Esperado (enunciado):** Debe detectar ambigüedad, formular preguntas y mejorar el requisito.

**Entrada:**

```text
El sistema debe permitir a los clientes buscar productos de forma rápida y sencilla, mostrando resultados relevantes.
```

**Respuestas del stakeholder usadas al aclarar:**

```text
La búsqueda se hace desde un único cuadro de texto visible en la parte superior de todas las páginas y busca por nombre, marca y categoría del producto. Los resultados deben mostrarse en máximo 2 segundos con un catálogo de hasta 20000 productos. 'Relevantes' significa que el texto buscado aparece en el nombre, la marca o la categoría; primero se muestran las coincidencias en el nombre y luego las demás, ordenadas por unidades vendidas. 'Sencilla' significa que no hace falta iniciar sesión ni usar filtros para buscar. Aplica a clientes registrados e invitados.
```

| Verificación | Corrida 1 | Corrida 2 | Corrida 3 |
|---|---|---|---|
| **G1** El análisis terminó sin error | ❌ Error del Mejorador al llamar a NVIDIA: NVIDIA respondió 200 pero 'message.content' está vacío. | ✅ COMPLETED | ✅ COMPLETED |
| **G2** La evaluación del original es válida (10 criterios) | ✅ | ✅ | ✅ |
| **B1** Detecta los términos vagos (rápida / sencilla / relevantes) | ✅ rápido, sencilla, relevantes | ✅ rápido, sencilla, relevantes | ✅ rápido, sencilla, relevantes |
| **B2** Formula preguntas de aclaración | ✅ 5 preguntas | ✅ 5 preguntas | ✅ 4 preguntas |
| **B3** Mejora el requisito (versión mejorada con delta > 0) | ❌ delta None | ❌ delta -4 | ❌ delta -5 |
| **B4** No inventa valores numéricos | ✅ ninguno | ✅ ninguno | ✅ ninguno |
| **B5** Con las respuestas del stakeholder el requisito final supera al original | — | ✅ original 31 → final tras aclarar 73 | — |
| **B6** (informativa) Tras aclarar quedan menos datos por definir | — | ✅ 5 → 0 pendientes | — |
| **B7** Tras aclarar no inventa valores numéricos | — | ✅ ninguno | — |

<details><summary>Corrida 1 — análisis <code>05c212f3-e247-4802-9c5a-c5fdb7e3fa77</code></summary>

**Diagnóstico:** El requisito es compuesto y poco específico: mezcla búsqueda funcional con criterios de usabilidad, usa términos vagos ('rápido', 'sencilla', 'relevantes') y falta definición de filtros, actor y criterio de relevancia. No tiene criterios de aceptación medibles, lo que dificulta su desarrollo y prueba. Se recomienda descomponer el requisito, definir criterios observables y asignar un identificador único.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | — | El requisito expresa la intención de 'mostrar resultados relevantes' pero no define qué determina la relevancia ni el criterio de ordenamiento, lo que deja abierta la interpretación sobre qué resultados se deben mostrar primero. |
| especificidad | 2 | — | Los términos 'rápido' y 'sencilla' son vagos y no expresan comportamiento, condición o resultado con la precisión necesaria para su desarrollo y prueba. |
| atomicidad | 3 | — | El requisito mezcla al menos dos conceptos independientes: la capacidad de búsqueda y la usabilidad/ simplicidad de la misma. No está claro si la 'sencillez' es un requisito funcional o una restricción de usabilidad. |
| completitud | 2 | — | Falta información esencial para desarrollar y probar el comportamiento: qué campos o filtros están disponibles en la búsqueda, qué actor(es) participan (cliente invitado vs. registrado) y qué se entiende por 'resultados relevantes'. |
| consistencia | 5 | — | No hay contradicción interna evidente en el texto del requisito. No se dispone de otros requisitos del proyecto para verificar consistencia externa, pero el propio texto no choca consigo mismo. |
| factibilidad | 5 | — | Desde el texto no se puede determinar factibilidad técnicamente, pero la implementación de una funcionalidad de búsqueda es técneaamente factible en una tienda en línea standard. |
| verificabilidad | 2 | — | No es posible comprobar objetivamente si el requisito se cumple porque 'rápido', 'sencilla' y 'relevantes' no tienen criterios de medición definidos. No hay condiciones observables. |
| trazabilidad | 3 | — | El requisito no incluye un identificador único ni declara el origen de la necesidad (p. ej., como requisito de usuario o historia de usuario). No permite relacionarlo directamente con diseño, código o pruebas sin agregar metadatos. |
| ausencia_ambiguedad | 2 | — | Se detectan términos subjetivos o vagos: 'rápido', 'sencilla' y 'relevantes'. ningunodefine un tiempo, un número de pasos o una regla de ordenamiento medible. |
| criterios_aceptacion | 1 | — | El requisito no incluye criterios de aceptación explícitos ni condiciones medibles que permitan determinar verificablemente cuándo está satisfecho. No hay condiciones Dado/Cuando/Entonces ni valores umbral. |

**Preguntas:**

- ¿Qué campos o filtros deben estar disponibles en el campo de búsqueda (p. ej., nombre, categoría, rango de precio, marca)?
- ¿Se dirige el requisito a clientes invitados, usuarios registrados o ambos?
- ¿Cuál es el criterio de 'relevancia' para ordenar los resultados (p. ej., coincidencia exacta, popularidad, precio, fecha de publicación)?
- ¿Cuál es el tiempo máximo de respuesta aceptable para mostrar los resultados de búsqueda?
- ¿Qué métrica de usabilidad se espera para considerar que la búsqueda es 'sencilla' (p. ej., máximo 3 clics para encontrar el producto)?

</details>

<details><summary>Corrida 2 — análisis <code>a4711797-feb3-4dd7-a853-0311ea96a84a</code></summary>

**Diagnóstico:** El requisito es compuesto y vague al mezclar búsqueda, usabilidad y exhibición de resultados sin definiciones técnicas. Términos como rápido, sencilla y relevantes son subjetivos y imposibles de verificar. Faltan campos de búsqueda, criterios de relevancia, tiempos de respuesta y definición de actores. Se necesita desglosar en requisitos atómicos y agregar criterios de aceptación medibles.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | 3 | El término "rápido y sencilla" es subjetivo y permite interpretaciones contradictorias sobre qué velocidad o nivel de esfuerzo se espera. |
| especificidad | 2 | 2 | No se expresa el comportamiento de búsqueda: qué campos se pueden buscar (palabra clave, categoría, marca), qué filtros están disponibles ni cómo se define "resultados relevantes". |
| atomicidad | 3 | 1 | El requisito mezcla tres ideas independientes: habilitar la búsqueda, la facilidad de uso y el mostrado de resultados. No están separados. |
| completitud | 2 | 2 | Falta información esencial: actores involucrados (cliente vs. invitado), condiciones de activación, valores de búsqueda y reglas de relevancia. |
| consistencia | 6 | 5 | No hay contradicción interna visible, pero el uso de "sencilla" puede chocar con futuros requisitos de filtros avanzados o búsquedas complejas que no sean "sencillas". No se provee contexto externo que contradiga el texto. |
| factibilidad | 6 | 5 | Técnicamente factible, pero depende de definiciones sin especificar de "rápido" y "relevantes". Sin criterios claros, la implementación puede no cumplir las expectativas. |
| verificabilidad | 2 | 2 | No hay forma objetiva de comprobar si la búsqueda es "rápida" o "sencilla". No se definen tiempos, pasos ni criterios de resultado medibles. |
| trazabilidad | 4 | 3 | No hay identificador único ni declaración de necesidad/origen que permita relacionar el requisito con diseño, código o pruebas. Es un requisito suelto. |
| ausencia_ambiguedad | 2 | 2 | Términos subjetivos detectados: "rápido", "sencilla", "relevantes". No definen umbrales, tiempos ni criterios de medición. |
| criterios_aceptacion | 1 | 2 | No hay criterios de aceptación explícitos ni condiciones verificables de cuándo el requisito está satisfecho. |

**Preguntas:**

- ¿Qué campos y filtros deben estar disponibles en la búsqueda (por ejemplo, palabra clave, categoría, marca, rango de precio)?
- ¿Cómo se define "resultado relevante" para el negocio (por ejemplo, coincidencia de nombre, popularidad, stock disponible)?
- ¿Cuál es el tiempo máximo de respuesta aceptable para la operación de búsqueda?
- ¿El requisito se aplica a clientes invitados, registrados o ambos?
- ¿Se requiere mostrar algún mensaje o estado cuando no hay resultados?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá permitir a los usuarios (clientes registrados e invitados) buscar productos del catálogo ingresando [POR DEFINIR: campos de búsqueda soportados, p. ej. palabra clave, categoría, marca] y [POR DEFINIR: filtros disponibles].
REQ-2: El sistema deberá mostrar los resultados de búsqueda en un tiempo máximo de [POR DEFINIR: tiempo máximo de respuesta en segundos] desde que el usuario confirma la búsqueda.
REQ-3: El sistema deberá ordenar los resultados según [POR DEFINIR: criterio de relevancia, p. ej. coincidencia con el término buscado, disponibilidad, popularidad].
REQ-4: El sistema deberá permitir al usuario completar una búsqueda en un máximo de [POR DEFINIR: número máximo de pasos o interacciones para realizar una búsqueda].
```

**Criterios de aceptación:**

- Dado un usuario (registrado o invitado) en la tienda, cuando ingresa un término en [POR DEFINIR: campos de búsqueda soportados] y confirma la búsqueda, entonces el sistema muestra los productos del catálogo que coinciden según [POR DEFINIR: criterio de relevancia].
- Dado un usuario que confirma una búsqueda, cuando el sistema procesa la consulta, entonces los resultados se muestran en un tiempo menor o igual a [POR DEFINIR: tiempo máximo de respuesta en segundos].
- Dado que existen productos coincidentes, cuando se muestran los resultados, entonces están ordenados según [POR DEFINIR: criterio de relevancia].
- Dado un usuario en la tienda, cuando desea buscar un producto, entonces puede completar la búsqueda en un máximo de [POR DEFINIR: número máximo de pasos o interacciones].

**Tras responder las preguntas** (análisis `16e48201-b16d-4832-8865-a75b070cb6e3`): estado COMPLETED, puntaje original 47, mejorado 73.

```text
REQ-1: El cliente (registrado o invitado) podrá buscar productos ingresando texto en un único cuadro de búsqueda visible en la parte superior de todas las páginas, sin necesidad de iniciar sesión ni aplicar filtros.
REQ-2: El sistema deberá buscar el texto ingresado en el nombre, la marca y la categoría de los productos del catálogo.
REQ-3: El sistema deberá mostrar los resultados de la búsqueda en un tiempo máximo de 2 segundos con un catálogo de hasta 20.000 productos.
REQ-4: El sistema deberá ordenar los resultados mostrando primero los productos cuyo nombre coincide con el texto buscado, y luego los que coinciden en marca o categoría; dentro de cada grupo, los productos se ordenarán por unidades vendidas de mayor a menor.
```

</details>

<details><summary>Corrida 3 — análisis <code>e2366eb6-5995-40b8-8216-77f6b9a672fc</code></summary>

**Diagnóstico:** El requisito define una intención de usuario pero incumple los criterios esenciales de especificidad, verificabilidad y criterios de aceptación por el uso de términos vagos y falta de datos medibles. Es necesario definir umbrales de tiempo, criterios de relevancia y condiciones de entrada para pasar a un desarrollo guiado por pruebas.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | 3 | El requisito expresa el objetivo general pero utiliza términos no cuantificados: 'rápido y sencilla' generan interpretaciones contradictorias sobre qué tan rápido o cuántos pasos se consideran sencillos. No hay definición de la experiencia de búsqueda esperada. |
| especificidad | 3 | 3 | El requisito describe un comportamiento deseado pero no especifica la lógica de filtrado, ordenamiento o qué se entiende por 'resultados relevantes'. No define qué productos se muestran ni bajo qué condiciones. |
| atomicidad | 5 | 5 | El texto combina dos intenciones: (1) permitir la búsqueda de productos y (2) mostrar resultados relevantes. No están claramente separados en sub-requisitos independientes, pero la unión es estrechamente relacionada en una misma funcionalidad de usuario. |
| completitud | 3 | 2 | Falta información crítica para desarrollar y probar: no se define el actor que ejecuta la búsqueda, las condiciones de entrada (palabras clave, filtros), ni el resultado esperado. No hay descripción de la interfaz ni de los datos de catálogo involucrados. |
| consistencia | 6 | 5 | No hay contradicción explícita con otros requisitos entregados. El texto es autosuficiente dentro de la funcionalidad de búsqueda, pero carece de alineación con reglas de catálogo o flujos de compra no definidos en este fragmento. |
| factibilidad | 6 | 5 | Desde una perspectiva técnica, permitir búsquedas de productos es factible. Sin embargo, la falta de especificidad sobre 'rápido' y 'relevantes' dificulta estimar el esfuerzo de ingeniería necesario para cumplir con expectativas no definidas. |
| verificabilidad | 3 | 2 | No hay condiciones medibles que permitan comprobar objetivamente si el requisito se cumple. No se pueden probar tiempos, relevancia ni simplicidad sin definiciones previas. No se especifica qué se observa ni cómo se mide. |
| trazabilidad | 5 | 5 | El requisito no incluye un identificador único ni declara explícitamente la necesidad o el actor de origen que permita relacionarlo con diseño, código y pruebas. No hay mención a historias de usuario, épicos o etiquetas de trazabilidad. |
| ausencia_ambiguedad | 3 | 2 | Se detectan términos subjetivos/vagos: 'rápido', 'sencilla' y 'relevantes'. Estos términos no tienen significado medible y su interpretación varía según el stakeholder. No están marcados como [POR DEFINIR] en el texto. |
| criterios_aceptacion | 2 | 2 | El requisito no incluye criterios de aceptación explícitos ni condiciones medibles de las que derivarlos. No hay definición de cuándo la búsqueda está 'satisfecha' ni qué resultados se consideran relevantes. |

**Preguntas:**

- ¿Qué entiende el stakeholder por 'rápido' en términos de tiempo de respuesta o número de pasos de usuario?
- ¿Cómo se determina qué resultado se considera 'relevante' para el cliente? ¿Hay filtros o ranking implícitos?
- ¿La funcionalidad de búsqueda aplica tanto a clientes invitados como a los registrados, o hay diferencias en el comportamiento?
- ¿Se deben especificar filtros por defecto o el usuario debe ingresarlos manualmente?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá permitir a un cliente (invitado o registrado) buscar productos del catálogo ingresando [POR DEFINIR: tipos de entrada aceptados, p. ej., texto libre, campos específicos] y, opcionalmente, aplicando [POR DEFINIR: filtros disponibles, p. ej., categoría, marca, talla, rango de precio].
REQ-2: El sistema deberá mostrar los resultados de la búsqueda en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta, p. ej., 2 s], presentando [POR DEFINIR: cantidad máxima de resultados por página y formato de presentación].
REQ-3: Los resultados mostrados deberán ordenarse según [POR DEFINIR: criterio de relevancia o ranking, p. ej., coincidencia con la palabra clave, popularidad, precio], de modo que cada resultado cumpla [POR DEFINIR: condición mínima que hace a un producto relevante para la búsqueda].
```

**Criterios de aceptación:**

- Dado un cliente (invitado o registrado) en la tienda, cuando ingrese [POR DEFINIR: tipo de entrada aceptada] y solicite la búsqueda, entonces el sistema mostrará resultados de productos del catálogo.
- Dado un cliente, cuando ejecute una búsqueda, entonces los resultados se mostrarán en un tiempo menor o igual a [POR DEFINIR: umbral de tiempo de respuesta].
- Dado un cliente que aplica [POR DEFINIR: filtros disponibles], cuando ejecute la búsqueda, entonces los resultados respetarán los filtros aplicados.
- Dado un conjunto de resultados de búsqueda, cuando se muestren al cliente, entonces aparecerán ordenados según [POR DEFINIR: criterio de relevancia o ranking] y cada resultado cumplirá [POR DEFINIR: condición mínima de relevancia].
- Dado un conjunto de resultados, cuando se muestren al cliente, entonces la lista contendrá como máximo [POR DEFINIR: cantidad por página] resultados en el formato [POR DEFINIR: formato de presentación].

</details>

## Caso C — Requisito contradictorio o incompleto

**Esperado (enunciado):** Debe señalar la inconsistencia o falta de información y abstenerse de inventar datos.

**Entrada:**

```text
Los reportes de ventas deben generarse automáticamente cada día, pero solo cuando el gerente los solicite manualmente, y deben incluir los datos necesarios.
```

| Verificación | Corrida 2 | Corrida 3 |
|---|---|---|
| **G1** El análisis terminó sin error | ✅ COMPLETED | ❌ Error del Mejorador al llamar a NVIDIA: NVIDIA respondió 200 pero 'message.content' está vacío. |
| **G2** La evaluación del original es válida (10 criterios) | ✅ | ✅ |
| **C1** Detecta la contradicción (consistencia ≤ 3) | ✅ consistencia 3 | ✅ consistencia 3 |
| **C2** Señala la información faltante y pregunta | ✅ 4 faltantes, 4 preguntas | ✅ 4 faltantes, 3 preguntas |
| **C3** Deja explícito lo que falta con [POR DEFINIR] | ✅ 5 pendientes | ❌ 0 pendientes |
| **C4** No resuelve la contradicción por su cuenta (la deja pendiente) | ✅ | ❌ |
| **C5** No inventa valores numéricos | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 2 — análisis <code>49d07f7d-d8c0-44f8-b2aa-079561af7ab9</code></summary>

**Diagnóstico:** El requisito es compuesto y contradictorio al mezclar generación automática diaria con solicitud manual exclusiva. Faltan definiciones de datos, horarios y lógica de gatillo. No hay criterios de aceptación medibles. Es necesario dividir el requisito en partes atómicas y especificar condiciones concretas.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | 2 | El requisito mezcla dos condiciones contradictorias o superpuestas: 'generarse automáticamente cada día' y 'solo cuando el gerente los solicite manualmente'. Queda sin qué grado de automatización se aplica si hay solicitud manual, generando ambigüedad sobre el gatillo real. |
| especificidad | 4 | 1 | Se menciona 'datos necesarios' sin precisar qué datos ni formato. No se especifica el alcance de los datos (qué campos, rangos, filtros) ni la estructura del reporte. |
| atomicidad | 2 | 5 | El requisito es compuesto: combina la frecuencia (diaria), el gatillo (solicitud manual) y el contenido (datos necesarios). Mezcla tres comportamientos independientes en una sola oración. |
| completitud | 2 | 1 | Falta información esencial para desarrollar y probar: qué datos conforman 'los datos necesarios', con qué frecuencia exacta se ejecuta 'cada día' (hora exacta), y si la solicitud manual invalida la generación automática o es el único gatillo. |
| consistencia | 3 | 2 | Contradicción interna: 'generarse automáticamente cada día' implica un gatilo temporal recurrente, mientras que 'solo cuando el gerente los solicite manualmente' implica un gatilo humano. Los dos no pueden ser la única fuente de generación sin una lógica de combinación que no se especifica. Además, el contexto indica que los gerentes consultan reportes desde la web, lo cual sugiere una consulta bajo su criterio, no necesariamente una generación sobrerreglada. |
| factibilidad | 5 | 3 | Desde el punto de vista técnico, generar reportes diarios y bajo solicitud es factible con los sistemas actuales. No hay restricciones técnicas declaradas que lo hagan imposible. |
| verificabilidad | 2 | 1 | No hay forma objetiva de verificar si el reporte se generó 'cada día' bajo las condiciones mezcladas, ni qué datos se consideran 'necesarios'. Faltan umbrales de tiempo, condiciones lógicas y lista de campos para poder comprobar el cumplimiento. |
| trazabilidad | 4 | 2 | No se asigna un identificador único ni se declara el actor/necesidad de origen explícita. El contexto menciona que los gerentes consultan reportes desde la web, lo que permite relacionarlo con roles de usuario, pero el requisio en sí no tiene etiqueta ni origen claro. |
| ausencia_ambiguedad | 2 | 1 | Términos ambiguos detectados: 'cada día' (no especifica hora ni zona horaria), 'datos necesarios' (vago y sujeto a interpretación), 'generarse automáticamente' (no define si es bajo gatilo, schedule o evento), 'solicite manualmente' (no define canal o frecuencia máxima de solicitud). |
| criterios_aceptacion | 1 | 1 | No hay criterios de aceptación explícitos ni condiciones medibles de las que derivarlos. No se especifica cuándo el requisito está satisfecho (¿qué reportes se generaron?, ¿qué datos incluyen?, ¿bajo qué condiciones exactas?). |

**Preguntas:**

- ¿La generación diaria es automática con horario fijo, o solo se genera bajo solicitud manual del gerente?
- ¿Cuáles son exactamente los datos/campos que deben incluirse en el reporte de ventas?
- ¿El gerente solicita el reporte a través de la interfaz web, un correo electrónico o otro canal?
- ¿Se debe respetar una hora específica del día para la generación automática, o es bajo demanda continua?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá generar los reportes de ventas [POR DEFINIR: resolver contradicción entre generación automática diaria y generación exclusiva bajo solicitud manual del gerente].
REQ-2: Si la generación es diaria, el sistema deberá ejecutarla a la hora [POR DEFINIR: hora exacta y zona horaria].
REQ-3: Si la generación es bajo solicitud manual, el gerente podrá solicitar el reporte desde [POR DEFINIR: canal o mecanismo de solicitud].
REQ-4: El reporte de ventas generado deberá incluir [POR DEFINIR: lista de campos/datos que debe contener el reporte] en formato [POR DEFINIR: formato de salida del reporte].
```

**Criterios de aceptación:**

- Dado que se cumple la condición de generación [POR DEFINIR: gatillo automático diario a hora definida o solicitud manual del gerente], cuando el sistema procesa la generación, entonces el reporte de ventas queda disponible para el gerente.
- Dado que el gerente solicita un reporte, cuando accede a través de [POR DEFINIR: canal de solicitud/consulta], entonces obtiene el reporte de ventas correspondiente.
- Dado un reporte de ventas generado, cuando el gerente lo abre, entonces contiene [POR DEFINIR: lista de campos/datos obligatorios] en formato [POR DEFINIR: formato de salida].

</details>

<details><summary>Corrida 3 — análisis <code>8e6b4e22-d7b5-475a-9f18-b19e08675247</code></summary>

**Diagnóstico:** El requisito presenta contradicción interna entre generación automática y solicitud manual, usa términos vagos ('necesarios', 'automáticamente', 'solicitar manualmente') y falta definición de datos concretos. Se recomienda separar el modo de desencadenamiento y especificar los campos obligatorios y formato de salida para lograr claridad y verificabilidad.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | — | El requisito contiene una contradicción interna: 'generarse automáticamente' y 'solo cuando el gerente los solicite manualmente' son mutuamente excluyentes. El sistema no puede ser simultáneamente totalmente automático y depender de una solicitud manual para iniciar el proceso. |
| especificidad | 4 | — | Se especifica la frecuencia (diaria) y el actor (gerente), pero no qué datos concretos se consideran 'necesarios'. Queda abierto qué métricas, rangos de fechas o formatos deben incluirse. |
| atomicidad | 2 | — | El texto combina dos ideas independentes: la programación automática diaria y la condición de solicitud manual del gerente. Mezclan el modo de desencadenamiento con la frecuencia, lo que dificulta evaluarlos por separado. |
| completitud | 3 | — | Falta especificar los datos exactos que deben incluirse ('necesarios' es un término vago). No hay definición de formato, frecuencia exacta ni condiciones de error o fallback si la automatización falla. |
| consistencia | 3 | — | Contradicción entre la generación automática y la solicitud manual. Además, el contexto indica que los gerentes consultan reportes desde la web, lo cual choca con la idea de que los reportes 'deben generarse' solo bajo solicitud, sin clarificar si la web los muestra automáticamente o requiere una acción. |
| factibilidad | 6 | — | Técnicamente factible generar reportes diarios y permitir solicitudes manuales, pero la contradicción interna y la falta de definición de datos dificultan estimar el esfuerzo real. |
| verificabilidad | 3 | — | No es posible verificar objetivamente el cumplimiento porque 'necesarios' no tiene criterio medible y la contradicción entre automático y manual genera dos escenarios de prueba distintos sin definir cuál es el esperado. |
| trazabilidad | 4 | — | No hay un identificador único ni una necesidad de origen explícita declarada en el requisito. El contexto indica que los gerentes consultan reportes desde la web, lo que permite asociar el requisito a una necesidad de usuario, pero el texto no lo vincula formalmente. |
| ausencia_ambiguedad | 2 | — | Términos ambigüos: 'necesarios' (no define qué datos), 'automáticamente' (no especifica el mecanismo ni la hora del día), 'solicitar manualmente' (no define el canal ni el disparador exacto). |
| criterios_aceptacion | 2 | — | No hay criterios de aceptación explícitos ni condiciones medibles para determinar cuándo el requisito está satisfecho. 'Cada día' y 'necesarios' no son verificables sin definiciones adicionales. |

**Preguntas:**

- ¿Los reportes se generan automáticamente a una hora fija cada día, o el gerente los inicia bajo demanda? Clarificar si es uno u otro escenario, o si ambos modos deben coexistir.
- ¿Cuáles son los datos o campos mínimos que deben incluirse en los reportes de ventas? Solicitar una lista concreta de métricas, rangos de fechas y formatos.
- ¿Cómo solicita el gerente el reporte manualmente? (p. ej., botón en la web, API, correo electrónico) y qué disparador activa esa acción.

</details>
