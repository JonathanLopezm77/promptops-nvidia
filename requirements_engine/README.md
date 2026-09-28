# /requirements_engine — Motor de Ingeniería de Requisitos multimodal (Componente 1)

El código del motor vive dentro del backend existente (se **amplió** la
plataforma de PromptOps, no se duplicó). Esta carpeta es el índice de sus
piezas y la documentación del subsistema de voz ([`VOZ.md`](VOZ.md)).

## Flujo (enunciado §4.1) y dónde está cada paso

| Paso | Implementación |
|---|---|
| Entrada por texto o voz | `frontend/requisitos.html`, `frontend/requisitos.js` (pantalla `/requisitos.html`) |
| Speech-to-Text | `frontend/voz.js` (Web Speech API) — ver [`VOZ.md`](VOZ.md) |
| Requisito original | Se guarda tal cual: tabla `requirement_analyses` (`backend/schema_requirements.sql`) |
| Motor de calidad (10 criterios, ISO/IEC/IEEE 29148) | Evaluador: `backend/services/requirements_evaluator.py`, prompt en `backend/services/prompts/requirements_evaluator_system_prompt.py`, esquema en `backend/schemas/requirements.py` |
| Diagnóstico + métricas + preguntas de aclaración | Misma evaluación: puntaje/hallazgo/recomendación por criterio, términos ambiguos, preguntas e información faltante |
| Requisito mejorado | Mejorador: `backend/services/requirements_improver.py` (marca `[POR DEFINIR]` lo que falta en vez de inventarlo; detector de números sin respaldo) |
| Nueva validación del mejorado | `backend/services/requirements_workflow.py` (reevalúa y calcula el delta y la versión recomendada) |
| Retroalimentación en pantalla + TTS | `frontend/requisitos.js` + `speechSynthesis` (`frontend/voz.js`); cada lectura se registra en `tts_log` |
| Aclaraciones del stakeholder | `POST /api/requirements/{id}/clarify` crea un análisis hijo con las respuestas |

## Puntaje

- Cada criterio de 1 a 10. **Requirements Quality Score** = promedio × 10 (0-100).
- **Alta calidad**: Score ≥ 80 y ningún criterio < 6. Un requisito de alta
  calidad no se modifica (caso A).
- Se conserva todo para auditoría: original, evaluaciones (con la respuesta
  cruda del modelo), mejora, tokens, latencias, modelo y metadatos de voz.

## API

| Método | Ruta | Uso |
|---|---|---|
| POST | `/api/requirements` | Crea un análisis (texto o voz con `stt_metadata`); responde 202 y procesa en segundo plano |
| GET | `/api/requirements` · `/api/requirements/{id}` | Lista / detalle con evaluaciones y delta |
| POST | `/api/requirements/{id}/clarify` | Respuestas a las preguntas de aclaración |
| POST | `/api/requirements/{id}/tts` | Registra una lectura en voz alta |

## Modelos y confiabilidad

Evaluador `nvidia/nemotron-3-super-120b-a12b` (modo JSON) y Mejorador
`moonshotai/kimi-k3` con respaldo en Nemotron (`IMPROVER_FALLBACK_MODEL`):
decisiones y experimentos en `evidence/punto3_casos_exploratorio/`.

## Evidencia

- Casos A, B, C (3 corridas cada uno, 9/9 cumplen): `evidence/punto3_casos/`.
- Caso D (voz): ver [`VOZ.md`](VOZ.md) §4.
- Pruebas: `tests/test_requirements.py`, `tests/test_requirements_api.py`, `tests/test_casos_requisitos.py`.
