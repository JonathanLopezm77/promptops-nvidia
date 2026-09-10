# Laboratorio de PromptOps

Aplicación web local que demuestra un pipeline de PromptOps observable:

```
prompt → optimización → auditoría → Quality Gates → Human-in-the-Loop →
iteración → aprobación → ejecución → historial
```

Proyecto académico. No es una plataforma comercial: prioriza que el proceso
completo sea observable y explicable por encima de cualquier otra
consideración. La especificación completa está en [`docs/SPEC.md`](docs/SPEC.md)
y los criterios oficiales de auditoría en [`docs/quality_gates.md`](docs/quality_gates.md)
y [`docs/auditor_system_prompt.md`](docs/auditor_system_prompt.md).

---

## 1. Requisitos

- Python 3.11+
- PostgreSQL 13+ en local (se usa `gen_random_uuid()`, disponible de forma
  nativa desde PostgreSQL 13; probado contra PostgreSQL 18)
- Una API key de NVIDIA con acceso a `https://integrate.api.nvidia.com/v1`
  ([build.nvidia.com](https://build.nvidia.com))
- Sin Docker, sin Redis, sin Celery, sin Node — el frontend es HTML/CSS/JS
  vanilla servido directamente por FastAPI

## 2. Instalación

```bash
git clone <este-repositorio>
cd promptops-lab

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate

pip install -r requirements.txt
```

**Nota de compatibilidad**: si al correr los tests aparece
`ModuleNotFoundError: No module named 'backend'` corriendo `pytest` a secas,
o `async def functions are not natively supported`, verifica que instalaste
exactamente `requirements.txt` dentro de tu propio `.venv` (no en un
intérprete global que ya tenga otras cosas instaladas) — ambos casos ya
están resueltos en este repo (`pytest.ini` con `pythonpath`/`asyncio_mode`,
y `pytest-asyncio` en `requirements.txt`), pero si clonas en un entorno
distinto vale la pena confirmarlo.

## 3. Configuración de PostgreSQL

Crea la base de datos y aplica el esquema (es SQL puro, sin Alembic ni
migraciones — `backend/schema.sql` es la fuente de verdad del esquema):

```bash
createdb promptops
psql promptops -f backend/schema.sql
```

Si tu PostgreSQL no corre en el puerto/usuario por defecto, ajusta esos
datos en `DATABASE_URL` dentro de `.env` (ver más abajo). Para verificar
que el esquema se aplicó:

```bash
psql promptops -c "\dt"
```

Deberías ver cinco tablas: `runs`, `iterations`, `audits`,
`human_decisions`, `results`.

## 4. Configuración de NVIDIA

1. Crea una cuenta en [build.nvidia.com](https://build.nvidia.com) y genera
   una API key.
2. Anótala para el paso siguiente — nunca se escribe en el código ni se
   sube al repositorio.
3. Elige los modelos que quieras usar para cada rol (Optimizer, Auditor,
   Executor). Pueden ser el mismo modelo para los tres, o distintos; este
   proyecto se probó con `moonshotai/kimi-k3` (Optimizer/Executor) y
   `deepseek-ai/deepseek-v4-pro-0813` (Auditor).

## 5. Configuración del `.env`

Copia `.env.example` a `.env` y completa los valores:

```bash
cp .env.example .env
```

```env
DATABASE_URL=postgresql+psycopg://usuario:password@localhost:5432/promptops
NVIDIA_API_KEY=tu-api-key-aqui
NVIDIA_BASE_URL=https://integrate.api.nvidia.com/v1
OPTIMIZER_MODEL=moonshotai/kimi-k3
AUDITOR_MODEL=deepseek-ai/deepseek-v4-pro-0813
EXECUTOR_MODEL=moonshotai/kimi-k3
LLM_TIMEOUT_SECONDS=180
LLM_MAX_RETRIES=2
```

`backend/config.py` es el **único** módulo del proyecto que lee variables
de entorno; ningún otro archivo menciona un nombre de modelo literal.
`.env` está en `.gitignore` — nunca se sube al repositorio.

**Sobre `LLM_TIMEOUT_SECONDS`**: los modelos de razonamiento (como
`deepseek-v4-pro` o `kimi-k3`) pueden tardar 60-170 segundos por llamada
real, especialmente en iteraciones con contexto de feedback. `180` es un
margen realista verificado en pruebas reales contra la API; con `60` es
fácil que el cliente agote los reintentos y el run termine en `ERROR` por
timeout sin que haya nada roto de verdad.

## 6. Ejecución

```bash
uvicorn backend.main:app --reload
```

## 7. Acceso a la aplicación

Abre [http://localhost:8000](http://localhost:8000) en el navegador. El
frontend (HTML/CSS/JS vanilla, sin build step) se sirve como estáticos
desde el mismo FastAPI — no hay un servidor de frontend separado.

La documentación interactiva de la API (Swagger) está en
[http://localhost:8000/docs](http://localhost:8000/docs).

## 8. Tests

```bash
pytest -v
```

58 tests: schemas Pydantic de las tres IAs (JSON correcto/incompleto/
malformado), el cliente de reintentos del Auditor mockeado, y la máquina
de estados completa (transiciones válidas e inválidas) contra PostgreSQL
real con los servicios de LLM mockeados — ningún test llama a la API real
de NVIDIA, así que corren rápido y sin costo.

---

## 9. Estructura del proyecto

```
promptops-lab/
├── backend/
│   ├── main.py                  FastAPI, manejo de errores, estáticos
│   ├── config.py                único módulo que lee os.environ
│   ├── database.py               engine, sesión, Base declarativa
│   ├── schema.sql                DDL de las 5 tablas (fuente de verdad)
│   │
│   ├── models/
│   │   └── models.py             Run, Iteration, Audit, HumanDecision, Result
│   │
│   ├── schemas/
│   │   ├── optimizer.py          OptimizerResponse (IA 1)
│   │   ├── auditor.py            AuditorResponse + mapeo de 21 propiedades (IA 2)
│   │   ├── executor.py           ExecutorResponse (IA 3)
│   │   └── api.py                request/response de la API REST
│   │
│   ├── routes/
│   │   └── runs.py                los endpoints de /api/runs
│   │
│   └── services/
│       ├── nvidia_client.py       cliente HTTP async con reintentos
│       ├── json_extraction.py     extrae el JSON de la respuesta del LLM
│       ├── prompt_optimizer.py    IA 1
│       ├── prompt_auditor.py      IA 2
│       ├── final_executor.py      IA 3
│       ├── workflow.py            máquina de estados + orquestación
│       └── prompts/               system prompts de cada IA, en su propio archivo
│
├── frontend/
│   ├── index.html
│   ├── style.css                  fondo negro, monoespaciada, sin librerías
│   └── app.js
│
├── tests/
├── docs/                          SPEC.md, quality_gates.md, auditor_system_prompt.md
├── .env.example
├── requirements.txt
└── pytest.ini
```

---

## 10. El pipeline

```
PROMPT ORIGINAL
      ↓
OPTIMIZER (IA 1)         mejora el prompt; recibe feedback de iteraciones previas
      ↓
AUDITOR (IA 2)           evalúa el prompt mejorado contra los 4 Quality Gates
      ↓
QUALITY GATES            PASS / FAIL / NO_APLICA por cada uno de los 4 Gates
      ↓
HUMAN-IN-THE-LOOP        el humano revisa todo lo anterior
      ↓                  y decide: APROBAR / NUEVA ITERACIÓN / EDITAR / RECHAZAR
      │
      ├─ NUEVA ITERACIÓN ──→ vuelve al OPTIMIZER con el feedback como contexto
      ├─ EDITAR ───────────→ vuelve directo al AUDITOR (sin pasar por el Optimizer)
      ├─ RECHAZAR ─────────→ fin (REJECTED)
      └─ APROBAR
            ↓
      EXECUTOR (IA 3)      ejecuta el prompt aprobado — SOLO el prompt, sin
      ↓                    contexto de auditoría ni de iteraciones anteriores
   RESPUESTA FINAL
      ↓
   HISTORIAL (PostgreSQL)
```

**Separación de roles real, no solo documentada**: cada IA es un servicio
distinto (`prompt_optimizer.py`, `prompt_auditor.py`, `final_executor.py`)
con su propio system prompt en `services/prompts/`, y cada uno solo recibe
el contexto que le corresponde. El Auditor nunca ve ni responde la tarea
original; el Executor nunca ve el historial de auditorías ni de feedback
humano — solo el string final del prompt aprobado.

**¿Por qué el request no se queda esperando ~170s?** Las llamadas reales
a NVIDIA (sobre todo el Auditor, con `deepseek-v4-pro`) pueden tardar más
de dos minutos. `POST /api/runs`, `/iterate`, `/edit` y `/execute` hacen la
parte rápida de forma síncrona (crear la fila, registrar la decisión
humana, transicionar el estado) y devuelven `202 Accepted` de inmediato;
el ciclo Optimizer→Auditor (o el Executor) corre en segundo plano con
`BackgroundTasks` de FastAPI, con su propia sesión de base de datos. El
frontend hace polling a `GET /api/runs/{id}` y `GET /api/runs/{id}/events`
cada 3 segundos hasta que el estado deja de ser transitorio. No se usa
Celery, Redis, colas de mensajes ni WebSockets — están explícitamente
descartados para este proyecto.

### Manejo de JSON inválido

Cada IA pide JSON explícito en su system prompt, validado con un modelo
Pydantic. Si el LLM devuelve algo que no valida (JSON malformado, o JSON
sintácticamente válido pero incompleto — por ejemplo, al Auditor le
faltan Gates):

1. Se intenta extraer el bloque JSON del texto (por si vino envuelto en
   ```` ```json ```` o con texto alrededor).
2. Si sigue sin validar, se hace **un** reintento con el error como
   contexto para el LLM.
3. Si vuelve a fallar, se trata como error técnico: el `raw_response` del
   LLM se guarda siempre (columna `raw_response`, `NOT NULL`), y el run
   pasa a `ERROR` con un `error_message` claro. Nunca se inventan valores
   por defecto para rellenar un score o un Gate.

Este reintento automático **no cuenta como una iteración del prompt** — no
crea una fila nueva en `iterations`.

---

## 11. Quality Gates

El marco de auditoría es el oficial de [`docs/auditor_system_prompt.md`](docs/auditor_system_prompt.md):
**21 propiedades** repartidas en **4 Quality Gates**. No se inventaron
Gates adicionales ni se renombró ningún criterio.

| Gate | Nombre | Propiedades | Puede ser NO_APLICA |
|---|---|---|---|
| **Gate 1** | Estructura e Instrucción | P1–P6 (Tokens, Tono, Objetivos, Demos, Lógica Estructural, Lógica Contextual) | No |
| **Gate 2** | Razonamiento y Cognición | P7–P12 (Cargas Intrínseca/Extránea/Germana, Metacognición, Herramientas Externas, Recompensas) | **Sí** — si la tarea no requiere razonamiento complejo |
| **Gate 3** | Seguridad y Veracidad | P13–P19 (Alucinaciones, Factibilidad vs. Creatividad, Sesgo, Seguridad, Privacidad, Confiabilidad, Normas Sociales) | No |
| **Gate 4** | Eficiencia y Foco | P20–P21 (Interacción, Cortesía) | No |

Cada Gate resulta en `PASS`, `FAIL` o `NO_APLICA`, con una justificación y
las propiedades de su mapeo evaluadas individualmente (1-10, con
observación). El **Auditor nunca reescribe el prompt** — solo evalúa y
recomienda; es el Optimizer quien aplica las recomendaciones en la
siguiente iteración.

`total_score` (0-100) es un juicio holístico que el propio Auditor emite,
no un promedio de las propiedades puntuadas — así un Gate crítico en
`FAIL` (p. ej. Gate 3, con 7 propiedades) pesa por su naturaleza, no
porque tenga más o menos propiedades que Gate 4 (que solo tiene 2).

`gates_score = gates_passed / (gates_passed + gates_failed)`: el
denominador excluye los Gates en `NO_APLICA`, para que no penalicen ni
favorezcan artificialmente el resultado.

---

## 12. Human-in-the-Loop

El ejecutor final **nunca corre automáticamente**, ni aunque los 4 Gates
pasen. Tras cada auditoría el run queda en `WAITING_HUMAN`, y el humano
decide entre:

- **APROBAR** → pasa a `APPROVED`, habilitando `/execute`.
- **NUEVA ITERACIÓN** (con feedback) → vuelve al Optimizer, que recibe el
  prompt anterior, el feedback de la auditoría y el feedback humano como
  contexto.
- **EDITAR** (prompt manual) → salta el Optimizer y va directo a
  reauditar la versión editada a mano.
- **RECHAZAR** → termina el run en `REJECTED`.

Cada decisión se guarda en `human_decisions`, ligada a la iteración sobre
la que se tomó, con su feedback o prompt editado si corresponde.

---

## 13. Estructura de la base de datos

Cinco tablas (`backend/schema.sql`). Lo estructurado va en columnas; lo
variable del LLM (la respuesta cruda, las propiedades evaluadas, los
Gates) va en `JSONB`.

```
runs
├── id, created_at, finished_at, status, original_prompt
├── optimizer_model, auditor_model, executor_model   ← modelo usado en CADA rol
└── error_message

iterations
├── id, run_id, iteration_number, source ('optimizer' | 'human_edit')
├── input_prompt, output_prompt (NULL si el Optimizer falló)
└── optimizer_raw JSONB (siempre se guarda, aunque el parseo falle)

audits
├── id, iteration_id, parse_ok
├── total_score, gates_passed, gates_failed, gates_not_applicable, gates_score
├── properties JSONB, gates JSONB, recommendations JSONB
└── raw_response JSONB NOT NULL   ← se guarda SIEMPRE, incluso si parse_ok=false

human_decisions
├── id, iteration_id, decision ('approve'|'iterate'|'edit'|'reject')
└── feedback, edited_prompt

results
├── id, run_id (UNIQUE), approved_prompt, final_response, model
```

No existe una sexta tabla de "eventos": el timeline de observabilidad
(`GET /api/runs/{id}/events`) se **deriva** en el momento a partir de los
timestamps de estas cinco tablas (`workflow.build_timeline()`), no se
persiste aparte.

**Máquina de estados** (única fuente de verdad: `backend/services/workflow.py`):

```
CREATED → OPTIMIZING → AUDITING → GATING → WAITING_HUMAN
WAITING_HUMAN → ITERATING → OPTIMIZING        (nueva iteración)
WAITING_HUMAN → AUDITING                      (edición manual → reauditar)
WAITING_HUMAN → APPROVED → EXECUTING → COMPLETED
WAITING_HUMAN → REJECTED
cualquier estado activo → ERROR
```

Ningún endpoint ni servicio asigna `run.status` directamente; todas las
transiciones pasan por `workflow.py`, que valida cada una y lanza
`InvalidTransitionError` (traducido a HTTP 409) si no es válida.

---

## 14. API

```
POST   /api/runs                  crea el run, corre Optimizer+Auditor en segundo plano → 202
GET    /api/runs                  listado para el historial
GET    /api/runs/{id}             run completo: iteraciones + auditorías + decisiones + resultado
GET    /api/runs/{id}/events      timeline de observabilidad
POST   /api/runs/{id}/iterate     body: {"feedback": "..."} → nueva iteración
POST   /api/runs/{id}/edit        body: {"prompt": "..."} → edición manual + reauditoría
POST   /api/runs/{id}/approve     → APPROVED
POST   /api/runs/{id}/reject      body: {"feedback": "..."} (opcional) → REJECTED
POST   /api/runs/{id}/execute     solo si APPROVED → ejecuta en segundo plano → COMPLETED
```

`GET /api/runs/{id}` basta por sí solo para reconstruir el proceso
completo de un run en el frontend, sin llamadas adicionales.
