# Punto 3 — Ejecuciones exploratorias y experimentos

Antes de la ejecución final (`evidence/punto3_casos/`) hubo dos ejecuciones
completas de los casos A, B y C que **no cumplieron** y que llevaron a
cambios en el sistema. Se conservan sin modificar como evidencia de por qué
se tomó cada decisión. Todos los números de esta página se pueden verificar
en los archivos de cada carpeta.

## Cronología

| # | Configuración | Resultado | Hallazgo | Cambio |
|---|---|---|---|---|
| 0 | Evaluador `nemotron-3.5-lightning`, 9 análisis en paralelo | El servidor dejó de responder; los análisis se interrumpieron (no hay carpeta: no se generó evidencia) | `QueuePool limit of size 5 overflow 10 reached`: cada análisis retenía 2 conexiones a PostgreSQL durante los minutos de espera a la IA | Commit `ecfeff4`: el proceso en segundo plano y la petición liberan la conexión mientras esperan a la IA (2 tests lo reproducen) |
| 1 | Evaluador `nemotron-3.5-lightning`, Mejorador `kimi-k3` | 3/8 corridas cumplen (C1 se perdió por un corte al consultar el estado) — `ejecucion_1_nemotron_lightning/` | (a) `kimi-k3` devolvió `content` vacío; (b) el Evaluador devolvió JSON mal formado; (c) las versiones mejoradas puntuaban **menos** que las originales porque el Evaluador trataba los `[POR DEFINIR]` como ambigüedad | Experimento de evaluadores (abajo) |
| 2 | Evaluador `nemotron-3-super-120b` con modo JSON, reintento de respuestas vacías | 7/9 corridas cumplen — `ejecucion_2_nemotron_super_sin_respaldo/` | A, B y C cumplen su comportamiento principal en las 3 corridas; fallan las 2 aclaraciones de B: `kimi-k3` degeneró (`reasoning_content: "!!!!"`, `content: null`) en los 3 reintentos | Diagnóstico de `kimi-k3` y modelo de respaldo para el Mejorador (commit `a7a1ded`) |

## Experimento 1 — ¿Qué modelo evaluador respeta la regla de los `[POR DEFINIR]`?

`experimento_evaluador/experimento_evaluador.py`: los mismos 3 pares
(original, mejorado) de la ejecución 1, evaluados por 3 modelos con modo
JSON. Salida literal en `experimento_evaluador/salida.txt`.

| Evaluador | Delta B_2 / B_3 / C_2 | Tiempo por evaluación | Observación |
|---|---|---|---|
| `nvidia/nemotron-3.5-lightning-30b-a3b` | −7 / −6 / −20 | 66-142 s | Baja claridad y atomicidad de versiones ya separadas en REQ-n |
| `nvidia/nemotron-3-super-120b-a12b` | +18 / +24 / +7 | 13-24 s | Sube claridad/atomicidad, mantiene baja la completitud, detecta la contradicción de C (consistencia 2) |
| `moonshotai/kimi-k3` | solo 1 de 3 pares completó (+34) | 86-96 s | 3 respuestas "200 sin choices"; además es el mismo modelo que el Mejorador (se evaluaría a sí mismo) |

**Decisión:** Evaluador = `nemotron-3-super-120b-a12b` (independiente del
Mejorador, más rápido y consistente con las instrucciones).

## Experimento 2 — Modo JSON por modelo

Llamadas directas pidiendo un JSON simple:

- `nemotron-3.5-lightning` (1 llamada por configuración): con
  `response_format: json_object` devolvió JSON limpio; sin él, lo envolvió
  en un bloque de código.
- `kimi-k3` (3 llamadas por configuración): **sin** modo JSON, 3/3
  correctas; **con** modo JSON, 1/3 con `content` vacío.

**Decisión:** el modo JSON se configura por modelo (`LLM_JSON_MODE_MODELS`),
activo solo para el Evaluador.

## Experimento 3 — ¿Por qué `kimi-k3` responde vacío?

`experimento_evaluador/diagnostico_cache_kimi.py` reconstruye la petición
exacta del Mejorador de una aclaración fallida y la envía 3 veces idéntica
y 3 veces con una variación mínima (secuencialmente):

| Petición | Resultado | Tokens en caché |
|---|---|---|
| idéntica #1 | correcta | 0 / 2971 |
| idéntica #2 | **degenerada** (`"Produce!!!!!!!!!!!!!"`, content vacío) | 0 / 2971 |
| idéntica #3 | correcta | 0 / 2971 |
| variada #1-#3 | correctas | 0, 0 y 2944 / 2976 |

La degeneración ocurre **con 0 tokens en caché**: no es la caché de NVIDIA
(hipótesis descartada) sino una degeneración aleatoria del modelo, más
frecuente con prompts largos (las aclaraciones) y con varias llamadas
simultáneas.

Candidatos a modelo de respaldo, probados con esa misma aclaración:
`nemotron-3-super-120b` respondió en 46 s usando los datos del stakeholder
sin inventar; `z-ai/glm-5.3` y `deepseek-ai/deepseek-v4.1-flash` agotaron el
timeout (3 × 180 s); `mistralai/mistral-large` no está disponible para la
cuenta (404 "Not found for account").

**Decisión:** Mejorador principal `kimi-k3`, respaldo
`nemotron-3-super-120b-a12b` (`IMPROVER_FALLBACK_MODEL`) solo cuando el
principal no da una respuesta usable; queda registrado en cada análisis.

## Otros hallazgos

- `deepseek-ai/deepseek-v4-pro-0813`, el Auditor original del proyecto,
  responde **410 Gone**: NVIDIA lo retiró del servicio.
- Las consultas de estado del script fallaban ocasionalmente con
  `ReadError` / `RemoteProtocolError`: el script consulta cada 5 s y
  uvicorn cierra las conexiones inactivas a los 5 s. No afecta a los
  análisis; el script ahora reintenta la consulta (commit `8364cd1`).
