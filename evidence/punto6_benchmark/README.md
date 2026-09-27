# Punto 6 — Benchmark de 27 ejecuciones (Componente 4)

3 modelos × 3 fases (Requisitos, Arquitectura, Implementación) × 3 corridas.
El diseño completo (qué se mantiene constante, Quality Gate de cada fase,
jueces, métricas y límites) está en `benchmarks/DISENO.md` y se fijó
**antes** de ejecutar.

- Resultados y conclusiones: [`RESULTADOS.md`](RESULTADOS.md)
- Revisión manual de salidas y calificaciones: [`REVISION_MANUAL.md`](REVISION_MANUAL.md)
- Tablas exigidas por el enunciado: `benchmarks/results.csv` (9 filas: fase × modelo)
  y `benchmarks/execution_log.csv` (27 filas: una por ejecución)

## Contenido de esta carpeta

| Ruta | Qué es |
|---|---|
| `manifiesto.json` | Máquina (CPU, RAM, GPU), versión exacta de cada modelo (digest de Ollama; id y fecha para NVIDIA), parámetros, orden aleatorio de ejecución (semilla 20260927) |
| `ejecuciones/*.json` | Las 27 ejecuciones: prompt enviado completo, salida completa, razonamiento, TTFT, tokens, recursos, intentos y errores previos, respuesta cruda del servicio |
| `calificaciones/*.json` | La calificación de cada ejecución: componentes del puntaje, respuesta completa de **ambos** jueces, pruebas fallidas, avisos de lint, supuestos detectados |
| `calificaciones_descartadas/` | Primera calificación de `f3_local_2`, reemplazada (ver `REVISION_MANUAL.md` §4) |
| `ejecutar.log`, `calificar.log` | Salida de consola de cada paso (los `.err` están vacíos: sin errores) |
| `experimentos/` | Pruebas previas que justificaron decisiones: juez neutral, esfuerzo de razonamiento del juez, mutantes de las pruebas ocultas |

## Cómo reproducir

```bash
# 1. Ollama con qwen2.5-coder:7b y la clave de NVIDIA en .env
python scripts/benchmark.py plan         # muestra el orden de las 27 ejecuciones
python scripts/benchmark.py ejecutar     # genera ejecuciones/ (se salta las ya hechas)
python scripts/benchmark.py calificar    # genera calificaciones/ (jueces + tests + lint)
python scripts/benchmark.py informe      # genera benchmarks/results.csv y execution_log.csv
# Recalificar una ejecución concreta:
python scripts/benchmark.py --solo f3_local_2 calificar --forzar
```

Las 27 ejecuciones se hicieron el 2026-09-27 entre 20:06 y 20:39 UTC, con la
PC sin otros programas que usaran la GPU. Los modelos cloud no publican
versión: se registra su id y la fecha.
