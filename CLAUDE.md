# CLAUDE.md — Laboratorio de PromptOps

Proyecto académico local. Demuestra un pipeline de PromptOps observable:
prompt → optimización → auditoría → Quality Gates → Human-in-the-Loop → iteración → aprobación → ejecución → historial.

La especificación completa está en `docs/SPEC.md`. Los criterios oficiales de auditoría están en
`docs/quality_gates.md`. **Lee ambos antes de tocar `services/prompt_auditor.py` o los schemas de auditoría.**

---

## Invariantes (no negociables)

No elimines ni "simplifiques" nada de esto sin pedirlo explícitamente:

1. **Human-in-the-Loop obligatorio.** El ejecutor final NUNCA corre automáticamente, ni aunque los 4 Gates pasen. Siempre hay un estado `WAITING_HUMAN` y una decisión humana registrada en BD.
2. **PostgreSQL como persistencia.** Nada de SQLite ni almacenamiento en memoria, ni siquiera "temporalmente para probar".
3. **Trazabilidad completa.** Toda etapa escribe en BD: entradas, salidas, timestamps, modelo usado, tokens si están disponibles.
4. **Los Quality Gates son los del documento oficial.** No inventes gates, no renombres criterios, no cambies definiciones ni umbrales.
5. **Iteraciones múltiples.** El feedback humano + la auditoría vuelven al Optimizer como contexto.
6. **Separación de roles.** Optimizer, Auditor y Executor son servicios distintos con system prompts distintos. El Auditor jamás responde a la tarea del usuario; solo evalúa el prompt.

## Anti-objetivos

Es un proyecto local y académico. **No** añadas: Docker obligatorio, Redis, Celery, colas de mensajes,
microservicios, autenticación/usuarios, React/Vue/Svelte, WebSockets, Alembic salvo que se pida,
capas de abstracción "por si acaso", ni tests que mockeen todo hasta no probar nada.
Si crees que algo de esto hace falta, explica el motivo y espera confirmación.

---

## Stack

- Backend: Python 3.11+, FastAPI, SQLAlchemy 2.x, Pydantic v2, `httpx` (async), `python-dotenv`
- BD: PostgreSQL local
- Frontend: HTML + CSS + JS vanilla, servido como estáticos desde FastAPI. Sin build step, sin npm.
- LLM: API de NVIDIA (endpoint compatible OpenAI: `https://integrate.api.nvidia.com/v1/chat/completions`).
  Verifica el endpoint y el nombre del modelo contra la documentación real antes de dar por bueno el cliente.

## Comandos

```bash
# entorno
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# base de datos (crear una vez)
createdb promptops
psql promptops -f backend/schema.sql

# servidor (frontend en http://localhost:8000)
uvicorn backend.main:app --reload

# tests
pytest -q
pytest tests/test_gates.py -q
```

## Configuración

Todo por `.env`, nunca hardcodeado. Variables esperadas:

```
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/promptops
NVIDIA_API_KEY=
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
OPTIMIZER_MODEL=
AUDITOR_MODEL=
EXECUTOR_MODEL=
LLM_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=2
```

Reglas: `config.py` es el **único** módulo que lee `os.environ`. Ningún otro archivo menciona un nombre de
modelo literal. `.env` va en `.gitignore`; `.env.example` se mantiene actualizado con claves vacías.
Nunca loguees la API key ni la devuelvas por la API.

---

## Máquina de estados

```
CREATED → OPTIMIZING → AUDITING → GATING → WAITING_HUMAN
WAITING_HUMAN → ITERATING → OPTIMIZING        (nueva iteración)
WAITING_HUMAN → AUDITING                      (edición manual → reauditar)
WAITING_HUMAN → APPROVED → EXECUTING → COMPLETED
WAITING_HUMAN → REJECTED
cualquiera → ERROR
```

Las transiciones se validan en un único sitio (`services/workflow.py`). Ningún endpoint cambia
`run.status` por su cuenta. Una transición inválida devuelve 409, no revienta.

## Modelo de datos

Cinco tablas. Lo estructurado va en columnas; lo variable del LLM en `JSONB`.

- `runs` — id, created_at, finished_at, status, original_prompt, models usados
- `iterations` — id, run_id, iteration_number, input_prompt, output_prompt, source (`optimizer` | `human_edit`), created_at, `optimizer_raw` JSONB
- `audits` — id, iteration_id, audited_prompt, total_score, gates_passed, `properties` JSONB, `gates` JSONB, `recommendations` JSONB, `raw_response` JSONB
- `human_decisions` — id, iteration_id, decision (`approve` | `iterate` | `edit` | `reject`), feedback, edited_prompt, created_at
- `results` — id, run_id, approved_prompt, final_response, model, created_at

Guarda **siempre** la respuesta cruda del modelo en `raw_response`, aunque el parseo falle. Es la prueba
de trazabilidad y lo que se enseña en la defensa del proyecto.

## API

```
POST /api/runs                  crea run + primera optimización + auditoría → WAITING_HUMAN
GET  /api/runs                  listado para el historial
GET  /api/runs/{id}             run completo: iteraciones + auditorías + decisiones + resultado
POST /api/runs/{id}/iterate     body: {feedback} → nueva iteración con contexto previo
POST /api/runs/{id}/edit        body: {prompt} → registra edición humana y reaudita
POST /api/runs/{id}/approve     → APPROVED
POST /api/runs/{id}/execute     solo si APPROVED → ejecuta y guarda resultado
GET  /api/runs/{id}/events      timeline de observabilidad
```

`GET /api/runs/{id}` debe bastar para reconstruir el proceso entero en el frontend sin más llamadas.

## Salidas de los LLM

- Cada rol pide JSON explícitamente en su system prompt y se valida con un modelo Pydantic.
- Si el JSON es inválido: extraer el bloque JSON del texto → si sigue fallando, **un** reintento con el
  error como feedback → si vuelve a fallar, marcar la iteración como fallida, guardar el raw y mostrar un
  mensaje comprensible. Nunca inventes valores por defecto para rellenar un score o un gate.
- Los prompts de sistema viven en `services/prompts/*.py` (o `.md`), no incrustados entre la lógica.
- El system prompt del Auditor incorpora el marco de `docs/quality_gates.md` literalmente.

## Errores

Maneja y distingue: API key inválida (401), rate limit (429), timeout, modelo inexistente, respuesta vacía,
JSON inválido, PostgreSQL caído, validación. El usuario ve un mensaje claro en español; el traceback va al
log. Un fallo del LLM pone el run en `ERROR` con `error_message`, no tumba el servidor.

## Frontend

Fondo negro, alto contraste, tipografía monoespaciada, sin librerías. Secciones: entrada, pipeline con la
etapa actual resaltada, timeline de eventos, panel de iteraciones (con diff o comparación lado a lado),
panel de auditoría, panel de Gates (✓/✗/N-A), botones APROBAR / NUEVA ITERACIÓN / EDITAR, respuesta final,
historial. Todo el estado se deriva de la respuesta de la API; no dupliques la máquina de estados en JS.

---

## Cómo quiero que trabajes

- Implementa por componentes y **verifica cada uno antes de seguir**: cliente NVIDIA → esquemas → BD →
  servicios → workflow → endpoints → frontend.
- Prueba de verdad: ejecuta el servidor, llama a los endpoints, consulta la BD. No des por bueno un archivo
  porque "el código se ve correcto".
- Nada de pseudocódigo ni `# TODO: implementar` en funciones centrales.
- Antes de una decisión arquitectónica que se desvíe de esta guía, dime cuál y por qué en una o dos frases.
- Al terminar un bloque, actualiza la sección de progreso de abajo.
- Escribe código y comentarios en español; nombres de identificadores en inglés.

## Progreso
- [x] Estructura del proyecto + config + `.env.example`
      Verificado: get_settings() OK, NVIDIA 200 con kimi-k3, PostgreSQL 18.2 conectando.
      Driver: psycopg[binary]. Entorno: .venv activo.
- [x] Cliente NVIDIA con reintentos y manejo de errores
      Verificado contra API real: modelo inexistente -> NvidiaModelNotFoundError
      sin reintentar; 401/404 no reintentan, timeout/429/5xx sí.
      content y reasoning_content confirmados como campos hermanos en kimi-k3.
      extra_payload soporta chat_template_kwargs.

- [x] Esquema PostgreSQL + modelos SQLAlchemy
      Verificado: schema.sql aplicado con psql sobre promptops; \dt muestra las
      5 tablas. Roundtrip ORM completo (insert en las 5 + rollback) sin residuos.
      gen_random_uuid() nativo en PG18, sin pgcrypto.
      Añadida columna parse_ok boolean para distinguir fallo de parseo de campos
      vacíos. CHECK: los 3 contadores suman 4 salvo parse_ok=false.

- [x] Schemas Pydantic de las tres IAs
      Verificado: pytest -v en verde. AuditorResponse valida contra
      GATE_PROPERTIES (P1-P6 / P7-P12 / P13-P19 / P20-P21): exige los 4 gates
      con todas sus propiedades. gate_counts() y gates_score() implementados.
      Requiere pytest.ini con pythonpath=. y pytest-asyncio (asyncio_mode=auto).

- [x] Optimizer
      Verificado por mí en terminal: "hazme un resumen de este texto" ->
      prompt con rol, objetivo, restricciones, formato y límite de longitud.
      70.2s reales. Acepta previous_prompt, audit_feedback y human_feedback.
      Un reintento ante JSON inválido -> OptimizerParseError con raw_response.

- [x] Auditor + Quality Gates
      Verificado contra API real con deepseek-v4-pro-0813, thinking desactivado:
      prompt malo ("Dime todo lo que sabes") -> 5/100, 0/4 gates, 111.1s.
      prompt bueno (salida del Optimizer) -> 62/100, 1 PASS / 2 FAIL /
      1 NO_APLICA, gates_score 0.3333, 103.1s. Detectó el placeholder vacío.
      Camino reintento -> AuditorParseError cubierto con chat_completion mockeado.

NOTA DE TIEMPOS: una iteración completa (Optimizer ~70s + Auditor ~110s) tarda
unos 3 minutos. LLM_TIMEOUT_SECONDS=180. El frontend necesita timeline en vivo,
no puede quedarse congelado esperando.

- [x] Workflow / máquina de estados
      TRANSICIONES_VALIDAS + _ensure_transition_allowed son el único punto que
      valida transiciones; _set_status el único que escribe run.status.
      58 tests (transiciones puras + integración con Postgres real y
      optimize_prompt/audit_prompt mockeados): las 11 transiciones válidas,
      "cualquiera->ERROR" en los 8 estados activos, 5 inválidas (incluidas las
      3 pedidas: ejecutar sin aprobar, aprobar dos veces, iterar desde
      COMPLETED). build_timeline() deriva el timeline de las 5 tablas, sin
      sexta tabla de eventos.

- [x] Endpoints
      Todos los de CLAUDE.md + POST /reject (no estaba en la lista literal,
      pero WAITING_HUMAN->REJECTED ya existía en la máquina de estados).
      Probado con servidor real: 201/404/409(x2)/200/422 verificados con
      curl. InvalidTransitionError->409, NvidiaClientError->502,
      SQLAlchemyError->503, catch-all->500, traceback solo a logger.

- [x] Executor final
      final_executor.py recibe SOLO el prompt aprobado (separación de roles
      real). Conectado a start_execution/advance_execution/complete_execution.
      Verificado end-to-end con servidor real: create->approve->execute->
      COMPLETED, respuesta final coherente ("por qué el cielo es azul" en 3
      puntos). Run c84c7230 (que había quedado atascado en EXECUTING antes de
      que este servicio existiera) completado manualmente.

- [x] Frontend
      index.html/style.css/app.js: fondo negro, monoespaciada, sin librerías.
      Pipeline mapea run.status -> nodo activo (sin duplicar la máquina de
      estados). Problema de los ~170s bloqueando la respuesta resuelto con
      BackgroundTasks (202 Accepted, <1s de respuesta) + polling cada 3s a
      /runs/{id} y /events. Verificado end-to-end con servidor real
      (create: 0.3s->OPTIMIZING, 67.5s->AUDITING, 128.3s->WAITING_HUMAN).
      Usuario verificó en navegador: pipeline, historial, iteraciones,
      auditoría, gates, recomendaciones, rechazar/iterar funcionan.

- [x] Historial y reconstrucción del proceso
      GET /api/runs/{id} basta para reconstruir todo. Se agregó al frontend
      lo que faltaba para reconstrucción completa: prompt original visible,
      decisiones humanas (con su feedback real) dentro de cada iteración,
      prompt aprobado junto a la respuesta final. Verificado con runs reales
      ya completados en Postgres (incluye casos con 2 iteraciones y feedback
      real del usuario).

- [x] README
      Cubre requisitos, instalación, PostgreSQL, NVIDIA, .env, dependencias,
      arranque, estructura, pipeline, Quality Gates, Human-in-the-Loop,
      esquema de BD y API. requirements.txt verificado desde cero: venv
      nuevo + pip install -r requirements.txt + 58 tests en verde, sin
      depender del intérprete global.