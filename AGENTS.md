# AGENTS.md — Laboratorio de PromptOps → Ingeniería de Requisitos Aumentada con IA

Instrucciones para cualquier agente o asistente de código que trabaje en este
repositorio (formato abierto: https://agents.md/). `CLAUDE.md` contiene la
misma guía con más detalle y el registro de progreso del Laboratorio previo.

## Qué es este proyecto

Plataforma local que valida y optimiza prompts con un pipeline observable:
prompt → Optimizer (IA 1) → Auditor (IA 2) → 4 Quality Gates → Human-in-the-Loop
→ iteración → aprobación → Executor (IA 3) → historial en PostgreSQL.

En el Parcial 1 se **amplía** (no se reemplaza) con:

1. Una capa de Ingeniería de Requisitos multimodal (texto y voz, STT/TTS) que
   evalúa requisitos con 10 criterios de calidad (ISO/IEC/IEEE 29148).
2. Los 7 prompts del SDLC, validados con esta misma plataforma (`/prompts`).
3. Un benchmark de modelos local/cloud por fase del SDLC (`/benchmarks`).
4. Una especificación SDD trazable REQ → SPEC → ARCH → CODE → TEST (`/specs`).

## Comandos

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt

createdb promptops
psql promptops -f backend/schema.sql

uvicorn backend.main:app --reload # http://localhost:8000
pytest -q                         # debe quedar en verde antes de cada commit
```

## Estructura

| Ruta | Contenido |
|---|---|
| `backend/` | FastAPI, servicios de IA, máquina de estados, modelos SQLAlchemy |
| `frontend/` | HTML/CSS/JS vanilla servido por FastAPI (sin build step) |
| `tests/` | pytest; los LLM se mockean, PostgreSQL es real |
| `docs/` | especificación y Quality Gates oficiales del Laboratorio previo |
| `prompts/` | los 7 prompts del SDLC y su evidencia de validación |
| `context/` | paquetes de contexto que recibe cada fase del SDLC |
| `specs/` | artefactos SDD: requisito, criterios de aceptación, especificación, contrato |
| `benchmarks/` | resultados y log de las ejecuciones del benchmark |
| `evidence/` | salidas crudas, capturas y grabaciones que respaldan las métricas |

## Invariantes (no negociables)

1. **Human-in-the-Loop obligatorio.** Nada se ejecuta automáticamente sin una
   decisión humana registrada en BD.
2. **PostgreSQL como persistencia.** Nada de SQLite ni memoria.
3. **Trazabilidad completa.** Cada etapa guarda entradas, salidas, timestamps,
   modelo y tokens; la respuesta cruda del modelo se guarda siempre.
4. **No inventar datos.** Si a un requisito le falta información, el sistema
   pregunta; nunca rellena con supuestos presentados como requisitos válidos.
   Nunca se inventan scores, Gates ni métricas de benchmark.
5. **Separación de roles.** Cada IA es un servicio con su propio system prompt
   en `backend/services/prompts/`.
6. **Máquina de estados única** en `backend/services/workflow.py`.

## Configuración y secretos

- `backend/config.py` es el único módulo que lee variables de entorno.
- Ningún archivo fuera de `.env` menciona un nombre de modelo literal.
- **Nunca** se suben API keys, tokens ni contraseñas. `.env` está en
  `.gitignore`; `.env.example` se mantiene con valores vacíos.

## Evidencia (requisito del parcial)

- Toda métrica reportada debe venir de una ejecución real y reproducible.
- Registrar modelo, versión, parámetros de inferencia y fecha de cada ejecución.
- Indicar si cada componente (LLM, STT, TTS) corre local o en un servicio remoto.

## Estilo

- Código y comentarios en español; identificadores en inglés.
- Sin frameworks de frontend, Docker, Redis, Celery ni WebSockets salvo que
  el equipo lo decida y lo justifique.
- Verificar cada cambio ejecutándolo de verdad (servidor, endpoints, BD), no
  solo leyendo el código.
