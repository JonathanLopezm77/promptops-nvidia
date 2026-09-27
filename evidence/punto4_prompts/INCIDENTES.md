# Punto 4 — Incidentes durante la validación

Registro de lo que salió mal durante la validación de los 7 prompts, con su
causa y corrección. Nada de esto se ocultó ni se editó en los datos salvo lo
indicado explícitamente.

## 1. Arquitectura, primer run en ERROR (kimi-k3 degenerado)

- Run `07017870-a79e-4d6c-a384-c98c136fba78`, 27/9/2026 ~12:20.
- En una auto-iteración el Optimizer (`moonshotai/kimi-k3`) devolvió
  `content` vacío en los 3 reintentos (la misma degeneración documentada en
  `evidence/punto3_casos_exploratorio/`). El Optimizer de prompts no tenía
  modelo de respaldo.
- Corrección: commit `60c9778` (respaldo `IMPROVER_FALLBACK_MODEL` también
  para el Optimizer, y registro por iteración del modelo usado).
- Se validó de nuevo la fase: run `36a2f1b0-69cc-4fff-a535-e941a5751c67`. El
  run fallido queda en el manifiesto como `intentos_previos` y se exporta.

## 2. Arquitectura, run aprobado marcado ERROR por los tests y luego sobrescrito con COMPLETED

Cronología del run `36a2f1b0-69cc-4fff-a535-e941a5751c67`:

| Hora (UTC-5) | Hecho |
|---|---|
| 12:45:22 | El humano aprueba la iteración 5. |
| ~12:5x | El humano pulsa EJECUTAR: el run pasa a EXECUTING y el Executor empieza a correr. |
| 12:54:51 | Se ejecutan los tests del proyecto antes de un `git push`. Un test arranca la app con `TestClient` y la recuperación de arranque (pensada para reinicios del servidor) pasa a ERROR el run en la base de datos real, con el mensaje "el servidor se reinició". No hubo reinicio. |
| 12:57:19 | El Executor termina bien, guarda el resultado (11 334 caracteres) y marca el run COMPLETED, sobrescribiendo el ERROR. |

Dos defectos distintos:

1. **Los tests tocaban datos reales.** La recuperación solo estaba
   desactivada para los análisis de requisitos, no para los runs.
   Corrección: `tests/conftest.py` la desactiva en todos los tests; un test
   reproduce el incidente (falla sin el parche y pasa con él).
2. **Las transiciones se validaban contra la copia en memoria.** Las
   sesiones de fondo usan `expire_on_commit=False`; el Executor validó
   `EXECUTING -> COMPLETED` contra su copia desactualizada, aunque en la BD
   el run ya estaba en ERROR (`ERROR -> COMPLETED` es inválida). Corrección:
   toda transición lee el estado de la BD con `SELECT ... FOR UPDATE`, y
   `complete_execution` lo verifica antes de guardar el resultado. Un test
   reproduce el caso (falla con la validación en memoria y pasa con la de
   la BD).

**Datos corregidos a mano (única edición):** el run quedó `COMPLETED` pero
con el `error_message` falso de las 12:54. Como la ejecución sí terminó
correctamente, se borró ese `error_message`. La aprobación humana de la
iteración 5 no se modificó.

**Observación sobre el contenido aprobado:** la versión aprobada de
Arquitectura pide al modelo afirmar que verificó el diagrama "con un linter
de Mermaid y un script de trazabilidad" (no puede ejecutarlos) e incluye un
"Incentivo de calidad". Se señaló antes de la aprobación; ver la revisión
manual.
