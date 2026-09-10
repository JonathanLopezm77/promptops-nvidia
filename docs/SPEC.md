# LABORATORIO DE PROMPTOPS — ESPECIFICACIÓN COMPLETA DE LA APLICACIÓN

## 1. ROL

Actúa como un **arquitecto de software senior, desarrollador full-stack y especialista en Prompt Engineering, LLMs, PromptOps, evaluación de prompts, Quality Gates y sistemas Human-in-the-Loop**.

Tu objetivo es diseñar e implementar una aplicación web local que funcione como un **Laboratorio de PromptOps**.

No quiero una aplicación comercial ni una plataforma empresarial. Es un proyecto académico cuyo objetivo es demostrar de forma clara y funcional:

* Prompt Engineering.
* Optimización iterativa de prompts.
* Evaluación automática.
* Quality Gates.
* Observabilidad.
* Trazabilidad.
* Human-in-the-Loop.
* Ejecución controlada de prompts.
* Persistencia de resultados.

Debes priorizar una arquitectura sencilla, modular, mantenible y fácil de explicar académicamente.

---

# 2. OBJETIVO GENERAL

La aplicación permitirá que un usuario introduzca un prompt inicial y lo someta a un pipeline de PromptOps.

El flujo general será:

```text
PROMPT ORIGINAL
       ↓
PROMPT OPTIMIZER
       ↓
PROMPT MEJORADO
       ↓
PROMPT AUDITOR
       ↓
QUALITY GATES
       ↓
HUMAN IN THE LOOP
       ↓
APROBACIÓN
       ↓
EJECUCIÓN DEL PROMPT
       ↓
RESPUESTA FINAL
       ↓
HISTORIAL / POSTGRESQL
```

El sistema debe permitir múltiples iteraciones antes de llegar a la aprobación final.

---

# 3. TECNOLOGÍAS

Utiliza preferiblemente:

### Backend

* Python.
* FastAPI.
* PostgreSQL.
* SQLAlchemy o una alternativa razonable para ORM.
* Pydantic.
* Cliente HTTP apropiado para comunicarse con NVIDIA.
* `.env` para configuración.

### Frontend

* HTML.
* CSS.
* JavaScript vanilla.

No utilices React, Vue, Angular ni otros frameworks frontend salvo que exista una razón técnica fuerte y explícitamente justificada.

### Base de datos

PostgreSQL debe ejecutarse localmente.

### IA

Los modelos serán consumidos mediante las APIs disponibles de NVIDIA.

La arquitectura debe permitir cambiar de modelo fácilmente.

---

# 4. FILOSOFÍA DEL PROYECTO

La aplicación debe demostrar que PromptOps no consiste simplemente en enviar un prompt a una IA.

Debe existir un proceso observable:

```text
Entrada
   ↓
Optimización
   ↓
Evaluación
   ↓
Quality Gates
   ↓
Feedback
   ↓
Iteración
   ↓
Intervención humana
   ↓
Aprobación
   ↓
Ejecución
   ↓
Resultado
```

Cada etapa debe dejar trazabilidad.

---

# 5. ROLES DE LAS IAs

Inicialmente se utilizarán tres roles principales.

No es obligatorio utilizar tres modelos diferentes. Puedes utilizar el mismo modelo de NVIDIA para diferentes roles mediante diferentes system prompts si eso resulta más eficiente.

## IA 1 — PROMPT OPTIMIZER

Responsabilidad:

Recibir el prompt original y generar una versión mejorada.

Debe analizar, cuando sea pertinente:

* claridad;
* objetivo;
* contexto;
* instrucciones;
* restricciones;
* formato esperado;
* ambigüedades;
* redundancias;
* eficiencia;
* precisión;
* adecuación al problema.

Debe recibir feedback de iteraciones anteriores cuando existan.

Su resultado debe ser estructurado.

Como mínimo debe proporcionar:

```json
{
  "original_prompt": "...",
  "analysis": "...",
  "improved_prompt": "...",
  "changes": [],
  "reasoning_summary": "..."
}
```

No es necesario exponer razonamiento interno privado del modelo. La aplicación debe mostrar únicamente una explicación resumida y segura de los cambios realizados.

---

# 6. IA 2 — PROMPT AUDITOR

La segunda IA será responsable de auditar el prompt.

Debe utilizar EXACTAMENTE el marco de evaluación proporcionado al final de este documento.

El marco proporcionado incluye:

* 21 propiedades.
* 6 dimensiones.
* 4 Quality Gates.

No inventes Quality Gates adicionales.

No reemplaces los criterios proporcionados.

No modifiques sus definiciones.

La auditoría debe devolver información estructurada.

Debe incluir:

* estado de cada Gate;
* puntuaciones;
* observaciones;
* propiedades críticas;
* recomendaciones;
* versión optimizada cuando corresponda.

La respuesta del modelo debe ser validada antes de ser utilizada por el backend.

---

# 7. QUALITY GATES

Los Quality Gates proporcionados por el profesor/Gemini constituyen un requisito funcional de la aplicación.

Deben incorporarse al sistema de auditoría.

El sistema debe distinguir claramente:

* Gate PASS.
* Gate FAIL.
* Gate NO APLICA cuando el marco lo permita.

La aplicación debe poder mostrar visualmente los resultados.

Ejemplo:

```text
QUALITY GATES

✓ GATE 1 — PASÓ
✓ GATE 2 — PASÓ
✗ GATE 3 — NO PASÓ
✓ GATE 4 — PASÓ

Resultado: 3/4 Gates aprobados
```

El backend debe conservar el resultado completo, no únicamente el resultado final.

---

# 8. HUMAN IN THE LOOP

Esta es una característica central del proyecto.

El sistema NO debe ejecutar automáticamente el prompt final simplemente porque la auditoría sea positiva.

Debe existir una etapa explícita de intervención humana.

Cuando termine una iteración, el sistema debe entrar en un estado similar a:

```text
WAITING_HUMAN
```

El usuario debe poder revisar:

* prompt original;
* prompt mejorado;
* cambios realizados;
* evaluación;
* puntuaciones;
* Quality Gates;
* recomendaciones;
* historial de iteraciones.

El usuario tendrá como mínimo tres posibilidades:

### APROBAR

Aprueba la versión actual y permite pasar a la ejecución final.

### SOLICITAR NUEVA ITERACIÓN

El prompt vuelve al Optimizer.

Debe utilizarse como contexto:

* prompt actual;
* resultado de auditoría;
* Quality Gates;
* recomendaciones;
* feedback humano.

### EDITAR

El usuario puede modificar manualmente el prompt.

Después de editarlo, el sistema debe permitir volver a evaluarlo.

---

# 9. ITERACIONES

Debe existir soporte explícito para múltiples iteraciones.

Ejemplo:

```text
ITERACIÓN 1

Prompt original
       ↓
Optimizer
       ↓
Prompt V1
       ↓
Auditor
       ↓
Gates
       ↓
Humano solicita cambios


ITERACIÓN 2

Prompt V1
+
Feedback
       ↓
Optimizer
       ↓
Prompt V2
       ↓
Auditor
       ↓
Gates
       ↓
Humano solicita cambios


ITERACIÓN 3

Prompt V2
       ↓
Auditor
       ↓
Gates
       ↓
Humano aprueba
```

Cada iteración debe almacenarse.

El sistema debe poder mostrar la evolución.

Por ejemplo:

```text
Iteración 1 — 68/100 — 3/4 Gates
Iteración 2 — 82/100 — 3/4 Gates
Iteración 3 — 94/100 — 4/4 Gates
```

---

# 10. IA 3 — EJECUTOR FINAL

Después de que el humano apruebe una versión:

```text
PROMPT APROBADO
       ↓
FINAL EXECUTOR
       ↓
RESPUESTA
```

La IA ejecutora debe recibir exclusivamente el contexto necesario para producir la respuesta final.

Debe existir separación conceptual entre:

* Optimizer.
* Auditor.
* Executor.

El auditor no debe generar la respuesta final de la tarea original.

---

# 11. OBSERVABILIDAD

La interfaz debe permitir visualizar el proceso.

No quiero que el sistema parezca una caja negra.

Debe existir un timeline/log similar a:

```text
[09:30:01] Prompt recibido.
[09:30:02] Optimizer iniciado.
[09:30:05] Prompt mejorado.
[09:30:06] Auditor iniciado.
[09:30:09] Auditoría completada.
[09:30:10] Quality Gates ejecutados.
[09:30:12] 3/4 Gates aprobados.
[09:30:13] Esperando aprobación humana.
```

Debe mostrarse claramente en qué etapa está la ejecución.

---

# 12. ESTADOS

Diseña una máquina de estados apropiada.

Como referencia:

```text
CREATED
OPTIMIZING
AUDITING
GATING
WAITING_HUMAN
ITERATING
APPROVED
EXECUTING
COMPLETED
REJECTED
ERROR
```

Puedes modificar estos estados si consideras que existe una arquitectura mejor.

Evita estados ambiguos o transiciones imposibles.

---

# 13. POSTGRESQL

La aplicación debe guardar el historial completo.

Como mínimo deben conservarse:

### Ejecución

* ID.
* Fecha.
* Estado.
* Prompt original.
* Modelo utilizado.
* Fecha de finalización.

### Iteraciones

* ID.
* ID de ejecución.
* Número de iteración.
* Prompt de entrada.
* Prompt generado.
* Fecha.
* Estado.

### Auditoría

* Prompt auditado.
* Score.
* Propiedades evaluadas.
* Quality Gates.
* Recomendaciones.
* Resultado completo del auditor.

### Human-in-the-Loop

* Decisión.
* Feedback.
* Prompt editado si corresponde.
* Fecha.
* Iteración relacionada.

### Resultado

* Prompt aprobado.
* Respuesta final.
* Modelo utilizado.
* Fecha.

Evalúa cuidadosamente qué información debe estar normalizada en tablas y qué información puede almacenarse como JSONB.

No crees una base de datos innecesariamente compleja.

---

# 14. API BACKEND

Diseña una API REST clara.

Como referencia:

```text
POST   /api/runs
GET    /api/runs
GET    /api/runs/{id}

POST   /api/runs/{id}/iterate

POST   /api/runs/{id}/approve

POST   /api/runs/{id}/edit

POST   /api/runs/{id}/execute

GET    /api/runs/{id}/iterations
GET    /api/runs/{id}/audit
```

Puedes modificar estos endpoints si existe una arquitectura mejor.

Cada endpoint debe tener una responsabilidad clara.

---

# 15. FRONTEND

La aplicación debe ser visualmente sencilla.

Características:

* fondo negro;
* interfaz limpia;
* buen contraste;
* tipografía legible;
* pocos elementos decorativos.

Debe contener como mínimo:

## Panel de entrada

Textarea:

```text
Introduce tu prompt...
```

Botón:

```text
INICIAR
```

## Pipeline

Mostrar visualmente:

```text
PROMPT
 ↓
OPTIMIZER
 ↓
AUDITOR
 ↓
QUALITY GATES
 ↓
HUMAN
 ↓
EXECUTOR
```

La etapa actual debe poder identificarse fácilmente.

## Panel de iteraciones

Mostrar las diferentes versiones.

## Panel de auditoría

Mostrar:

* score;
* propiedades;
* observaciones;
* recomendaciones.

## Panel de Quality Gates

Mostrar los 4 gates.

## Panel Human-in-the-Loop

Botones:

```text
APROBAR
NUEVA ITERACIÓN
EDITAR
```

## Respuesta final

Mostrar la respuesta generada.

## Historial

Permitir consultar ejecuciones anteriores.

---

# 16. HISTORIAL

El usuario debe poder seleccionar una ejecución anterior.

Al abrirla debe poder reconstruir el proceso:

```text
Prompt original
      ↓
Iteración 1
      ↓
Auditoría 1
      ↓
Gates 1
      ↓
Decisión humana
      ↓
Iteración 2
      ↓
Auditoría 2
      ↓
Gates 2
      ↓
Decisión humana
      ↓
Prompt aprobado
      ↓
Respuesta final
```

Esto es importante para demostrar trazabilidad.

---

# 17. RESPUESTAS JSON DE LAS IAs

Siempre que sea posible, las llamadas a las IAs deben solicitar respuestas JSON estructuradas.

El backend debe validar esas respuestas mediante modelos Pydantic.

Si el modelo devuelve JSON inválido:

1. detectar el error;
2. intentar manejarlo de manera segura;
3. registrar el error;
4. evitar que la aplicación se rompa.

No confíes ciegamente en la salida del modelo.

---

# 18. MANEJO DE ERRORES

Implementa manejo razonable de:

* API key inválida;
* NVIDIA API no disponible;
* timeout;
* rate limit;
* modelo inexistente;
* respuesta vacía;
* JSON inválido;
* PostgreSQL no disponible;
* errores de validación;
* errores inesperados.

El usuario debe recibir mensajes comprensibles.

Los errores técnicos completos deben registrarse en logs.

---

# 19. SEGURIDAD

Nunca escribas API keys directamente en el código.

Utiliza `.env`.

No almacenes innecesariamente secretos en PostgreSQL.

No muestres claves API en el frontend.

Evita imprimir secretos en logs.

Incluye:

```text
.env
```

en:

```text
.gitignore
```

Incluye:

```text
.env.example
```

---

# 20. ESTRUCTURA DEL PROYECTO

Propón una estructura similar a:

```text
promptops-lab/
│
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   │
│   ├── models/
│   ├── schemas/
│   ├── routes/
│   ├── services/
│   │   ├── nvidia_client.py
│   │   ├── prompt_optimizer.py
│   │   ├── prompt_auditor.py
│   │   ├── final_executor.py
│   │   └── workflow.py
│   │
│   └── ...
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── .env
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

Puedes modificar esta estructura si existe una alternativa técnicamente superior.

---

# 21. SIMPLICIDAD

No quiero sobreingeniería.

Evita agregar sin necesidad:

* microservicios;
* Kubernetes;
* Redis;
* RabbitMQ;
* Docker obligatorio;
* sistemas distribuidos;
* autenticación compleja;
* frontend frameworks;
* arquitecturas empresariales innecesarias.

La aplicación es local y académica.

La solución debe ser suficientemente profesional para demostrar el concepto, pero sencilla para poder comprenderla y explicarla.

---

# 22. TRAZABILIDAD

Una característica central debe ser poder responder:

> ¿Qué ocurrió con este prompt desde que entró hasta que produjo la respuesta final?

Por lo tanto, debe ser posible conocer:

```text
qué prompt entró
↓
qué modificó el Optimizer
↓
qué dijo el Auditor
↓
qué Gates pasaron/fallaron
↓
qué decidió el humano
↓
qué cambios ocurrieron
↓
qué prompt terminó siendo aprobado
↓
qué respuesta generó
```

---

# 23. CONFIGURACIÓN DE MODELOS

No hardcodees el nombre de un modelo en múltiples archivos.

Centraliza la configuración.

Por ejemplo:

```text
OPTIMIZER_MODEL=...
AUDITOR_MODEL=...
EXECUTOR_MODEL=...
```

Esto permitirá cambiar los modelos sin modificar la lógica principal.

Si resulta mejor utilizar el mismo modelo para varias funciones, la arquitectura debe permitirlo.

---

# 24. CRITERIO ACADÉMICO

No optimices solamente para "que funcione".

La aplicación debe ser demostrable.

Un profesor debe poder observar:

1. Prompt inicial.
2. Optimización.
3. Evaluación.
4. Quality Gates.
5. Iteración.
6. Feedback.
7. Human-in-the-Loop.
8. Aprobación.
9. Ejecución.
10. Resultado.
11. Historial.

El flujo debe ser comprensible visualmente.

---

# 25. REGLA SOBRE EL CONTEXTO DE QUALITY GATES

A continuación proporcionaré el marco oficial que debo utilizar para la auditoría.

Este contexto contiene los criterios entregados para el laboratorio.

Debes:

* analizarlo;
* incorporarlo al diseño;
* respetar sus definiciones;
* utilizarlo como requisito funcional;
* evitar inventar criterios que sustituyan los oficiales.

Si encuentras contradicciones entre la arquitectura propuesta y el marco de Quality Gates, debes identificar el problema y resolverlo de manera coherente.

---

# 26. AUTONOMÍA TÉCNICA

Tienes libertad para tomar decisiones técnicas razonables.

No necesito que copies literalmente mi arquitectura si encuentras una solución mejor.

Sin embargo:

* no cambies el objetivo;
* no elimines Human-in-the-Loop;
* no elimines PostgreSQL;
* no elimines la trazabilidad;
* no elimines los Quality Gates;
* no elimines las iteraciones;
* no conviertas el proyecto en una aplicación innecesariamente compleja.

Cuando tomes una decisión arquitectónica importante, explica brevemente por qué.

---

# 27. FORMA DE TRABAJO

No quiero que simplemente generes miles de líneas de código sin verificar nada.

Trabaja como un desarrollador profesional:

1. analiza el proyecto;
2. crea la estructura;
3. implementa por componentes;
4. verifica cada componente;
5. ejecuta pruebas;
6. identifica errores;
7. corrige errores;
8. vuelve a probar;
9. integra los componentes;
10. verifica el flujo completo.

Utiliza el entorno de desarrollo disponible para inspeccionar y modificar los archivos reales del proyecto.

No asumas que un archivo funciona simplemente porque el código parece correcto.

---

# 28. DOCUMENTACIÓN

Incluye un README que explique:

* requisitos;
* instalación;
* configuración de PostgreSQL;
* configuración de NVIDIA;
* configuración del `.env`;
* instalación de dependencias;
* ejecución del backend;
* acceso a la aplicación;
* estructura del proyecto;
* funcionamiento del pipeline;
* explicación de los Quality Gates;
* funcionamiento del Human-in-the-Loop;
* estructura de la base de datos.

El README debe estar escrito pensando en que otra persona pueda clonar/copiar el proyecto y ejecutarlo localmente.

---

# 29. RESULTADO ESPERADO

Quiero terminar con una aplicación funcional localmente que permita:

```text
1. Introducir prompt
2. Ejecutar optimización
3. Auditar
4. Evaluar Quality Gates
5. Mostrar resultados
6. Esperar intervención humana
7. Iterar
8. Aprobar
9. Ejecutar
10. Mostrar respuesta
11. Guardar historial
12. Consultar ejecuciones anteriores
```

---

# 30. CONTEXTO OFICIAL DE QUALITY GATES

A continuación te proporciono el contexto del marco de auditoría y Quality Gates que debe utilizar el proyecto.

[PEGAR AQUÍ EL TEXTO COMPLETO PROPORCIONADO POR GEMINI]

Este contenido forma parte de los requisitos funcionales del proyecto.

---

# 31. INICIO DEL TRABAJO

Primero analiza toda esta especificación y el contexto de Quality Gates.

Después:

1. Inspecciona el entorno/proyecto existente.
2. Determina si existe algún código previo que deba conservarse.
3. Propón o confirma la arquitectura.
4. Implementa la solución.
5. Ejecuta las pruebas necesarias.
6. Corrige los problemas encontrados.
7. Deja el proyecto funcionando localmente.
8. Explica al final qué se implementó, cómo ejecutarlo y qué decisiones importantes tomaste.

No omitas componentes esenciales.

No reemplaces funcionalidades por pseudocódigo si pueden implementarse realmente.

Cuando una decisión técnica dependa del entorno disponible, inspecciona primero el entorno antes de asumir.
