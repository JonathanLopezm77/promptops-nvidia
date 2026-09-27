# Punto 3 — Casos mínimos de prueba (Componente 1, sección 4.4)

> Archivo generado por `scripts/casos_requisitos.py informe` a partir de los JSON de
> `corridas/`. No editar a mano: la revisión humana está en `REVISION_MANUAL.md`.

## Condiciones de ejecución

- Ejecutado: 2026-09-27T16:15:42.302586+00:00 (UTC) contra `http://localhost:8000`
- Commit: `a7a1ded67c` (con cambios sin commit)
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
| A | Requisito claro | **3/3** | 97.3 ± 4.6 | — | — | 18.4 ± 9.6 |
| B | Requisito ambiguo | **3/3** | 52.3 ± 1.2 | 66.7 ± 6.1 | 14.3 ± 7.0 | 169.9 ± 25.8 |
| C | Requisito contradictorio o incompleto | **3/3** | 30.7 ± 1.5 | 48.0 ± 9.5 | 17.3 ± 8.5 | 128.7 ± 46.5 |
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
| **A1** Reconoce alta calidad (≥ 80 y ningún criterio < 6) | ✅ puntaje 92, mínimo 8 | ✅ puntaje 100, mínimo 10 | ✅ puntaje 100, mínimo 10 |
| **A2** No modifica el requisito | ✅ omitida | ✅ omitida | ✅ omitida |
| **A3** (informativa) No hace preguntas de aclaración | ✅ 0 preguntas | ✅ 0 preguntas | ✅ 0 preguntas |
| **A4** (informativa) No marca términos ambiguos | ✅ ninguno | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 1 — análisis <code>f907735a-fa6b-47ae-b53e-daf0fda50757</code></summary>

**Diagnóstico:** El requisito REQ-AUT-03 es de alta calidad: claro, específico, atómico, completo, consistente, factible, verificable, trazable y libre de ambigüedades. Sus criterios de aceptación están bien definidos y permiten una verificación objetiva. Solo se podrían hacer mejoras menores en trazabilidad y notificaciones al usuario, pero no afectan significativamente su utilidad para desarrollo y prueba.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 9 | — | El requisito es claro y no admite interpretaciones contradictorias: establece explícitamente el umbral de 5 intentos fallidos consecutivos, el periodo de 10 minutos, el bloqueo de 15 minutos y el comportamiento esperado. El texto y los criterios de aceptación describen la condición, el desencadenante y el resultado sin ambigüedad. |
| especificidad | 9 | — | El requisito especifica con precisión los valores numéricos (5 intentos, 10 minutos, 15 minutos), las condiciones (intentos fallidos consecutivos dentro del periodo), el actor (cliente registrado) y el resultado (cuenta bloqueada, sistema rechaza inicios de sesión). |
| atomicidad | 10 | — | El requisito es atómico: expresa un único comportamiento relacionado con el bloqueo de cuenta tras intentos fallidos. No combina múltiples requisitos independientes en una sola oración. |
| completitud | 9 | — | El requisito proporciona la información necesaria para comprender y desarrollar el comportamiento: actor, condiciones (número de intentos, periodo de tiempo), duración del bloqueo, y excepciones (éxito tras bloqueo). Los criterios de aceptación cubren los escenarios clave. Solo falta detalle sobre notificaciones al usuario, pero no es esencial para el desarrollo y prueba del comportamiento principal. |
| consistencia | 10 | — | No hay contradicciones internas ni con el contexto del proyecto. El requisito y sus criterios de aceptación son coherentes entre sí y alineados con la política de seguridad de la tienda en línea que exige bloqueo temporal ante intentos fallidos repetidos. |
| factibilidad | 9 | — | El comportamiento descrito es factible con tecnologías estándar de autenticación y manejo de sesiones. No se mencionan restricciones técnicas que lo impidan. Los marcadores [POR DEFINIR] no están presentes, por lo que no hay incertidumbre sobre datos faltantes. |
| verificabilidad | 9 | — | El requisito permite verificar objetivamente su cumplimiento: se pueden diseñar pruebas que simulen 4 intentos fallidos, luego un quinto, y validar que la cuenta se bloquee durante 15 minutos; o que tras 15 minutos, un intento exitoso permita el acceso. Los criterios de aceptación proporcionan un marco verificable (Dado/Cuándo/Entonces). |
| trazabilidad | 8 | — | El requisito tiene un identificador único (REQ-AUT-03) y declara su origen (política de seguridad de la tienda en línea), lo que permite relacionarlo con necesidad, diseño, implementación y prueba. No especifica explícitamente trazabilidad a elementos de diseño o código, pero el ID y el origen son suficientes para un rastreo básico. |
| ausencia_ambiguedad | 10 | — | No hay términos subjetivos o vagos como 'rápido', 'fácil', 'adecuado', etc. Todos los conceptos son precisos: 5 intentos, 10 minutos, 15 minutos, bloqueo, intentos fallidos consecutivos, reinicio del contador. |
| criterios_aceptacion | 9 | — | Los criterios de aceptación están presentes y son verificables: cubren el escenario principal (bloqueo tras quinto intento), la recuperación tras el tiempo de bloqueo y el reinicio del contador ante éxito. Están escritos en formato Dado/Cuándo/Entonces, lo que facilita su traducción a pruebas. |

</details>

<details><summary>Corrida 2 — análisis <code>ece16cfa-a7c1-4664-88af-8af241906120</code></summary>

**Diagnóstico:** El requisito REQ-AUT-03 es de alta calidad: claro, específico, atómico, completo, consistente, factible, verificable, trazable, sin ambigüedad y con criterios de aceptación bien definidos. No requiere modificaciones.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 10 | — | El requisito es claro y sin ambigüedad: 'El sistema deberá bloquear durante 15 minutos la cuenta de un cliente registrado cuando se produzcan 5 intentos fallidos consecutivos de inicio de sesión dentro de un periodo de 10 minutos.' |
| especificidad | 10 | — | El requisito especifica con precisión los valores: 5 intentos fallidos, periodo de 10 minutos, bloqueo de 15 minutos. |
| atomicidad | 10 | — | El requisito expresa un solo comportamiento: bloqueo tras 5 intentos fallidos en 10 minutos. No mezcla requisitos independientes. |
| completitud | 10 | — | El requisito incluye todos los elementos necesarios: actor (cliente registrado), condición (5 intentos fallidos consecutivos en 10 minutos), acción (bloquear cuenta), duración (15 minutos). |
| consistencia | 10 | — | No hay contradicciones internas ni con el contexto del proyecto (tienda en línea, política de seguridad). |
| factibilidad | 10 | — | El comportamiento descrito es técnicamente factible con mecanismos comunes de control de intentos y temporización. |
| verificabilidad | 10 | — | El requisito permite verificar objetivamente: se puede probar que tras 5 intentos fallidos en 10 minutos la cuenta se bloquea 15 minutos y rechaza accesos. |
| trazabilidad | 10 | — | Cuenta con identificador único REQ-AUT-03 y menciona su origen (política de seguridad de la tienda en línea), permitiendo relación con necesidad, diseño, implementación y prueba. |
| ausencia_ambiguedad | 10 | — | No contiene términos subjetivos o vagos como rápido, fácil, adecuado, intuitivo, suficiente, etc. Todos los términos son precisos y medibles. |
| criterios_aceptacion | 10 | — | Los criterios de aceptación están explícitamente definidos y son verificables: tres escenarios Given/When/Then que cubren el bloqueo, desbrague tras 15 minutos y reset al éxito. |

</details>

<details><summary>Corrida 3 — análisis <code>b71d9cc1-d795-4a57-9482-fd4a246ee4ed</code></summary>

**Diagnóstico:** El requisito REQ-AUT-03 es ejemplar: claro, específico, atómico, completo, consistente, factible, verificable, trazable, libre de ambigüedades y con criterios de aceptación bien definidos. No requiere modificaciones.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 10 | — | El requisito es claro y sin interpretaciones contradictorias: 'El sistema deberá bloquear durante 15 minutos la cuenta de un cliente registrado cuando se produzcan 5 intentos fallidos consecutivos de inicio de sesión dentro de un periodo de 10 minutos.' |
| especificidad | 10 | — | Expresa con precisión el comportamiento: 5 intentos fallidos consecutivos dentro de 10 minutos → bloqueo de 15 minutos. Incluye umbrales numéricos exactos y condiciones temporales. |
| atomicidad | 10 | — | El requisito expresa una sola regla de comportamiento: bloqueo tras 5 fallos en 10 minutos. No combina requisitos independientes. |
| completitud | 10 | — | Incluye toda la información necesaria: actor (cliente registrado), condición (5 intentos fallidos consecutivos en 10 minutos), acción (bloqueo de 15 minutos) y alcance (rechazo de inicios de sesión). |
| consistencia | 10 | — | No hay contradicciones internas ni con el contexto del proyecto (tienda en línea con política de seguridad de bloqueo temporal tras intentos fallidos). |
| factibilidad | 10 | — | Es factible implementar un mecanismo de conteo de intentos fallidos con ventana deslizante de 10 minutos y temporizador de bloqueo de 15 minutos utilizando tecnologías estándar. |
| verificabilidad | 10 | — | Permite verificar objetivamente: se pueden diseñar pruebas que inyecten 5 fallos en <10 min y confirmen el bloqueo de 15 min, o que tras 15 min permita login exitoso. |
| trazabilidad | 10 | — | Tiene un identificador único (REQ-AUT-03) y declara su origen (política de seguridad de la tienda en línea), lo que permite relacionarlo con necesidad, diseño, implementación y prueba. |
| ausencia_ambiguedad | 10 | — | No contiene términos subjetivos o vagos. Todos los elementos son cuantificados: 5 intentos, 10 minutos, 15 minutos, cuenta registrada, inicio de sesión. |
| criterios_aceptacion | 10 | — | Incluye tres criterios de aceptación explícitos en formato Dado/Cuándo/Entonces que cubren el comportamiento esperado: activación del bloqueo, recuperación tras tiempo, y reset en éxito. |

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
| **B1** Detecta los términos vagos (rápida / sencilla / relevantes) | ✅ rápida, sencilla | ✅ rápida, sencilla, relevantes | ✅ rápido, sencillo, relevantes |
| **B2** Formula preguntas de aclaración | ✅ 6 preguntas | ✅ 6 preguntas | ✅ 3 preguntas |
| **B3** Mejora el requisito (versión mejorada con delta > 0) | ✅ delta 21 | ✅ delta 7 | ✅ delta 15 |
| **B4** No inventa valores numéricos | ✅ ninguno | ✅ ninguno | ✅ ninguno |
| **B5** Con las respuestas del stakeholder el requisito final supera al original | ✅ original 51 → final tras aclarar 79 | ✅ original 53 → final tras aclarar 90 | ✅ original 53 → final tras aclarar 86 |
| **B6** (informativa) Tras aclarar quedan menos datos por definir | ✅ 5 → 1 pendientes | ✅ 6 → 0 pendientes | ✅ 4 → 0 pendientes |
| **B7** Tras aclarar no inventa valores numéricos | ✅ ninguno | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 1 — análisis <code>3d8734d5-7317-44ee-9a2e-f7b4eab8fe21</code></summary>

**Diagnóstico:** El requisito describe una funcionalidad deseable pero carece de especificidad, criterios medibles y trazabilidad. Los términos 'rápida' y 'sencilla' son ambiguos y no permiten verificar su cumplimiento. Falta información esencial sobre los campos de búsqueda, la relevancia de los resultados y metas de usabilidad y rendimiento. Se requiere definir criterios de aceptación claros y un identificador único para mejorar su calidad.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 6 | 8 | El requisito menciona 'buscar productos de forma rápida y sencilla', lo cual es comprensible, pero los adjetivos 'rápida' y 'sencilla' introducen ambigüedad sin criterios medibles de lo que constituye velocidad o facilidad de uso. |
| especificidad | 5 | 6 | El requisito establece que el sistema debe permitir buscar productos y mostrar resultados relevantes, pero no especifica qué atributos de los productos pueden usarse como criterios de búsqueda (nombre, categoría, marca, precio, etc.) ni qué constituye un resultado 'relevante'. |
| atomicidad | 8 | 9 | El requisito describe una única funcionalidad principal: buscar productos y mostrar resultados relevantes. Aunque incluye cualidades como 'rápida' y 'sencilla', estas no representan requisitos funcionales independientes, sino atributos de la misma funcionalidad. |
| completitud | 4 | 5 | Falta información esencial para el desarrollo: no se especifica en qué campos se puede buscar, cómo se determina la relevancia de los resultados, ni qué se considera 'rápida' o 'sencilla' desde el punto de vista técnico o de experiencia de usuario. |
| consistencia | 8 | 8 | No se observan contradicciones internas en el requisito. Es consistente con el contexto del proyecto (tienda en línea de artículos deportivos), donde la búsqueda de productos es una funcionalidad esperada y coherente. |
| factibilidad | 7 | 8 | La búsqueda de productos y la presentación de resultados son funcionalidades factibles en una tienda en línea. Sin embargo, la falta de definición de 'rápida' y 'sencilla' dificulta saber si las metas de rendimiento son razonables dadas las restricciones del proyecto (no especificadas). |
| verificabilidad | 4 | 6 | No es posible verificar objetivamente si la búsqueda es 'rápida' y 'sencilla' ni si los resultados son 'relevantes', ya que estos términos no tienen criterios medibles definidos en el requisito. |
| trazabilidad | 3 | 7 | El requisito no incluye un identificador único (como REQ-1) ni menciona su origen (necesidad del usuario, objetivo de negocio, etc.), lo que dificulta su trazabilidad a diseño, implementación o pruebas. |
| ausencia_ambiguedad | 3 | 9 | El requisito contiene los términos subjetivos 'rápida' (línea: 'buscar productos de forma rápida') y 'sencilla' (misma línea), que no definen un umbral medible y pueden interpretarse de forma distinta según el interlocutor. |
| criterios_aceptacion | 3 | 6 | El requisito no incluye condiciones ni criterios de aceptación explícitos ni implícitos que permitan determinar cuándo se considera satisfecho. No hay un formato Dado/Cuando/Entonces ni umbrales definidos para velocidad, facilidad o relevancia. |

**Preguntas:**

- ¿En qué atributos de los productos puede el cliente realizar la búsqueda (nombre, descripción, categoría, marca, precio, etc.)?
- ¿Qué se considera un resultado 'relevante'? ¿Debe coincidir el término de búsqueda con el título, descripción, etiquetas u otros campos?
- ¿Cuál es el tiempo máximo aceptable para que el sistema devuelva los resultados de una búsqueda para considerarla 'rápida'?
- ¿Cuántos pasos o interacciones debe realizar el cliente para ejecutar una búsqueda y ver los resultados para considerarla 'sencilla'?
- ¿El requisito necesita un identificador único para su trazabilidad?
- ¿Cuál es la necesidad de negocio o del usuario que este requisito satisface (por ejemplo, mejorar la experiencia de usuario, aumentar las conversiones, reducir la tasa de abandono)?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá permitir a los clientes buscar productos del catálogo ingresando un término de búsqueda sobre los siguientes atributos: [POR DEFINIR: campos buscables, p. ej. nombre, categoría, marca, precio].
REQ-2: El sistema deberá mostrar los resultados de la búsqueda en un tiempo de respuesta de [POR DEFINIR: tiempo máximo de respuesta] o menos.
REQ-3: El cliente deberá poder ejecutar una búsqueda en un máximo de [POR DEFINIR: número máximo de pasos o interacciones que se considera 'sencillo'] interacciones.
REQ-4: El sistema deberá ordenar o filtrar los resultados según el siguiente criterio de relevancia: [POR DEFINIR: criterio de relevancia, p. ej. coincidencia del término en título o descripción].
```

**Criterios de aceptación:**

- Dado un cliente en la tienda en línea, cuando ingresa un término en el campo de búsqueda y la ejecuta, entonces el sistema busca coincidencias en [POR DEFINIR: campos buscables] y muestra los productos correspondientes.
- Dado un cliente que ejecuta una búsqueda, cuando el sistema procesa la consulta, entonces los resultados se muestran en [POR DEFINIR: tiempo máximo de respuesta] o menos.
- Dado un cliente en la tienda, cuando realiza una búsqueda desde [POR DEFINIR: punto de inicio], entonces completa la búsqueda en un máximo de [POR DEFINIR: número máximo de interacciones] interacciones.
- Dado un conjunto de productos que coinciden con el término buscado, cuando el sistema muestra los resultados, entonces estos se presentan según [POR DEFINIR: criterio de relevancia].

**Tras responder las preguntas** (análisis `495a381e-518a-4f6e-8220-515849e7180c`): estado COMPLETED, puntaje original 54, mejorado 79.

```text
[POR DEFINIR: identificador único del sub-requisito 1]: El sistema deberá proporcionar un único cuadro de texto de búsqueda, visible en la parte superior de todas las páginas, que permita a clientes registrados e invitados buscar productos por nombre, marca y categoría, sin requerir inicio de sesión ni el uso de filtros.
[POR DEFINIR: identificador único del sub-requisito 2]: El sistema deberá mostrar los resultados de la búsqueda en un máximo de 2 segundos desde que el cliente envía la consulta, para un catálogo de hasta 20000 productos.
[POR DEFINIR: identificador único del sub-requisito 3]: El sistema deberá incluir en los resultados únicamente los productos en los que el texto buscado aparezca en el nombre, la marca o la categoría.
[POR DEFINIR: identificador único del sub-requisito 4]: El sistema deberá ordenar los resultados mostrando primero las coincidencias en el nombre del producto y después las coincidencias en marca o categoría, ordenadas por unidades vendidas.
```

</details>

<details><summary>Corrida 2 — análisis <code>62d12f1c-b608-4df0-aafc-b3593b441a7d</code></summary>

**Diagnóstico:** El requisito expresa una intención clara pero carece de especificidad, medibilidad y trazabilidad necesarios para su implementación y verificación. Los términos subjetivos impiden una evaluación objetiva y requieren definición de umbrales y criterios claros.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 7 | 7 | El requisito es comprensible en su intención general, pero los términos 'rápida y sencilla' no definen parámetros objetivos que eliminen interpretaciones contradictorias sobre qué se considera rápido o sencillo. |
| especificidad | 5 | 6 | El requisito menciona 'buscar productos' y 'mostrando resultados relevantes', pero no especifica qué atributos del producto pueden buscarse (nombre, categoría, marca, etc.), ni qué criterios determinan la relevancia de los resultados. |
| atomicidad | 6 | 4 | El requisito combina dos aspectos: la búsqueda de productos y la presentación de resultados relevantes, los cuales podrían considerarse separados aunque estén estrechamente relacionados. |
| completitud | 5 | 5 | Faltan detalles esenciales como los atributos de producto sobre los que se puede buscar, los algoritmos o reglas para determinar relevancia, y los umbrales de tiempo o pasos para considerar la búsqueda rápida y sencilla. |
| consistencia | 8 | 8 | No se detectan contradicciones internas ni con el contexto del proyecto (tienda en línea de artículos deportivos con catálogo público y acceso como invitado o registrado). |
| factibilidad | 8 | 8 | Permitir búsquedas de productos y mostrar resultados relevantes es factible con tecnologías estándar de búsqueda en catálogos de tiendas en línea. |
| verificabilidad | 4 | 6 | No incluye criterios medibles ni condiciones observables que permitan verificar objetivamente si la búsqueda es 'rápida y sencilla' o si los resultados son 'relevantes'. |
| trazabilidad | 4 | 3 | El requisito no incluye un identificador único ni referencia explícita a una necesidad de origen, lo que dificulta su relación con diseño, implementación y pruebas. |
| ausencia_ambiguedad | 3 | 7 | Los términos 'rápida', 'sencilla' y 'relevantes' son subjetivos y no definidos, lo que introduce ambigüedad en la interpretación. |
| criterios_aceptacion | 3 | 6 | No se incluyen criterios de aceptación explícitos ni condiciones medibles de las que puedan derivarse, lo que impide determinar verificablemente cuándo el requisito está satisfecho. |

**Preguntas:**

- ¿Qué atributos de los productos pueden utilizarse como criterios de búsqueda?
- ¿Qué se considera un resultado relevante en el contexto de esta tienda deportiva?
- ¿Cuál es el tiempo máximo aceptable para que la búsqueda se considere rápida?
- ¿Cuántos pasos o interacciones máximo debería requerir la búsqueda para considerarse sencilla?
- ¿El requisito necesita un identificador único para trazabilidad?
- ¿Qué criterios de aceptación específicos deben cumplirse para considerar el requisito satisfecho?

**Requisito mejorado:**

```text
[POR DEFINIR: identificador único del requisito de búsqueda]: El sistema deberá permitir a los clientes buscar productos del catálogo ingresando un texto de búsqueda, de modo que la respuesta se muestre en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta, ej. 2 segundos] y la acción de buscar requiera como máximo [POR DEFINIR: número máximo de pasos o interacciones].
[POR DEFINIR: identificador único del requisito de resultados relevantes]: El sistema deberá mostrar los resultados de la búsqueda ordenados según [POR DEFINIR: criterios que determinan la relevancia, ej. coincidencia de texto, popularidad, disponibilidad], tomando en cuenta los siguientes campos del producto: [POR DEFINIR: campos de búsqueda permitidos, ej. nombre, categoría, marca].
```

**Criterios de aceptación:**

- Dado un cliente (invitado o registrado) en la tienda, cuando ingresa un texto de búsqueda y la ejecuta, entonces el sistema muestra los resultados en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta].
- Dado un cliente (invitado o registrado) en la tienda, cuando realiza una búsqueda, entonces la acción de buscar no requiere más de [POR DEFINIR: número máximo de pasos o interacciones].
- Dado un cliente que ingresa un texto de búsqueda, cuando el sistema muestra los resultados, entonces únicamente incluye productos que coincidan en [POR DEFINIR: campos de búsqueda permitidos] según [POR DEFINIR: criterios de relevancia].
- Dado un conjunto de resultados de búsqueda, cuando se muestran al cliente, entonces están ordenados según [POR DEFINIR: criterios de relevancia y orden].

**Tras responder las preguntas** (análisis `ffe86cda-35f5-4ca5-83f6-eecb7382932d`): estado COMPLETED, puntaje original 63, mejorado 90.

```text
REQ-1: El sistema deberá mostrar un único cuadro de texto de búsqueda en la parte superior de todas las páginas, accesible para clientes registrados e invitados.
REQ-2: El sistema deberá permitir a cualquier cliente (registrado o invitado) buscar productos ingresando un término en dicho cuadro de texto, sin requerir inicio de sesión ni uso de filtros. La búsqueda se realizará sobre el nombre, la marca y la categoría del producto.
REQ-3: El sistema deberá mostrar los resultados de la búsqueda en un tiempo máximo de 2 segundos con un catálogo de hasta 20,000 productos.
REQ-4: El sistema deberá mostrar como resultados únicamente los productos cuyo nombre, marca o categoría contengan el texto buscado, presentando primero las coincidencias en el nombre y después las demás coincidencias, ordenadas estas últimas por unidades vendidas.
```

</details>

<details><summary>Corrida 3 — análisis <code>6be65303-f2dd-4c3c-bb8d-7fef8172280b</code></summary>

**Diagnóstico:** El requisito establece una necesidad básica de búsqueda pero carece de definiciones medibles para términos clave como 'rápido', 'sencillo' y 'relevantes', lo que afecta su verificabilidad, especificidad y ausencia de ambigüedad. Aunque es atómico y factible, requiere criterios objetivos para ser desarrollable y testeable.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 6 | 7 | El requisito establece que los clientes deben poder buscar productos 'de forma rápida y sencilla', pero no define qué se considera 'rápido' ni 'sencillo', lo que permite interpretaciones subjetivas. |
| especificidad | 5 | 6 | El requisito indica que el sistema debe permitir buscar productos y mostrar resultados 'relevantes', pero no especifica qué criterios determinan la relevancia (por ejemplo, coincidencia de texto, popularidad, filtros aplicados). |
| atomicidad | 8 | 8 | El requisito expresa una única funcionalidad principal: permitir la búsqueda de productos con resultados relevantes. Aunque incluye cualidades como 'rápido' y 'sencillo', estas son características de la misma función, no requisitos independientes. |
| completitud | 4 | 5 | Falta información esencial como el umbral de tiempo para considerar la búsqueda 'rápida', los criterios para definir qué resultados son 'relevantes', y si hay límites en la cantidad de resultados mostrados. |
| consistencia | 7 | 8 | No se detectan contradicciones internas en el requisito. Es coherente con el contexto de una tienda en línea donde la búsqueda de productos es una funcionalidad esperada. |
| factibilidad | 8 | 8 | Permitir búsquedas de productos y mostrar resultados relevantes es factible en una tienda en línea estándar, usando tecnologías comunes como índices de búsqueda o filtrado por palabras clave. |
| verificabilidad | 4 | 6 | No es posible verificar objetivamente si la búsqueda es 'rápida' o 'sencilla' sin umbrales definidos, ni si los resultados son 'relevantes' sin criterios medibles de relevancia. |
| trazabilidad | 5 | 7 | El requisito no incluye un identificador único (como REQ-1) ni menciona su origen (por ejemplo, necesidad del usuario o stakeholder), lo que dificulta su trazabilidad a diseño, código o pruebas. |
| ausencia_ambiguedad | 3 | 7 | Los términos 'rápido', 'sencillo' y 'relevantes' son subjetivos y no definidos, lo que introduce ambigüedad en la interpretación del requisito. |
| criterios_aceptacion | 3 | 6 | El requisito no incluye condiciones medibles ni criterios de aceptación explícitos (como tiempo de respuesta, número de pasos o reglas de relevancia), lo que impide determinar cuándo está satisfecho. |

**Preguntas:**

- ¿Cuál es el tiempo máximo aceptable (en segundos) para que una búsqueda se considere 'rápida'?
- ¿Cuántos pasos o interacciones (por ejemplo, clics, teclas) se consideran aceptables para que la búsqueda sea 'sencilla'?
- ¿Qué criteria deben cumplir los productos para que sus resultados se consideren 'relevantes' (por ejemplo, coincidencia de texto en nombre, descripción, categoría, popularidad)?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá permitir a los clientes buscar productos del catálogo mediante [POR DEFINIR: mecanismo de búsqueda, p. ej. campo de texto, filtros, categorías].
REQ-2: El sistema deberá mostrar los resultados de la búsqueda en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta] desde que el cliente envía la consulta.
REQ-3: El cliente podrá realizar una búsqueda en un máximo de [POR DEFINIR: número máximo de pasos o interacciones] desde la pantalla donde se inicia la búsqueda.
REQ-4: El sistema deberá ordenar o seleccionar los resultados según los siguientes criterios de relevancia: [POR DEFINIR: criterios objetivos de relevancia, p. ej. coincidencia de texto en nombre, descripción o categoría].
```

**Criterios de aceptación:**

- Dado un cliente en la tienda en línea, cuando ingresa una consulta mediante [POR DEFINIR: mecanismo de búsqueda], entonces el sistema muestra los productos del catálogo que cumplen los criterios de búsqueda.
- Dado un cliente que envía una consulta de búsqueda, cuando el sistema procesa la consulta, entonces los resultados se muestran en un tiempo máximo de [POR DEFINIR: umbral de tiempo de respuesta].
- Dado un cliente que desea buscar un producto, cuando inicia desde [POR DEFINIR: pantalla de inicio de la búsqueda], entonces completa la búsqueda en un máximo de [POR DEFINIR: número máximo de pasos o interacciones].
- Dado una consulta de búsqueda ejecutada, cuando el sistema genera los resultados, entonces estos cumplen los criterios de relevancia definidos en [POR DEFINIR: criterios objetivos de relevancia].

**Tras responder las preguntas** (análisis `7f864a52-084f-4a85-a955-6104e36a4f4f`): estado COMPLETED, puntaje original 65, mejorado 86.

```text
REQ-1: El sistema deberá permitir a los clientes, tanto registrados como invitados, buscar productos desde un único cuadro de texto visible en la parte superior de todas las páginas, sin requerir inicio de sesión ni uso de filtros.
REQ-2: La búsqueda deberá realizarse sobre los campos nombre, marca y categoría del producto.
REQ-3: Los resultados deberán mostrarse en un tiempo máximo de 2 segundos con un catálogo de hasta 20000 productos.
REQ-4: El sistema mostrará como resultados únicamente los productos cuyo nombre, marca o categoría contenga el texto buscado, ordenados de la siguiente forma: primero las coincidencias en el nombre y luego el resto, ordenadas por unidades vendidas.
```

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
| **C1** Detecta la contradicción (consistencia ≤ 3) | ✅ consistencia 2 | ✅ consistencia 2 | ✅ consistencia 2 |
| **C2** Señala la información faltante y pregunta | ✅ 5 faltantes, 3 preguntas | ✅ 4 faltantes, 3 preguntas | ✅ 4 faltantes, 4 preguntas |
| **C3** Deja explícito lo que falta con [POR DEFINIR] | ✅ 7 pendientes | ✅ 5 pendientes | ✅ 4 pendientes |
| **C4** No resuelve la contradicción por su cuenta (la deja pendiente) | ✅ | ✅ | ✅ |
| **C5** No inventa valores numéricos | ✅ ninguno | ✅ ninguno | ✅ ninguno |

<details><summary>Corrida 1 — análisis <code>d3d5c80b-5dcb-4f41-b476-b4eb2586fac4</code></summary>

**Diagnóstico:** El requisito es contradictorio, ambiguo y carece de especificidad necesaria para desarrollo y prueba. Mezcla múltiples ideas sin aclarar su relación y omite detalles críticos como datos requeridos, formato y mecanismo de activación. Requieren una redefinición clara para resolver la contradicción entre lo automático y lo manual.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 4 | 6 | El requisito presenta una contradicción lógica: 'generarse automáticamente cada día, pero solo cuando el gerente los solicite manualmente' implica simultaneidad entre automático y manual, lo que genera confusión sobre cuándo y cómo se dispara la generación. |
| especificidad | 3 | 4 | Falta especificar qué se entiende por 'datos necesarios', qué formato tiene el reporte, qué sistema lo genera, y cómo se relaciona la solicitud manual con el disparo diario. La frase 'datos necesarios' es demasiado amplia para guiar desarrollo o prueba. |
| atomicidad | 3 | 3 | El requisito mezcla al menos tres aspectos independientes: (1) frecuencia automática diaria, (2) condición de solicitud manual, y (3) inclusión de datos necesarios. Estos podrían ser requisitos separados, ya que uno puede cambiar sin afectar los otros. |
| completitud | 3 | 4 | Faltan elementos esenciales: qué constituye un 'reporte de ventas', qué datos son 'necesarios', cómo se interpreta 'cada día' (zona horaria, hora exacta), y cómo se registra o valida la 'solicitud manual' del gerente. |
| consistencia | 2 | 3 | Hay una contradicción interna directa: 'generarse automáticamente cada día' (implícitamente sin intervención) contradice 'solo cuando el gerente los solicite manualmente' (requiere intervención humana). No pueden ser ciertos al mismo tiempo. |
| factibilidad | 5 | 7 | Asumiendo que se resuelve la contradicción, generar reportes diarios mediante programación o bajo solicitud es factible en un sistema web de ventas. No hay restricciones técnicas manifiestas que lo hagan imposible. |
| verificabilidad | 3 | 5 | No se puede verificar objetivamente el cumplimiento porque no hay criterios medibles: ¿cada día a qué hora? ¿Cómo se prueba que se generó 'solo cuando' se solicitó? ¿Cómo se mide si los datos incluidos son 'necesarios'? |
| trazabilidad | 4 | 6 | El requisito no incluye un identificador único (como REQ-1), ni menciona su origen (necesidad del gerente, norma, objetivo de negocio). Aunque el contexto menciona gerentes y web, no hay vínculo explícito a un stakeholder o motivo. |
| ausencia_ambiguedad | 3 | 7 | Términos ambiguos: 'datos necesarios' (¿qué datos? ¿cuántos?), 'cada día' (¿inicio/fin de día? ¿zona horaria?), 'automáticamente' (en contraste con manual, genera confusión). |
| criterios_aceptacion | 2 | 4 | No se incluyen criterios de aceptación ni condiciones medibles que permitan determinar cuándo el requisito está satisfecho. No hay estructura Dado/Cuando/Entonces ni valores umbral. |

**Preguntas:**

- ¿El reporte debe generarse todos los días a una hora específica sin intervención, o solo cuando el gerente lo solicite mediante una acción explícita en el sistema?
- ¿Qué datos específicos deben incluirse en el reporte de ventas (por ejemplo: ventas totales, por producto, por tienda, hora de venta, etc.)?
- ¿En qué formato debe entregarse el reporte (PDF, Excel, CSV, etc.) y cómo se notifica al gerente que está listo?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá generar los reportes de ventas [POR DEFINIR: resolver contradicción entre generación automática diaria y generación solo bajo solicitud manual del gerente].
REQ-2: Si la generación es automática diaria, el sistema deberá generar el reporte a las [POR DEFINIR: hora exacta] en la zona horaria [POR DEFINIR: zona horaria].
REQ-3: Si la generación es bajo solicitud, el gerente podrá solicitar la generación del reporte de ventas mediante [POR DEFINIR: mecanismo de solicitud, p. ej. botón en la web] desde la aplicación web.
REQ-4: El reporte de ventas generado deberá incluir [POR DEFINIR: lista específica de datos del reporte, p. ej. ventas por tienda, producto, período] y presentarse en formato [POR DEFINIR: formato del reporte, p. ej. PDF, Excel].
```

**Criterios de aceptación:**

- Dado que se cumple la condición de disparo [POR DEFINIR: automática diaria a hora exacta O solicitud manual del gerente], cuando el sistema procesa la generación, entonces produce el reporte de ventas correspondiente al período [POR DEFINIR: período cubierto, p. ej. día actual].
- Dado que el gerente accede desde la web, cuando solicita el reporte mediante [POR DEFINIR: mecanismo de solicitud] (si aplica el modo manual), entonces recibe el reporte en formato [POR DEFINIR: formato del reporte] con [POR DEFINIR: lista de datos del reporte].
- Dado que se generó un reporte, cuando el gerente lo abre, entonces contiene exactamente [POR DEFINIR: lista de datos del reporte] en formato [POR DEFINIR: formato del reporte].

</details>

<details><summary>Corrida 2 — análisis <code>10776b5a-b82c-4194-ba9a-bc100ea8b532</code></summary>

**Diagnóstico:** El requisito es contradictorio al afirmar que los reportes se generan automáticamente cada día pero solo cuando el gerente los solicite manualmente, lo cual es lógicamente imposible. Además, falta especificar qué constitutes 'datos necesarios', lo que impide la verificabilidad y el desarrollo. Se necesita resolver la contradicción y definir claramente el contenido y la condición de generación para que el requisito sea útil.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | 3 | El requisito contiene una contradicción lógica: 'deben generarse automáticamente cada día, pero solo cuando el gerente los solicite manualmente' implica que la generación es automática y manual a la vez, lo que son condiciones mutuamente excluyentes. |
| especificidad | 3 | 2 | Falta especificar qué se entiende por 'datos necesarios': no se indica qué campos, métricas, desgloses o niveles de detalle (por tienda, por producto, por vendedor, etc.) deben incluirse en el reporte. |
| atomicidad | 2 | 6 | El requisito combina múltiples condiciones independientes en una sola oración: (1) generación automática diaria, (2) condicionada a solicitud manual del gerente, (3) inclusión de datos necesarios. Cada una es un requisito distinto y potencialmente contradictorio. |
| completitud | 3 | 2 | Falta información esencial para desarrollar y probar: ¿qué constituye 'datos necesarios'? ¿Cuál es el formato del reporte? ¿Dónde se almacena o se envía? ¿Qué ocurre si el gerente no lo solicita? La contradicción no resuelta impide comprender el comportamiento esperado. |
| consistencia | 2 | 3 | Contradicción interna explícita: 'generarse automáticamente cada día' vs. 'solo cuando el gerente los solicite manualmente'. Estos son comportamientos opuestos: uno ocurre sin intervención, el otro requiere acción directa. No puede ser ambos simultáneamente. |
| factibilidad | 5 | 7 | Sin resolver la contradicción, no se puede determinar qué comportamiento implementar. Si se asume que la intención fue 'generación automática diaria disponible para que el gerente la consulte', sería factible. Pero tal como está, la lógica es imposible de implementar tal cual. |
| verificabilidad | 2 | 3 | No se puede verificar objetivamente porque: (a) la condición de generación es contradictoria (¿se generó automáticamente o solo si se solicitó?), y (b) no hay criterios medibles para 'datos necesarios'. No hay forma de pasar/failar una prueba sin resolver estas ambigüedades. |
| trazabilidad | 4 | 6 | No se proporciona un identificador único (como REQ-1) ni se vincula explícitamente a una necesidad de negocio o actor más allá de 'gerente'. Aunque el contexto menciona que los gerentes consultan reportes desde la web, el requisito no lo referencia como origen. |
| ausencia_ambiguedad | 3 | 4 | El término 'datos necesarios' es ambiguo y subjetivo: no define qué constituye lo 'necesario', lo cual depende del rol, contexto o juicio personal. No es medible ni verificable. |
| criterios_aceptacion | 2 | 2 | No se incluyen criterios de aceptación explícitos ni condiciones medibles de las que puedan derivarse. Sin una definición clara de cuándo se genera el reporte y qué debe contener, no es posible determinar si el requisito está satisfecho. |

**Preguntas:**

- ¿El reporte de ventas debe generarse automáticamente todos los días (sin intervención del gerente) y simplemente estar disponible para que él lo consulte cuando quiera?
- ¿O bien, el reporte solo debe generarse en los días en que el gerente lo solicite explícitamente?
- ¿Qué datos específicos debe incluir el reporte de ventas? Por favor, indique los campos, métricas y niveles de detalle requeridos (por ejemplo: total de ventas, unidades por producto, ventas por tienda, comparativo con día anterior, etc.).

**Requisito mejorado:**

```text
REQ-1: El sistema deberá generar el reporte de ventas diario [POR DEFINIR: resolver contradicción entre generación automática diaria y generación solo bajo solicitud manual del gerente].
REQ-2: El gerente podrá consultar el reporte de ventas desde la web.
REQ-3: El reporte de ventas deberá incluir [POR DEFINIR: lista específica de campos y métricas que debe contener el reporte].
REQ-4: El sistema deberá almacenar el reporte generado en [POR DEFINIR: ubicación o destino del reporte] con formato [POR DEFINIR: formato del reporte].
```

**Criterios de aceptación:**

- Dado que se cumple [POR DEFINIR: condición de generación del reporte], cuando el sistema ejecuta la generación, entonces el reporte de ventas queda disponible en [POR DEFINIR: ubicación o destino].
- Dado un gerente autenticado en la web, cuando accede al módulo de reportes, entonces puede consultar el reporte de ventas disponible.
- Dado un reporte de ventas generado, cuando el gerente lo consulta, entonces el reporte contiene exactamente [POR DEFINIR: lista específica de campos y métricas].
- Dado un reporte generado, cuando se abre, entonces tiene el formato [POR DEFINIR: formato del reporte] y se encuentra en [POR DEFINIR: ubicación o destino].

</details>

<details><summary>Corrida 3 — análisis <code>d9fd62ea-ca45-49b2-b67c-2c2ec6437d9d</code></summary>

**Diagnóstico:** El requisito presenta una contradicción lógica crítica entre generación automática y manual, carece de especificidad en los datos necesarios, es compuesto y no cuenta con criterios de aceptación verificables. Antes de poder mejorarlo, es necesario resolver la contradicción y definir los datos esenciales del reporte.

| Criterio | Original | Mejorado | Hallazgo (original) |
|---|---|---|---|
| claridad | 3 | 6 | El requisito contiene una contradicción lógica: 'deben generarse automáticamente cada día, pero solo cuando el gerente los solicite manualmente' es contradictorio porque lo automático excluye la solicitud manual y viceversa. |
| especificidad | 4 | 5 | Aunque se menciona 'reportes de ventas' y 'datos necesarios', no se especifican qué datos son necesarios ni el formato, contenido o alcance del reporte. |
| atomicidad | 2 | 8 | El requisito combina múltiples aspectos independientes: frecuencia de generación (diaria), condición de activación (solicitud manual), y contenido (datos necesarios), lo que lo hace compuesto. |
| completitud | 3 | 4 | Falta información esencial: qué constituye un 'reporte de ventas', qué datos son 'necesarios', cómo se interpreta la condición contradictoria entre automático y manual, y qué formato o medio se usa para generarlo. |
| consistencia | 2 | 3 | Contradicción interna: 'generarse automáticamente cada día' y 'solo cuando el gerente los solicite manualmente' son mutuamente excluyentes. No pueden ser verdaderos al mismo tiempo. |
| factibilidad | 5 | 7 | No hay información que haga el requisito técnicamente imposible de implementar, pero la contradicción interna impide una implementación coherente hasta que se resuelva. |
| verificabilidad | 3 | 5 | No se puede verificar objetivamente el cumplimiento debido a la contradicción y la falta de definición de 'datos necesarios'. No hay criterios observables claros. |
| trazabilidad | 4 | 8 | No se proporciona un identificador único ni se vincula explícitamente a una necesidad de negocio, stakeholder o objetivo del sistema de ventas para tiendas. |
| ausencia_ambiguedad | 3 | 7 | El término 'datos necesarios' es vago y subjetivo: no se especifica qué datos son necesarios ni según qué criterio. |
| criterios_aceptacion | 2 | 4 | No se incluyen criterios de aceptación medibles ni condiciones verificables. No se puede determinar cuándo el requisito está satisfecho debido a la contradicción y la vaguedad. |

**Preguntas:**

- ¿La generación del reporte debe ser automática todos los días a una hora fija, o debe ocurrir únicamente cuando el gerente la solicite manualmente a través de la interfaz web?
- ¿Qué datos específicos deben incluirse en el reporte de ventas? Por ejemplo: ¿ventas totales, ventas por tienda, por producto, por categoría, por horario, etc?
- ¿El requisito debe tener un identificador único para su trazabilidad?
- ¿A qué necesidad de negocio o objetivo del gerente responde este requisito? Por ejemplo: ¿monitorear desempeño diario, tomar decisiones de reposición, etc?

**Requisito mejorado:**

```text
REQ-1: El sistema deberá generar el reporte de ventas [POR DEFINIR: resolver contradicción entre generación automática diaria y generación solo bajo solicitud manual del gerente].
REQ-2: El gerente podrá consultar el reporte de ventas desde la aplicación web.
REQ-3: El reporte de ventas deberá incluir [POR DEFINIR: lista específica de datos que debe contener el reporte].
```

**Criterios de aceptación:**

- Dado que el sistema de ventas está en operación, cuando se cumpla [POR DEFINIR: condición de generación: automática diaria o solicitud manual del gerente], entonces el sistema genera el reporte de ventas.
- Dado un gerente autenticado en la aplicación web, cuando accede a la sección de reportes, entonces puede consultar el reporte de ventas generado.
- Dado un reporte de ventas generado, cuando el gerente lo abre, entonces el reporte contiene [POR DEFINIR: lista específica de datos del reporte].

</details>
