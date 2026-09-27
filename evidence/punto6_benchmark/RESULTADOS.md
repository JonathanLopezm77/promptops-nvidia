# Resultados del benchmark (27 ejecuciones)

Fuente: `benchmarks/results.csv` (medias de 3 corridas por celda) y
`benchmarks/execution_log.csv`. Definiciones de cada métrica y del Quality
Gate: `benchmarks/DISENO.md`. Las 27 ejecuciones terminaron bien (0 fallidas).

Modelos: **local** = `qwen2.5-coder:7b` (Ollama, RTX 3050 6 GB) ·
**Kimi** = `moonshotai/kimi-k3` (cloud generalista) ·
**Nemotron** = `nvidia/nemotron-3-super-120b-a12b` (cloud razonamiento).

## 1. Calidad por fase

"Éxito" = Task Success Rate; "QG" = Quality Gate Score medio (0-100);
"DE" = desviación estándar del QG entre las 3 corridas (Consistency);
"Violac." = Constraint Violation Rate; "Supuestos" = Unsupported
Assumption / Hallucination Rate; "Schema" = Schema Compliance.

### Fase 1 — Requisitos

| Modelo | Éxito | QG | DE | Violac. | Supuestos | Schema | QG con el otro juez |
|---|---|---|---|---|---|---|---|
| Kimi | **3/3** | 85.3 | 5.5 | 0 % | **0 %** | 100 % | 88.5 |
| Nemotron | 2/3 | **88.8** | 5.8 | 0 % | 33 % | 100 % | 88.7 |
| Local | 0/3 | 68.3 | 3.5 | 0 % | 100 % | 100 % | 75.3 |

- Los 3 modelos cumplen el formato, ponen criterio de aceptación a todos los
  requisitos y numeran bien (verificabilidad y trazabilidad al máximo en las 9).
  La diferencia está en el Quality Score del juez y en **inventar valores**.
- **Local inventa en las 3 corridas** (entre otros): 10.000 usuarios simultáneos, 2 segundos,
  percentil 95 y, en una corrida, un tope de 100 productos, cuando la necesidad solo da
  "20000" (catálogo). Pregunta 1-3 de los 4 huecos plantados.
- Nemotron inventó un "95 %" en una corrida (`f1_cloud_razonamiento_2`); Kimi
  nunca inventó y preguntó 3-4 de los 4 huecos.
- Nemotron tiene la media más alta, pero la diferencia con Kimi (3.5 puntos) es
  menor que la variación entre corridas de cada uno (DE ≈ 5.5): no es una
  diferencia confiable con 3 corridas.

### Fase 3 — Arquitectura

| Modelo | Éxito | QG | DE | Violac. | Supuestos | Schema | QG con el otro juez |
|---|---|---|---|---|---|---|---|
| Kimi | 3/3 | **93.0** | 3.5 | 0 % | 100 % | 100 % | 96.0 |
| Nemotron | 3/3 | 92.0 | **1.7** | 0 % | 100 % | 100 % | 96.0 |
| Local | 2/3 | 82.7 | 7.2 | 33 % | 0 % | 100 % | 72.0 |

- Kimi y Nemotron quedan prácticamente empatados; Nemotron es más constante y
  2.7 veces más rápido (70 s contra 188 s).
- El 100 % de "supuestos" de los modelos cloud se debe a que **las 6 salidas
  marcan como hecho `[x]` haber verificado el diagrama con un linter de
  Mermaid o un script de trazabilidad**, cosa que ninguno puede hacer. Lo
  induce el prompt aprobado en el punto 4 (su checklist final); el modelo
  local no lo hace. Ver `REVISION_MANUAL.md` §2.
- Local eligió **microservicios** en una corrida (viola R1, monolito modular)
  y aun así declaró "R1 cumplida por la arquitectura de microservicios".

### Fase 4 — Implementación

| Modelo | Éxito | QG | DE | Pruebas ocultas | Lint (ruff) |
|---|---|---|---|---|---|
| Kimi | **3/3** | **100.0** | 0.0 | 34/34 en las 3 | 0 avisos en las 3 |
| Nemotron | 1/3 | 83.6 | 1.2 | 34, 33, 33 de 34 | ≥ 10 avisos (UP, I) en las 3 |
| Local | 0/3 | 69.2 | 1.2 | 27, 26, 26 de 34 | ≥ 10 avisos en las 3 |

- Kimi entregó código correcto, limpio y trazable en las 3 corridas.
- Nemotron falla la misma prueba en 2 corridas: `list_items` devuelve la lista
  en orden de inserción, suponiendo que coincide con el orden por fecha, pero
  la fecha es un parámetro (`now`) y el contrato pide ordenar por `added_at`.
- Local: `round(drop_pct, 2, ROUND_HALF_UP)` lanza `TypeError` (`round()`
  admite 2 argumentos), con lo que falla todo SPEC-04; además `list_items` no
  ordena ni devuelve una copia.
- Los avisos de lint de Nemotron y Local son de estilo (`typing.List` en vez
  de `list`, orden de imports; el local además deja un import sin usar): no afectan la corrección, pero el Quality
  Gate definido les quita los 15 puntos de lint.

## 2. Latencia, tokens, costo y recursos

| Fase | Modelo | TTFT de respuesta (s) | Latencia total (s) | DE latencia | Tokens entrada / salida |
|---|---|---|---|---|---|
| 1 | Kimi | 23.7 | 64.1 | 15.6 | 1257 / 1164 |
| 1 | Nemotron | 24.6 | 30.3 | 9.5 | 1005 / 3261 |
| 1 | Local | **1.1** | 36.0 | 1.1 | 1086 / 596 |
| 3 | Kimi | 25.4 | 188.2 | 5.7 | 1812 / 4303 |
| 3 | Nemotron | 27.4 | 69.6 | 23.7 | 1493 / 6347 |
| 3 | Local | **1.1** | 86.2 | 8.2 | 1604 / 1450 |
| 4 | Kimi | 24.3 | 82.0 | 0.7 | 2701 / 1620 |
| 4 | Nemotron | 7.4 | **21.1** | 4.7 | 2367 / 2676 |
| 4 | Local | **1.3** | 55.1 | 2.4 | 2433 / 784 |

- **TTFT**: el modelo local empieza a responder en ~1 s; los cloud tardan
  7-27 s porque razonan antes de escribir (los tokens de salida de Nemotron
  incluyen su razonamiento).
- **Latencia total**: Nemotron es el más rápido en todas las fases
  (~90-130 tokens/s); Kimi el más lento (~18-23 tokens/s); el local genera
  ~14-17 tokens/s.
- Los tokens de entrada difieren entre modelos con el mismo prompt porque
  cada uno usa su propio tokenizador.
- **Costo**: 0 USD. Los modelos cloud se usaron en la capa gratuita de NVIDIA,
  que no publica precio, y el local no tiene costo por token. No se inventa
  un precio.
- **Recursos del modelo local**: el modelo cargado ocupa 5.4 GB, de los
  que 4.0 GB caben en la VRAM de 6 GB (**73 % en GPU**). El resto corre en la
  CPU, lo que explica el uso de ~5.7 núcleos (570 % de CPU) y la baja
  velocidad de generación. Proceso de Ollama: 1.4-1.7 GB de RAM; GPU hasta
  93-96 % de uso.
- **Confiabilidad del servicio**: 28 intentos para 27 ejecuciones. Kimi
  devolvió una respuesta vacía una vez (`f1_cloud_generalista_2`) y el
  reintento la resolvió.

## 3. Jueces: ¿cambia la conclusión según quién califica?

Cada salida de las fases 1 y 3 la calificaron dos jueces (DISENO.md §4).

| Qué | gpt-oss-20b (principal, neutral) | Nemotron (secundario, compite) |
|---|---|---|
| Juicios obtenidos | 18/18 (1 tras recalificar, ver REVISION_MANUAL §4) | 18/18 |
| Latencia media fase 1 / fase 3 | 153 s / 87 s | 16 s / 27 s |

Diferencia media (Nemotron − gpt-oss) en la nota del juez, por modelo calificado:

| Salidas de | Fase 1 (Quality Score 0-100) | Fase 3 (revisión 1-10) |
|---|---|---|
| Kimi | +6.3 | +1.0 |
| Nemotron (**autoevaluación**) | −0.3 | +1.3 |
| Local | +14.0 | −2.0 |

- **No hay evidencia de que Nemotron se favorezca a sí mismo**: con sus
  propias salidas es tan exigente como el juez neutral en requisitos (−0.3) y
  apenas más generoso en arquitectura, igual que con Kimi.
- Nemotron es **más indulgente con los requisitos del modelo local** (+14), que
  son justamente los que inventan valores; gpt-oss los castiga más. En
  arquitectura local es algo más estricto.
- **El orden de los modelos es el mismo con cualquiera de los dos jueces**
  (columna "QG con el otro juez" de las tablas de la §1): en fase 1 Nemotron ≈
  Kimi > Local; en fase 3 Kimi ≈ Nemotron > Local. Las conclusiones no
  dependen de la elección del juez.
- Un mismo juez también varía: Nemotron dio 7 y luego 3 a la misma salida
  `f3_local_2` en dos calificaciones.

## 4. Conclusiones (base para el punto 7)

1. **Implementación: Kimi** es claramente el mejor: 100 en las 3 corridas,
   sin variación. Nemotron es 4 veces más rápido pero falló un requisito del
   contrato en 2 de 3 corridas.
2. **Arquitectura: empate Kimi / Nemotron** en calidad; Nemotron es más
   constante y mucho más rápido. Ambos afirman verificaciones que no hicieron,
   por el prompt aprobado: hay que corregir ese prompt, no elegir otro modelo.
3. **Requisitos: Kimi y Nemotron sin diferencia confiable** en calidad; Kimi
   fue el único que nunca inventó valores y cumplió la tarea 3 de 3 veces.
4. **El modelo local (7B, 73 % en GPU) no es apto** para requisitos ni
   implementación en esta tarea: inventa valores de negocio y genera código
   con errores. Su ventaja es el TTFT (~1 s), la privacidad y el costo cero;
   con una GPU que lo cargue entero sería más rápido, pero la calidad no
   cambiaría.

Límites: una sola entrada por fase y 3 corridas por combinación (DISENO.md §6).
