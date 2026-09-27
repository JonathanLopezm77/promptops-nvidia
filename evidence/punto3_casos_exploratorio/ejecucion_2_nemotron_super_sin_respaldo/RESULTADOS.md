# Punto 3 — Casos mínimos de prueba (Componente 1, sección 4.4)

> Archivo generado por `scripts/casos_requisitos.py informe` a partir de los JSON de
> `corridas/`. No editar a mano: la revisión humana está en `REVISION_MANUAL.md`.

## Condiciones de ejecución

- Ejecutado: 2026-09-27T15:52:44.330869+00:00 (UTC) contra `http://localhost:8000`
- Commit: `6da00042cc` (con cambios sin commit)
- Repeticiones por caso (A, B, C): 3
- Evaluador: `nvidia/nemotron-3-super-120b-a12b` · Mejorador: `moonshotai/kimi-k3`
- NVIDIA_BASE_URL: `https://integrate.api.nvidia.com/v1`
- LLM_TIMEOUT_SECONDS: `180`
- LLM_MAX_RETRIES: `2`
- temperatura: `no se envía: valor por defecto de cada modelo en NVIDIA`
- Fórmula: Requirements Quality Score = promedio de los 10 criterios (1-10) × 10; alta calidad = ≥ 80 y ningún criterio < 6.

## Resumen

| Caso | Tipo | Corridas que cumplen | Puntaje original | Puntaje mejorado | Delta | Latencia total (s) |
|---|---|---|---|---|---|---|
| A | Requisito claro | **3/3** | 94.3 ± 4.9 | — | — | 11.5 ± 1.2 |
| B | Requisito ambiguo | **1/3** | 55.3 ± 1.5 | 60.0 ± 3.5 | 4.7 ± 2.5 | 179.1 ± 75.1 |
| C | Requisito contradictorio o incompleto | **3/3** | 35.0 ± 4.6 | 43.0 ± 9.0 | 8.0 ± 4.6 | 95.6 ± 19.3 |
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
| **G1** El análisis terminó sin error | ✅ COMPLETED | ✅ COMPLETED | ✅ COMPLETED |
| **G2** La evaluación del original es válida (10 criterios) | ✅ | ✅ | ✅ |
| **A1** Reconoce alta calidad (≥ 80 y ningún criterio < 6) | ✅ puntaje 100, mínimo 10 | ✅ puntaje 91, mínimo 8 | ✅ puntaje 92, mínimo 8 |
| **A2** No modifica el requisito | ✅ omitida | ✅ omitida | ✅ omitida |
| **A3** (informativa) No hace preguntas de aclaración | ✅ 0 preguntas | ❌ 2 preguntas | ❌ 1 preguntas |
| **A4** (informativa) No marca términos ambiguos | ✅ ninguno | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 1 — análisis <code>28d48c58-7b25-4b81-9d81-56fe2ecfe885</code></summary>

**Diagnóstico:** El requisito REQ-AUT-03 es de alta calidad: claro, específico, atómico, completo, consistente, factible, verificable, trazable, libre de ambigüedades y con criterios de aceptación bien definidos. No requiere cambios.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 10 | — | El requisito es claro y no admite interpretaciones contradictorias: 'El sistema deberá bloquear durante 15 minutos la cuenta de un cliente registrado cuando se produzcan 5 intentos fallidos consecutivos de inicio de sesión dentro de un periodo de 10 minutos'. |
| especificidad | 10 | — | Expresa con precisión el comportamiento: 5 intentos fallidos consecutivos dentro de 10 minutos provocan un bloqueo de 15 minutos. Los criterios de aceptación detallan condiciones y resultados esperados. |
| atomicidad | 10 | — | El requisito describe una única regla de bloqueo tras un número específico de intentos fallidos en una ventana temporal definida. No combina requisitos independientes. |
| completitud | 10 | — | Incluye toda la información necesaria: actor (cliente registrado), condición (5 intentos fallidos consecutivos en 10 minutos), acción (bloquear cuenta), duración (15 minutos), y criterios de aceptación que cubren casos de uso y recuperación. |
| consistencia | 10 | — | No hay contradicciones internas ni con el contexto del proyecto (tienda en línea con política de seguridad de bloqueo temporal). Los criterios de aceptación son consistentes entre sí y con el requisito principal. |
| factibilidad | 10 | — | Es factible implementar un mecanismo de conteo de intentos fallidos con ventanas temporales y bloqueo de cuenta, estándar en sistemas de autenticación. |
| verificabilidad | 10 | — | Permite verificacion objetiva mediante pruebas: se puede simular 4 intentos fallidos, luego un quinto y verificar el bloqueo; o esperar 15 minutos y verificar que el acceso se restablece con credenciales correctas. |
| trazabilidad | 10 | — | Tiene un identificador único (REQ-AUT-03) y declara su origen (política de seguridad de la tienda en línea), lo que permite relacionarlo con necesidad, diseño, implementación y prueba. |
| ausencia_ambiguedad | 10 | — | No contiene términos subjetivos o vagos. Todos los conceptos son medibles: 5 intentos, 10 minutos, 15 minutos, cuenta bloqueada, inicio de sesión exitoso/fallido. |
| criterios_aceptacion | 10 | — | Incluye tres criterios de aceptación explícitos, medibles y en formato Dado/Cuando/Entonces que definen claramente cuándo el requisito está satisfecho. |

</details>

<details><summary>Corrida 2 — análisis <code>a87eef01-19ca-4fde-a291-d8b5a9e7bfa1</code></summary>

**Diagnóstico:** El requisito REQ-AUT-03 es claro, específico, atómico, verificable y libre de ambigüedades, con buenos criterios de aceptación. Solo presenta lagunas menores en el manejo del contador tras eventos de tiempo (desbloqueo y vencimiento de intentos), lo que afecta ligeramente la completitud y trazabilidad. En general, es un requisito de alta calidad listo para desarrollo y prueba.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 9 | — | El requisito es claro y comprensible sin ambigüedades: bloqueo de 15 minutos tras 5 intentos fallidos consecutivos en 10 minutos. |
| especificidad | 9 | — | Especifica con precisión el umbral (5 intentos), ventana temporal (10 minutos), duración del bloqueo (15 minutos) y comportamiento (rechazo total de inicio de sesión). |
| atomicidad | 9 | — | Expresa un único requisito de seguridad: bloqueo temporal tras intentos fallidos. No combina requisitos independientes. |
| completitud | 8 | — | El texto define el comportamiento principal y los criterios de aceptación cubren casos clave, pero no especifica qué ocurre con intentos fuera de la ventana de 10 minutos o si el contador se reinicia tras el desbloqueo automático. |
| consistencia | 10 | — | No hay contradicciones internas ni con el contexto del proyecto (tienda en línea, política de seguridad). El requisito y sus criterios son coherentes entre sí. |
| factibilidad | 9 | — | Es técnicamente factible: requiere registro de timestamps de intentos y temporizador de bloqueo, ambos comunes en sistemas de autenticación. |
| verificabilidad | 9 | — | Permite verificar objetivamente: se pueden simular intentos fallidos y medir tiempos de bloqueo y restablecimiento. |
| trazabilidad | 8 | — | Tiene un identificador único (REQ-AUT-03) y menciona su origen (política de seguridad). Permite vincularse a diseño, código y pruebas, aunque no especifica la necesidad de negocio exacta detrás de la política. |
| ausencia_ambiguedad | 10 | — | No contiene términos subjetivos o vagos. Todos los elementos son medibles: 5 intentos, 10 minutos, 15 minutos, inicio de sesión exitoso/fallido. |
| criterios_aceptacion | 10 | — | Incluye tres criterios de aceptación claros, medibles y en formato Dado/Cuando/Entonces que definen condiciones de activación, comportamiento y restablecimiento. |

**Preguntas:**

- ¿Tras el desbloqueo automático de una cuenta (15 minutos después del bloqueo), el contador de intentos fallidos se reinicia a 0 o conserva su valor previo?
- ¿Los intentos fallidos más antiguos de 10 minutos se descartan del contador o se acumulan indefinidamente hasta alcanzar 5?

</details>

<details><summary>Corrida 3 — análisis <code>3495e028-a315-425a-bd3c-6334e54486c2</code></summary>

**Diagnóstico:** El requisito REQ-AUT-03 es de alta calidad: claro, específico, atómico, coherente, factible, verificable, trazable y libre de ambigüedades. Sus criterios de aceptación son completos y bien estructurados. Solo se beneficia de menor precisión en la definición de 'intento fallido' y mención explícita del actor en la frase principal.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 9 | — | El requisito es claro y no admite interpretaciones contradictorias. El texto especifica con precisión la condición (5 intentos fallidos consecutivos en 10 minutos) y la consecuencia (bloqueo de 15 minutos). |
| especificidad | 9 | — | El requisito expresa con suficiente precisión el comportamiento esperado: bloqueo de cuenta tras 5 intentos fallidos consecutivos dentro de 10 minutos, durante 15 minutos. Incluye umbrales numéricos claros. |
| atomicidad | 10 | — | El requisito es atómico: expresa una sola regla de seguridad (bloqueo tras fallos repetidos) sin mezclar varios requisitos independientes. |
| completitud | 8 | — | El requisito incluye la información necesaria para comprender y desarrollar el comportamiento solicitado (umbral de intentos, ventana de tiempo, duración del bloqueo). Solo falta especificar claramente qué constituye un 'intento fallido' (por ejemplo, credenciales inválidas), aunque esto se infiere del contexto. |
| consistencia | 10 | — | El requisito es internamente coherente y no contradice el contexto del proyecto (tienda en línea con política de seguridad que exige bloqueo temporal ante intentos fallidos repetidos). Los criterios de aceptación son consistentes entre sí y con el requisito principal. |
| factibilidad | 9 | — | El bloqueo temporal de cuentas tras un número definido de intentos fallidos es una medida de seguridad estándar y factible de implementar con tecnologías comunes (registros de intentos, temporizadores, estado de cuenta). |
| verificabilidad | 9 | — | El requisito permite comprobar objetivamente su cumplimiento mediante pruebas que simulen los escenarios descritos en los criterios de aceptación (4 fallos + quinto fallo → bloqueo; cuenta bloqueada ≥15 min + credencial correcta → éxito; 4 fallos + éxito → contador a 0). |
| trazabilidad | 8 | — | El requisito tiene un identificador único (REQ-AUT-03) y declara su origen (política de seguridad de la tienda en línea), lo que permite relacionarlo con necesidad, diseño, implementación y prueba. No especifica explícitamente al actor en el texto principal, pero se infiere del contexto y los criterios de aceptación mencionan 'cliente'. |
| ausencia_ambiguedad | 10 | — | No se detectan términos subjetivos o vagos como 'rápido', 'fácil', 'adecuado', etc. Todos los conceptos son específicos y medibles (intentos, minutos, conteo). |
| criterios_aceptacion | 10 | — | Los criterios de aceptación están explícitamente definidos en formato Dado/Cuando/Entonces, son verificables y cubren los casos clave: activación del bloqueo, recuperación tras tiempo suficiente y reseteo del contador tras éxito. |

**Preguntas:**

- ¿Se considera intento fallido únicamente cuando tanto el correo como la contraseña son incorrectos, o también aplica si solo uno de ellos es erróneo?

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
| **G1** El análisis terminó sin error | ✅ COMPLETED | ✅ COMPLETED | ✅ COMPLETED |
| **G2** La evaluación del original es válida (10 criterios) | ✅ | ✅ | ✅ |
| **B1** Detecta los términos vagos (rápida / sencilla / relevantes) | ✅ rápido, sencillo, relevantes | ✅ rápida, sencilla, relevantes | ✅ rápido, sencilla, relevantes |
| **B2** Formula preguntas de aclaración | ✅ 5 preguntas | ✅ 4 preguntas | ✅ 5 preguntas |
| **B3** Mejora el requisito (versión mejorada con delta > 0) | ✅ delta 5 | ✅ delta 7 | ✅ delta 2 |
| **B4** No inventa valores numéricos | ✅ ninguno | ✅ ninguno | ✅ ninguno |
| **B5** Con las respuestas del stakeholder el requisito final supera al original | ✅ original 57 → final tras aclarar 88 | ❌ original 55 → final tras aclarar 64 | ❌ original 54 → final tras aclarar 65 |
| **B6** (informativa) Tras aclarar quedan menos datos por definir | ✅ 6 → 0 pendientes | ❌ 5 → 0 pendientes | ❌ 5 → 0 pendientes |
| **B7** Tras aclarar no inventa valores numéricos | ✅ ninguno | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 1 — análisis <code>c8cad16b-d737-419a-a097-f4b62466c414</code></summary>

**Diagnóstico:** El requisito expresa una intención clara pero carece de especificidad, criterios medibles y detalles necesarios para su implementación y verificación. Contiene términos ambiguos que impiden una evaluación objetiva y carece de criterios de aceptación. Se necesita definir claramente qué se entiende por 'rápido', 'sencillo' y 'relevantes', así como agregar información esencial para hacer el requisito verificable y trazable.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 6 | 7 | El texto permite entender la idea general, pero 'buscar productos de forma rápida y sencilla' deja espacio a interpretaciones sobre qué se considera rápido y sencillo. |
| especificidad | 5 | 6 | No se especifica cómo se realiza la búsqueda (por nombre, categoría, atributos), ni qué se entiende por 'resultados relevantes'. |
| atomicidad | 8 | 3 | El requisito expresa una única funcionalidad principal: permitir la búsqueda de productos. Aunque incluye dos características (rápida y sencilla), están estrechamente ligadas al mismo objetivo. |
| completitud | 5 | 5 | Faltan detalles esenciales: qué atributos de producto se pueden buscar, cómo se determina la relevancia, y qué formato tienen los resultados mostrados. |
| consistencia | 9 | 8 | No hay contradicciones internas ni con el contexto del proyecto (tienda en línea de artículos deportivos). |
| factibilidad | 8 | 8 | Permitir búsqueda de productos es factible en una tienda en línea; no se mencionan restricciones técnicas que lo impidan. |
| verificabilidad | 4 | 6 | No se puede verificar objetivamente si la búsqueda es 'rápida', 'sencilla' o si muestra 'resultados relevantes' sin criterios medibles. |
| trazabilidad | 5 | 6 | No se incluye un identificador único ni se vincula explícitamente a una necesidad de usuario o objetivo de negocio. |
| ausencia_ambiguedad | 4 | 8 | Contiene términos ambiguos: 'rápido' (¿cuánto tiempo máximo?), 'sencillo' (¿cuántos pasos?, ¿interfaz?), 'relevantes' (¿según qué criterio?). |
| criterios_aceptacion | 3 | 5 | No se incluyen criterios de aceptación explícitos ni condiciones medibles que permitan determinar cuándo el requisito está satisfecho. |

**Preguntas:**

- ¿Qué se considera un tiempo máximo aceptable para que la búsqueda sea percibida como 'rápida' por el cliente?
- ¿Cuántos pasos o interacciones (por ejemplo, teclas pulsadas, selecciones) se consideran máximos para una búsqueda 'sencilla'?
- ¿En qué atributos de los productos (nombre, descripción, marca, categoría, etc.) debe poder buscarse el cliente?
- ¿Qué criterio debe usarse para determinar si un resultado es 'relevante' (por ejemplo, coincidencia de texto, popularidad, historial de compras, stock disponible)?
- ¿Se requiere un identificador único para este requisito y debe vincularse a una historia de usuario específica?

**Requisito mejorado:**

```text
[POR DEFINIR: identificador único del requisito]-A: El sistema deberá permitir a los clientes (invitados o registrados) buscar productos del catálogo ingresando un término de búsqueda sobre los campos [POR DEFINIR: campos de producto sobre los que se puede buscar, ej. nombre, marca, categoría].
[POR DEFINIR: identificador único del requisito]-B: El sistema deberá mostrar los resultados de la búsqueda en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta] desde que el cliente envía la consulta.
[POR DEFINIR: identificador único del requisito]-C: El sistema deberá presentar los resultados ordenados según [POR DEFINIR: criterio objetivo de relevancia, ej. coincidencia con el término, popularidad, disponibilidad de stock].
[POR DEFINIR: identificador único del requisito]-D: La interfaz de búsqueda deberá permitir al cliente acceder a los resultados en un máximo de [POR DEFINIR: número máximo de pasos o interacciones] desde la página donde se encuentre.
Vinculación: Como cliente, quiero encontrar productos fácilmente para comprar más rápido.
```

**Criterios de aceptación:**

- Dado un cliente en la tienda en línea, cuando ingresa un término en el campo de búsqueda y lo envía, entonces el sistema muestra resultados obtenidos de los campos [POR DEFINIR: campos de búsqueda] en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta].
- Dado un término de búsqueda con productos coincidentes, cuando el sistema muestra los resultados, entonces estos aparecen ordenados según [POR DEFINIR: criterio de relevancia].
- Dado un cliente en cualquier página del catálogo, cuando desea buscar un producto, entonces puede iniciar y ejecutar la búsqueda en un máximo de [POR DEFINIR: número máximo de pasos o interacciones].

**Tras responder las preguntas** (análisis `ac2ce3b7-f0fc-4275-9721-eec5862904b9`): estado COMPLETED, puntaje original 61, mejorado 88.

```text
REQ-1: El sistema deberá permitir a los clientes (registrados e invitados) buscar productos desde un único cuadro de texto visible en la parte superior de todas las páginas, sin requerir inicio de sesión ni el uso de filtros.
REQ-2: El sistema deberá buscar coincidencias del texto ingresado en los campos nombre, marca y categoría del producto.
REQ-3: El sistema deberá mostrar los resultados de búsqueda en un tiempo máximo de 2 segundos desde que se inicia la búsqueda, con un catálogo de hasta 20000 productos.
REQ-4: El sistema deberá ordenar los resultados mostrando primero las coincidencias en el nombre del producto y luego las demás coincidencias (marca o categoría), ordenando dentro de cada grupo por unidades vendidas de mayor a menor.
```

</details>

<details><summary>Corrida 2 — análisis <code>e74916d5-1102-4c41-b96c-499296a87544</code></summary>

**Diagnóstico:** El requisito es comprensible pero demasiado vago para guiar el desarrollo y las pruebas debido al uso de términos subjetivos como 'rápida', 'sencilla' y 'relevantes'. Carece de especificidad, criterios de aceptación medibles y detalles necesarios para su implementación y verificabilidad. Se requiere definir atributos buscables, umbrales de tiempo, pasos permitidos y reglas de relevancia para mejorar su calidad.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 6 | 7 | El requisito indica que el sistema debe permitir buscar productos de forma 'rápida y sencilla', lo cual puede interpretarse de manera subjetiva según el usuario o el contexto de uso. |
| especificidad | 5 | 6 | El requisito menciona 'buscar productos' y 'mostrar resultados relevantes', pero no especifica qué atributos se pueden buscar (nombre, categoría, marca, etc.) ni qué criterios determinan la relevancia de los resultados. |
| atomicidad | 7 | 2 | El requisito combina dos ideas: permitir la búsqueda y mostrar resultados relevantes, pero ambas están estrechamente relacionadas y forman parte de un mismo flujo de búsqueda, por lo que no constituye una mezcla clara de requisitos independientes. |
| completitud | 5 | 5 | Falta información esencial como los campos de búsqueda permitidos, el umbral de tiempo para considerar la búsqueda 'rápida', y los criterios que definen qué resultados son 'relevantes'. |
| consistencia | 8 | 9 | No se observa contradicción interna ni con el contexto del proyecto (tienda en línea de artículos deportivos), donde la búsqueda de productos es una funcionalidad esperada y coherente. |
| factibilidad | 8 | 8 | Permitir búsquedas de productos con resultados relevantes es factible en una tienda en línea usando tecnologías estándar de indexación y búsqueda (como bases de datos con full-text search o Elasticsearch). |
| verificabilidad | 4 | 6 | No se puede verificar objetivamente si la búsqueda es 'rápida y sencilla' ni si los resultados son 'relevantes', ya que estos términos no tienen umbrales o métricas definidas. |
| trazabilidad | 5 | 8 | El requisito no incluye un identificador único (como REQ-1) ni menciona su origen (por ejemplo, necesidad del cliente, objetivo de negocio), lo que dificulta su trazabilidad a diseño, código o pruebas. |
| ausencia_ambiguedad | 4 | 7 | Los términos 'rápida', 'sencilla' y 'relevantes' son subjetivos y no definidos, lo que introduce ambigüedad en la interpretación del requisito. |
| criterios_aceptacion | 3 | 4 | No se incluyen criterios de aceptación explícitos ni condiciones medibles que permitan determinar cuándo el requisito está satisfecho (por ejemplo, umbrales de tiempo, precisión, o pasos requeridos). |

**Preguntas:**

- ¿Qué atributos de los productos deben ser buscables (por ejemplo, nombre, descripción, marca, categoría)?
- ¿Cuál es el tiempo máximo de respuesta aceptable para considerar la búsqueda 'rápida'?
- ¿Cuántos pasos o interacciones como máximo se permiten para considerar la búsqueda 'sencilla'?
- ¿Qué criterios deben usarse para determinar si un resultado es 'relevante' (por ejemplo, coincidencia de texto, popularidad, stock disponible, historial de compras)?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá permitir a los clientes (con cuenta registrada o como invitados) buscar productos del catálogo ingresando un texto de búsqueda que se comparará con [POR DEFINIR: atributos buscables del producto, p. ej. nombre, categoría, marca, descripción].
REQ-2: El sistema deberá presentar los resultados de la búsqueda en un tiempo de respuesta menor o igual a [POR DEFINIR: tiempo máximo de respuesta] desde que el cliente envía la consulta.
REQ-3: El cliente podrá acceder a la búsqueda y obtener resultados en un máximo de [POR DEFINIR: número máximo de pasos o interacciones] desde [POR DEFINIR: punto de inicio, p. ej. la página principal].
REQ-4: El sistema deberá ordenar los resultados de búsqueda según [POR DEFINIR: criterios de relevancia, p. ej. coincidencia con el texto ingresado, popularidad, disponibilidad en stock].
```

**Criterios de aceptación:**

- Dado un cliente (registrado o invitado) en la tienda, cuando ingresa un texto de búsqueda y envía la consulta, entonces el sistema busca coincidencias en [POR DEFINIR: atributos buscables del producto] y muestra los resultados.
- Dado un cliente que envía una consulta de búsqueda, cuando el sistema procesa la solicitud, entonces los resultados se muestran en un tiempo menor o igual a [POR DEFINIR: tiempo máximo de respuesta].
- Dado un cliente en [POR DEFINIR: punto de inicio], cuando realiza una búsqueda, entonces obtiene resultados en no más de [POR DEFINIR: número máximo de pasos o interacciones].
- Dado un conjunto de productos que coinciden con la consulta, cuando se muestran los resultados, entonces están ordenados según [POR DEFINIR: criterios de relevancia].

**Tras responder las preguntas** (análisis `90b008e0-9962-4b25-a81f-0eca95429bc5`): estado ERROR, puntaje original 64, mejorado —.

</details>

<details><summary>Corrida 3 — análisis <code>da7fedc2-c211-49c5-8e16-65b6febc425f</code></summary>

**Diagnóstico:** El requisito expresa una necesidad válida pero demasiado vaga para ser desarrollado o probado. Carece de especificidad, criterios medibles y trazabilidad, lo que impide una implementación y verificación objetivas. Se requiere definir umbrales de rendimiento, usabilidad y relevancia, así como agregar un identificador y criterios de aceptación claros.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 6 | 6 | El requisito es generalmente claro en su intención, pero los términos 'rápido', 'sencilla' y 'relevantes' son subjetivos y permiten interpretaciones contradictorias sobre qué se considera aceptable. |
| especificidad | 5 | 5 | El requisito carece de especificidad en cuanto a cómo se realiza la búsqueda (por nombre, categoría, atributos), qué se considera un resultado relevante y qué umbral de velocidad o esfuerzo define 'rápido' y 'sencilla'. |
| atomicidad | 8 | 4 | El requisito expresa una única intención principal: permitir la búsqueda de productos. Aunque incluye varios aspectos (velocidad, facilidad, relevancia), todos contribuyen al mismo objetivo central y no representa requisitos funcionales independientes. |
| completitud | 4 | 5 | Faltan detalles esenciales para el desarrollo y prueba: campos de búsqueda permitidos, algoritmo o reglas de relevancia, umbrales de tiempo de respuesta, métricas de facilidad de uso y alcance (por ejemplo, si incluye filtros, ordenación o sugerencias). |
| consistencia | 8 | 8 | No se detectan contradicciones internas en el requisito. Es consistente con el contexto de una tienda en línea pública donde se espera funcionalidad de búsqueda básica. |
| factibilidad | 8 | 8 | Permitir búsquedas de productos en un catálogo público es técnicamente factible con tecnologías estándar. No se mencionan restricciones que hagan imposible su implementación. |
| verificabilidad | 4 | 5 | No hay criterios medibles para verificar si la búsqueda es 'rápida', 'sencilla' o muestra 'resultados relevantes'. Sin umbrales definidos, no se puede determinar objetivamente si el requisito se cumple. |
| trazabilidad | 5 | 3 | El requisito no incluye un identificador único ni referencia explícita a una necesidad, origen o stakeholder, lo que dificulta su trazabilidad a diseño, implementación o pruebas. |
| ausencia_ambiguedad | 3 | 7 | Contiene términos ambiguos y subjetivos: 'rápido' (no define tiempo máximo), 'sencilla' (no define esfuerzo o pasos máximos), 'relevantes' (no define criterios de pertinencia). |
| criterios_aceptacion | 3 | 5 | No se incluyen criterios de aceptación explícitos ni condiciones medibles que permitan determinar cuándo el requisito está satisfecho. Los adjetivos usados no pueden verificarse directamente. |

**Preguntas:**

- ¿Qué atributos del producto deben ser buscables (nombre, descripción, categoría, marca, etc.)?
- ¿Cuál es el tiempo máximo de respuesta aceptable para considerar la búsqueda 'rápida'?
- ¿Cuántos pasos o interacciones máximos debería requerir una búsqueda para considerarla 'sencilla'?
- ¿Qué criterios deben determinar la relevancia de los resultados (coincidencia de texto, popularidad, ventas, disponibilidad, etc.)?
- ¿Desea asignar un identificador único a este requisito para fines de trazabilidad?

**Requisito mejorado:**

```text
[POR DEFINIR: identificador único del requisito de búsqueda]: El sistema deberá permitir a los clientes (invitados o registrados) buscar productos del catálogo ingresando un término de búsqueda sobre los campos [POR DEFINIR: campos buscables, por ejemplo nombre, descripción, categoría, marca].
[POR DEFINIR: identificador único del requisito de tiempo de respuesta]: El sistema deberá mostrar los resultados de la búsqueda en un tiempo de respuesta máximo de [POR DEFINIR: umbral de tiempo de respuesta en segundos].
[POR DEFINIR: identificador único del requisito de esfuerzo de búsqueda]: El sistema deberá permitir realizar una búsqueda en un máximo de [POR DEFINIR: número máximo de pasos o interacciones del usuario].
[POR DEFINIR: identificador único del requisito de relevancia]: El sistema deberá ordenar o filtrar los resultados de búsqueda según los criterios de relevancia [POR DEFINIR: criterios de relevancia, por ejemplo coincidencia de texto, popularidad, disponibilidad].
```

**Criterios de aceptación:**

- Dado un cliente (invitado o registrado) en la tienda en línea, cuando ingresa un término de búsqueda, entonces el sistema busca en los campos [POR DEFINIR: campos buscables] y muestra los productos coincidentes.
- Dado un cliente que ejecuta una búsqueda, cuando el sistema procesa la consulta, entonces los resultados se muestran en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta].
- Dado un cliente que desea buscar un producto, cuando inicia la búsqueda, entonces puede completarla en un máximo de [POR DEFINIR: número máximo de pasos o interacciones].
- Dado un conjunto de resultados de búsqueda, cuando se muestran al cliente, entonces están ordenados según [POR DEFINIR: criterios de relevancia].

**Tras responder las preguntas** (análisis `bde13db1-c276-4a3c-9b24-b8953c5b2b0b`): estado ERROR, puntaje original 65, mejorado —.

</details>

## Caso C — Requisito contradictorio o incompleto

**Esperado (enunciado):** Debe señalar la inconsistencia o falta de información y abstenerse de inventar datos.

**Entrada:**

```text
Los reportes de ventas deben generarse automáticamente cada día, pero solo cuando el gerente los solicite manualmente, y deben incluir los datos necesarios.
```

| Verificación | Corrida 1 | Corrida 2 | Corrida 3 |
|---|---|---|---|
| **G1** El análisis terminó sin error | ✅ COMPLETED | ✅ COMPLETED | ✅ COMPLETED |
| **G2** La evaluación del original es válida (10 criterios) | ✅ | ✅ | ✅ |
| **C1** Detecta la contradicción (consistencia ≤ 3) | ✅ consistencia 2 | ✅ consistencia 2 | ✅ consistencia 3 |
| **C2** Señala la información faltante y pregunta | ✅ 4 faltantes, 4 preguntas | ✅ 4 faltantes, 4 preguntas | ✅ 4 faltantes, 4 preguntas |
| **C3** Deja explícito lo que falta con [POR DEFINIR] | ✅ 4 pendientes | ✅ 5 pendientes | ✅ 4 pendientes |
| **C4** No resuelve la contradicción por su cuenta (la deja pendiente) | ✅ | ✅ | ✅ |
| **C5** No inventa valores numéricos | ✅ ninguno | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 1 — análisis <code>e28a090f-e3de-489a-afde-a35a34075e0b</code></summary>

**Diagnóstico:** El requisito contiene una contradicción crítica entre generación automática diaria y dependencia de solicitud manual, lo que lo hace incomprensible y no verificable. Además, falta especificar el contenido del reporte y carece de identificador y criterios de aceptación. Se requiere aclarar la intención real antes de poder proceder con el desarrollo.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 4 | 4 | El requisito presenta una contradicción: 'deben generarse automáticamente cada día, pero solo cuando el gerente los solicite manualmente' es contradictorio porque 'automáticamente cada día' y 'solo cuando el gerente los solicite manualmente' no pueden ser ciertos simultáneamente. |
| especificidad | 4 | 3 | El requisito no especifica qué se entiende por 'datos necesarios', ni el formato, ni el alcance de los datos de ventas que deben incluirse en el reporte. |
| atomicidad | 3 | 7 | El requisito combina múltiples ideas independientes: (1) generación automática diaria, (2) dependencia de solicitud manual del gerente, (3) inclusión de datos necesarios. Estas son condiciones lógicamente conflictivas y no pueden considerarse como un único requisito atómico. |
| completitud | 3 | 3 | Faltan datos esenciales: qué se entiende por 'datos necesarios', cómo se dispara exactamente la generación (¿al solicitar, o se programa y se libera al solicitar?), y qué significa 'cada día' en relación con la solicitud manual. |
| consistencia | 2 | 2 | Contradicción interna explícita: 'generarse automáticamente cada día' y 'solo cuando el gerente los solicite manualmente' son mutuamente excluyentes. No pueden ocurrir ambas al mismo tiempo bajo la misma condición. |
| factibilidad | 5 | 6 | Dado el contexto de un sistema de ventas web para una cadena de tiendas, es factible generar reportes de ventas automáticamente o bajo demanda. Sin embargo, la contradicción impide determinar qué exactamente construir. |
| verificabilidad | 3 | 4 | No se puede verificar objetivamente si el requisito se cumple debido a la contradicción y la vaguedad de 'datos necesarios'. No hay criterio observable para confirmar si se generó 'automáticamente cada día' o 'solo cuando se solicitó manualmente'. |
| trazabilidad | 4 | 6 | El requisito no incluye un identificador único (como REQ-1) ni menciona explícitamente al actor (gerente) como origen de la necesidad, lo que dificulta relacionarlo con diseño, código y pruebas. Aunque el contexto menciona a los gerentes, no está vinculado explícitamente en el texto del requisito. |
| ausencia_ambiguedad | 4 | 5 | El término 'datos necesarios' es ambiguo y subjetivo: no define qué datos son considerados necesarios, lo que permite interpretaciones variadas. |
| criterios_aceptacion | 2 | 3 | No se incluyen criterios de aceptación explícitos ni condiciones medibles que permitan determinar cuándo el requisito está satisfecho. La contradicción y la vaguedad impiden derivar criterios verificables. |

**Preguntas:**

- ¿El reporte se debe generar automáticamente todos los días y estar disponible para que el gerente lo descargue manualmente cuando lo desee?
- ¿O el reporte solo se genera en el momento en que el gerente lo solicita manualmente?
- ¿Qué datos específicos se consideran 'necesarios' en el reporte de ventas?
- ¿El reporte debe incluir datos del día en curso, del día anterior, o acumulados?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá generar el reporte de ventas [POR DEFINIR: resolver contradicción entre generación automática diaria y generación solo cuando el gerente lo solicite manualmente].
REQ-2: El gerente podrá acceder al reporte de ventas generado desde la web [POR DEFINIR: mecanismo exacto de acceso: descarga, visualización en pantalla, etc.].
REQ-3: El reporte de ventas deberá incluir [POR DEFINIR: lista de datos que debe contener, p. ej.: ventas totales, por tienda, por producto] y cubrirá el período [POR DEFINIR: alcance temporal del reporte].
```

**Criterios de aceptación:**

- Dado que se cumple [POR DEFINIR: condición de generación: diaria automática o solicitud manual del gerente], cuando el sistema genera el reporte de ventas, entonces el reporte queda disponible para el gerente.
- Dado que el gerente accede desde la web, cuando solicita o consulta el reporte de ventas, entonces el sistema le muestra o entrega el reporte por [POR DEFINIR: mecanismo de acceso].
- Dado un reporte de ventas generado, cuando el gerente lo revisa, entonces contiene [POR DEFINIR: lista de datos] correspondientes al período [POR DEFINIR: alcance temporal].

</details>

<details><summary>Corrida 2 — análisis <code>a66c987a-c914-4c76-a74f-59459b0e36d8</code></summary>

**Diagnóstico:** El requisito es contradictorio y ambiguo: combina generación automática diaria con generación solo a petición manual, lo que lo hace imposible de interpretar sin aclaraciones. Carece de especificidad en datos necesarios, criterios de aceptación verificables y definiciones concretas. Antes de poder desarrollarse o probarse, se requiere resolver la contradicción central y definir claramente el comportamiento esperado, el contenido del reporte y el mecanismo de solicitud.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | 3 | El requisito contiene una contradicción lógica: 'generarse automáticamente cada día, pero solo cuando el gerente los solicite manualmente' es imposible de interpretar sin ambigüedad, ya que 'automáticamente' y 'solo cuando el gerente los solicite manualmente' son mutuamente excluyentes. |
| especificidad | 3 | 2 | No se especifica qué se entiende por 'datos necesarios', ni qué formato, ni qué métricas de ventas deben incluirse en el reporte. |
| atomicidad | 4 | 4 | El requisito mezcla al menos dos ideas: la condición de generación (automática vs manual) y el contenido (datos necesarios). Aunque podría interpretarse como una sola afirmación condicional, la contradicción interna lo hace difícil de tratar como atómico. |
| completitud | 3 | 2 | Falta definir: qué evento desencadena la generación automática (si es que existe), qué significa 'solo cuando el gerente los solicite manualmente' en un contexto diario, y qué datos son 'necesarios'. |
| consistencia | 2 | 2 | Contradicción directa: 'generarse automáticamente cada día' implica que ocurre sin intervención humana todos los días, pero 'solo cuando el gerente los solicite manualmente' implica que nunca ocurre sin solicitud. Estas dos afirmaciones no pueden ser verdaderas simultáneamente. |
| factibilidad | 4 | 7 | Si se interpreta como 'generarse automáticamente todos los días a una hora fija, pero solo enviarse/notificarse si el gerente lo solicitó ese día', podría ser factible. Sin embargo, como está escrito, la contradicción lo hace imposible de implementar sin aclaraciones. |
| verificabilidad | 3 | 3 | No se puede verificar objetivamente si se cumple debido a la contradicción y la vaguedad de 'datos necesarios'. No hay criterio observable para confirmar que el reporte se generó 'automáticamente cada día' ni que incluyó lo 'necesario'. |
| trazabilidad | 5 | 5 | Aunque no tiene un identificador explícito (como REQ-1), el requisito puede trazarse a la necesidad del gerente de acceder a reportes de ventas desde la web, tal como se indica en el contexto. |
| ausencia_ambiguedad | 2 | 3 | Términos ambiguos: 'automáticamente' (¿sin intervención? ¿cada cuánto?), 'cada día' (¿a qué hora? ¿días hábiles?), 'solo cuando el gerente los solicite manualmente' (¿qué constituye una solicitud manual?), 'datos necesarios' (¿qué datos? ¿según quién?). |
| criterios_aceptacion | 2 | 3 | No hay criterios de aceptación explícitos ni condiciones medibles que permitan determinar cuándo el requisito está satisfecho. La contradicción y la vaguedad impiden derivar criterios claros. |

**Preguntas:**

- ¿El reporte se genera automáticamente todos los días a una hora fija (ej. 07:00) independientemente de si el gerente lo solicita, o solo se genera cuando el gerente lo solicita manualmente?
- ¿Qué datos específicos deben incluirse en el reporte de ventas? (ej. total de ventas, unidades vendidas, top 5 productos, ventas por tienda, etc.)
- ¿Cómo realiza el gerente la solicitud manual? (ej. botón en el portal web, correo electrónico, etc.)
- ¿Los reportes automáticos se generan todos los días del año o solo días laborables?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá generar el reporte de ventas [POR DEFINIR: resolver contradicción entre generación automática diaria y generación únicamente por solicitud manual del gerente] [POR DEFINIR: hora y días de generación en caso de ser automática, o mecanismo de solicitud manual en caso de ser a petición].
REQ-2: El reporte de ventas deberá incluir [POR DEFINIR: lista específica de datos del reporte, ej. total de ventas, cantidad de transacciones, por tienda o consolidado].
REQ-3: El sistema deberá permitir que el gerente consulte el reporte de ventas desde la web.
```

**Criterios de aceptación:**

- Dado que se alcanza [POR DEFINIR: momento o evento de generación], cuando se ejecuta la generación del reporte, entonces el sistema produce el reporte de ventas correspondiente (pendiente resolver si la generación es automática diaria o solo por solicitud manual del gerente).
- Dado un reporte de ventas generado, cuando el gerente lo abre desde la web, entonces el reporte contiene [POR DEFINIR: lista específica de datos del reporte].
- Dado un gerente autenticado en el portal web, cuando accede a la sección de reportes, entonces puede consultar el reporte de ventas disponible.

</details>

<details><summary>Corrida 3 — análisis <code>96f2be4e-b7f1-418a-a0b6-16e0517b77a6</code></summary>

**Diagnóstico:** El requisito presenta una contradicción crítica entre generación automática y manual, falta de especificidad en los datos y ausencia de criterios de aceptación, lo que impide su implementación y verificación claras.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 4 | 6 | El requisito contiene una contradicción: 'generarse automáticamente cada día' y 'solo cuando el gerente los solicite manualmente' son mutuamente excluyentes (automático vs. manual). |
| especificidad | 4 | 4 | No se especifica qué datos son 'los necesarios' ni el formato, alcance o nivel de detalle de los reportes de ventas. |
| atomicidad | 3 | 8 | El requisito mezcla dos comportamientos independientes: generación automática diaria y generación bajo solicitud manual, lo que lo hace compuesto. |
| completitud | 4 | 4 | Falta definir qué datos son necesarios, el formato del reporte, el mecanismo de solicitud manual y cómo se concilia la automática diaria con la solicitud manual. |
| consistencia | 3 | 3 | Contradicción interna: 'automáticamente cada día' implica ejecución sin intervención, mientras que 'solo cuando el gerente los solicite manualmente' requiere intervención humana. No pueden ocurrir simultáneamente como se plantea. |
| factibilidad | 6 | 7 | Es factible generar reportes automáticamente o bajo solicitud, pero la combinación actual es logicamente inviable debido a la contradicción. |
| verificabilidad | 4 | 4 | No se puede verificar objetivamente debido a la contradicción y la vaguedad de 'datos necesarios'. No hay criterios observables para confirmar cumplimiento. |
| trazabilidad | 5 | 7 | El requisito no tiene un identificador único (como REQ-1) ni menciona su origen (necesidad del gerente, norma, etc.), lo que dificulta su trazabilidad. |
| ausencia_ambiguedad | 4 | 6 | El término 'necesarios' es subjetivo y ambiguo: no define qué datos son necesarios ni según qué criterio. |
| criterios_aceptacion | 3 | 3 | No se incluyen criterios de aceptación explícitos ni condiciones medibles que permitan determinar cuándo el requisito está satisfecho. |

**Preguntas:**

- ¿Los reportes deben generarse automáticamente todos los días sin intervención, o solo cuando el gerente los solicite manualmente?
- ¿Qué datos específicos deben incluirse en los reportes de ventas (por ejemplo: totales, por producto, por tienda, por hora)?
- ¿En qué formato deben entregarse los reportes (PDF, Excel, CSV, etc.)?
- ¿Cómo debe realizar el gerente la solicitud manual (por ejemplo: botón en interfaz web, menú, etc.)?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá generar el reporte de ventas [POR DEFINIR: resolver contradicción entre generación automática diaria y generación solo bajo solicitud manual del gerente] en la web del sistema.
REQ-2: El reporte de ventas deberá incluir [POR DEFINIR: lista específica de datos o métricas del reporte] en formato [POR DEFINIR: formato del reporte].
REQ-3: El gerente deberá poder acceder al reporte de ventas desde la interfaz web del sistema mediante [POR DEFINIR: mecanismo de consulta o solicitud].
```

**Criterios de aceptación:**

- Dado que se cumple [POR DEFINIR: condición de generación resuelta automática o manual], cuando el sistema genera el reporte de ventas, entonces el reporte queda disponible para el gerente en la web del sistema.
- Dado un reporte de ventas generado, cuando el gerente lo visualiza, entonces contiene [POR DEFINIR: lista específica de datos o métricas] en formato [POR DEFINIR: formato del reporte].
- Dado que el gerente accede a la web del sistema, cuando utiliza [POR DEFINIR: mecanismo de consulta o solicitud], entonces puede ver el reporte de ventas.

</details>
