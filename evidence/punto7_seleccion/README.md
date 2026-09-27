# Punto 7 — Análisis y selección de modelo por fase

Qué modelo usar en cada una de las 7 fases del SDLC, con una función
objetivo explícita (enunciado §7.1).

| Documento | Contenido |
|---|---|
| [`SELECCION.md`](SELECCION.md) | **La decisión**: modelo por fase, condiciones de uso, alternativa y justificación con evidencia |
| [`FUNCION_OBJETIVO.md`](FUNCION_OBJETIVO.md) | La función (5 criterios, pesos, regla de elegibilidad) aplicada a las 27 ejecuciones y su análisis de sensibilidad |
| [`SONDEO.md`](SONDEO.md) | Sondeo de las fases 2, 5, 6 y 7 (1 corrida por modelo) y la revisión manual de sus salidas |

Configuración resultante (para el punto 8): `benchmarks/seleccion_por_fase.json`.

## Archivos de esta carpeta

| Ruta | Qué es |
|---|---|
| `salida.txt`, `utilidad_por_perfil.csv` | Utilidad de cada modelo por fase y escenario de pesos |
| `montecarlo_pesos.csv` | % de victorias con 20 000 vectores de pesos aleatorios (con y sin la regla de elegibilidad) |
| `bootstrap_corridas.csv` | % de victorias remuestreando las corridas 10 000 veces |
| `precios_publicos.json` | Precios por token de Kimi K3 y Nemotron 3 Super (API pública de OpenRouter, 2026-09-27) |
| `sondeo/` | Las 12 ejecuciones del sondeo (prompt y salida completos), sus calificaciones, `sondeo.csv` y el manifiesto |
| `experimentos/nemotron_f2_presupuesto*` | Nemotron en la especificación con `max_tokens 16384` (variante, 2 corridas) |

## Cómo reproducir

```bash
python scripts/seleccion_modelos.py          # función objetivo y sensibilidad (semillas fijas)
python scripts/sondeo_fases.py ejecutar      # 12 ejecuciones del sondeo (reanudable)
python scripts/sondeo_fases.py calificar
python scripts/sondeo_fases.py informe
python evidence/punto7_seleccion/experimentos/nemotron_f2_presupuesto.py
```

Código: `benchmarks/seleccion.py`, `benchmarks/calificadores_sondeo.py`,
`benchmarks/mutantes.py`, `benchmarks/casos_sondeo/`. Pruebas:
`tests/test_seleccion_modelos.py` (7) y `tests/test_calificadores_sondeo.py` (19).
