# /evidence

Respaldo de cada métrica y decisión del parcial: respuestas crudas de los
modelos, calificaciones, manifiestos (modelo, versión, parámetros, fecha) y
revisiones manuales. Nunca incluye API keys ni datos personales.

| Carpeta | Punto | Contenido principal |
|---|---|---|
| `punto3_casos/` | 3 — Casos mínimos A-D | `RESULTADOS.md` (10/10: A, B y C en 3 corridas cada uno y D por voz), `REVISION_MANUAL.md`, corridas completas |
| `punto3_casos_exploratorio/` | 3 | Ejecuciones previas y el experimento que eligió el Evaluador |
| `punto4_prompts/` | 4 — 7 prompts del SDLC | Runs de validación en la plataforma, `REVISION_MANUAL.md`, `INCIDENTES.md`, manifiesto (métricas en `prompts/validation_metrics.csv`) |
| `punto5_proveedores/` | 5 — Ollama y proveedores | `README.md` (configuración y hallazgos), experimentos, prueba de los 3 modelos |
| `punto6_benchmark/` | 6 — Benchmark de 27 ejecuciones | `RESULTADOS.md`, `REVISION_MANUAL.md`, ejecuciones y calificaciones (tablas en `benchmarks/results.csv` y `execution_log.csv`) |
| `punto7_seleccion/` | 7 — Selección de modelo por fase | `SELECCION.md`, `FUNCION_OBJETIVO.md`, `SONDEO.md` |
| `punto8_sdd/` | 8 — SDD | `README.md`, `DECISIONES.md` (Quality Gates de la cadena), `DEMOSTRACION.md` |
| `punto9_mapa/` | 9 — Mapa mental | Mapa interactivo (`frontend/mapa.html`, público en Render), versiones Markmap y Mermaid con sus imágenes |
