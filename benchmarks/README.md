# /benchmarks

Benchmark de modelos (Componente 4): 3 modelos × 3 fases (Requisitos,
Arquitectura/Diseño, Implementación) × 3 corridas = 27 ejecuciones auditables.

| Archivo | Contenido |
|---|---|
| `modelos.json` | Los 3 modelos (local, cloud generalista, cloud de razonamiento), los parámetros de inferencia comunes, la política de reintentos y la justificación de cada decisión |
| `proveedores.py` | Invocación uniforme de Ollama y NVIDIA con streaming; mide TTFT, latencia, tokens y recursos locales; detecta respuestas vacías y degeneradas |
| `results.csv` | Métricas agregadas por modelo y fase (punto 6) |
| `execution_log.csv` | Una fila por ejecución: fecha, modelo, versión, parámetros, TTFT, latencia, tokens, costo, recursos y resultado del Quality Gate (punto 6) |

La preparación y los experimentos que justifican la configuración están en
`evidence/punto5_proveedores/README.md`. Para probar los proveedores:

```bash
python scripts/probar_proveedores.py --repeticiones 3
```

Antes de medir, cerrar los programas que usen la GPU o mucha RAM: el modelo
local comparte la GPU de 6 GB y parte de él corre en CPU.
