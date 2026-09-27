# Función objetivo para elegir el modelo de cada fase

El enunciado (§7.1) pide identificar "el modelo más conveniente para una tarea
específica bajo una función objetivo explícita de calidad, cumplimiento,
latencia, costo y recursos". Esta es esa función, aplicada a las 27
ejecuciones del punto 6 (`benchmarks/execution_log.csv`).

- Código: `benchmarks/seleccion.py` (funciones puras, con 7 pruebas en
  `tests/test_seleccion_modelos.py`) y `scripts/seleccion_modelos.py`.
- Salidas: `salida.txt`, `utilidad_por_perfil.csv`, `montecarlo_pesos.csv`,
  `bootstrap_corridas.csv` (esta carpeta). Reproducible:
  `python scripts/seleccion_modelos.py` (semillas fijas).

## 1. Los 5 criterios (cada uno en [0, 1], 1 = mejor)

| Criterio | Fórmula | Por qué así |
|---|---|---|
| **Calidad** | (media del Quality Gate − su desviación estándar) / 100 | Integra *Quality Gate Score* y *Consistency Across Runs*: un modelo que alterna salidas buenas y malas es más riesgoso que uno estable con la misma media. Es una estimación conservadora de la calidad que se va a obtener |
| **Cumplimiento** | 0.5 × *Task Success Rate* + 0.5 × media(1 − *Constraint Violation Rate*, 1 − *Hallucination Rate*, *Schema Compliance*) | La mitad es "¿cumplió la tarea?" (la métrica principal del enunciado); la otra mitad, las otras tres tasas de cumplimiento, con el mismo peso entre ellas |
| **Latencia** | menor duración media de la fase / duración media del modelo | Relativa al más rápido de la fase. Se usa la duración **con reintentos** (lo que realmente espera el usuario; a Kimi le suma su respuesta vacía) |
| **Costo** | menor costo de la fase / costo del modelo | Costo real = 0 USD para todos (capa gratuita de NVIDIA y modelo local), así que vale 1 para todos. Escenario de pago: ver §4 |
| **Recursos** | 1 − máx(VRAM del modelo / VRAM de la GPU, CPU usada / CPU total, RAM / RAM total) | Qué parte de la máquina del equipo ocupa. Cloud = 1. Local = 0.34 (el modelo ocupa 4.0 de 6 GB de VRAM: 66 %) |

**Utilidad** = Σ peso × criterio.

**Regla de elegibilidad** (restricción dura, no un peso): un modelo solo puede
ser elegido si cumple la tarea en la mayoría de las corridas (*Task Success
Rate* ≥ 0.5). Un artefacto que no pasa su Quality Gate no puede pasar a la
siguiente fase (Componente 3), así que un modelo que falla la mayoría de las
veces no es apto, por rápido o barato que sea.

## 2. Pesos base y por qué

| Calidad | Cumplimiento | Latencia | Costo | Recursos |
|---|---|---|---|---|
| 0.40 | 0.30 | 0.15 | 0.10 | 0.05 |

- **Calidad + cumplimiento = 70 %**: en una cadena SDLC, el error de una fase
  se propaga a las siguientes (un requisito inventado termina en código y
  pruebas). Corregirlo después cuesta más que esperar unos segundos más.
- **Latencia 15 %**: importa en el uso interactivo (el usuario espera cada
  fase y puede iterar), pero no por encima de la corrección.
- **Costo 10 % y recursos 5 %**: hoy el costo es 0 y los recursos solo
  diferencian al modelo local. Se incluyen para que la función siga siendo
  válida si cambian (§4).

Los pesos son un juicio del equipo. Por eso la §4 prueba si la elección
cambia con otros pesos.

## 3. Resultado con los pesos base

| Fase | Modelo | Calidad | Cumplim. | Latencia | Costo | Recursos | **Utilidad** | Elegible |
|---|---|---|---|---|---|---|---|---|
| 1 Requisitos | **Nemotron** | 0.831 | 0.778 | 1.000 | 1 | 1 | **0.866** | sí |
| | Kimi | 0.798 | 1.000 | 0.411 | 1 | 1 | 0.831 | sí |
| | Local | 0.648 | 0.333 | 0.826 | 1 | 0.34 | 0.600 | **no** (0/3) |
| 3 Arquitectura | **Nemotron** | 0.903 | 0.833 | 1.000 | 1 | 1 | **0.911** | sí |
| | Kimi | 0.895 | 0.833 | 0.370 | 1 | 1 | 0.814 | sí |
| | Local | 0.754 | 0.778 | 0.802 | 1 | 0.34 | 0.772 | sí (2/3) |
| 4 Implementación | **Kimi** | 1.000 | 1.000 | 0.257 | 1 | 1 | **0.888** | sí |
| | Nemotron | 0.824 | 0.667 | 1.000 | 1 | 1 | 0.830 | **no** (1/3) |
| | Local | 0.680 | 0.500 | 0.376 | 1 | 0.34 | 0.596 | **no** (0/3) |

Comprobación a mano (fase 1, Nemotron): calidad = (88.83 − 5.75)/100 = 0.831;
cumplimiento = 0.5 × 2/3 + 0.5 × media(1, 2/3, 1) = 0.778;
utilidad = 0.4 × 0.831 + 0.3 × 0.778 + 0.15 + 0.10 + 0.05 = 0.866.

## 4. ¿Cambia la elección? Análisis de sensibilidad

**a) Otros perfiles de pesos** (calidad / cumplimiento / latencia / costo / recursos):

| Escenario | Fase 1 | Fase 3 | Fase 4 |
|---|---|---|---|
| Base (40/30/15/10/5) | Nemotron | Nemotron | Kimi |
| Calidad primero (60/30/5/5/0) | **Kimi** | Nemotron | Kimi |
| Interactivo (30/20/40/5/5) | Nemotron | Nemotron | Kimi |
| Costo y recursos (30/20/10/20/20) | Nemotron | Nemotron | Kimi |
| Pesos iguales (20 c/u) | Nemotron | Nemotron | Kimi |
| Base + **precio público** | Nemotron | Nemotron | Kimi |
| Costo y recursos + precio público | Nemotron | Nemotron | Kimi |
| Base + notas del **otro juez** | Nemotron | Nemotron | Kimi |

**b) Pesos aleatorios**: 20 000 vectores de pesos al azar (uniformes sobre
todas las combinaciones posibles que suman 1). Porcentaje de veces que gana
cada modelo:

| Fase | Con la regla de elegibilidad | Sin la regla |
|---|---|---|
| 1 | Nemotron 75.8 %, Kimi 24.2 % | igual |
| 3 | Nemotron 100 % | Nemotron 100 % |
| 4 | Kimi 100 % | Nemotron 55.5 %, Kimi 44.5 % |

**c) Remuestreo de las corridas (bootstrap)**: 10 000 veces se toman al azar,
con reemplazo, 3 corridas de cada modelo y se recalcula el ganador con los
pesos base. Mide cuánto depende la elección de qué corridas salieron:
fase 1 Nemotron 70.9 % / Kimi 29.1 %; fase 3 Nemotron 99.0 %; fase 4 Kimi 96.2 %.

**Escenario de pago.** Costo por ejecución si se pagara con los precios
públicos de OpenRouter (consultados el 2026-09-27, `precios_publicos.json`:
Kimi 3 / 15 USD por millón de tokens de entrada / salida; Nemotron
0.08 / 0.45):

| Fase | Kimi | Nemotron | Local |
|---|---|---|---|
| 1 | 0.0212 USD | 0.0016 USD | 0 |
| 3 | 0.0700 USD | 0.0030 USD | 0 |
| 4 | 0.0324 USD | 0.0014 USD | 0 |

Nemotron es 14-24 veces más barato por ejecución aunque genera más tokens (su
razonamiento). No cambia ninguna elección, pero amplía la ventaja de Nemotron
en las fases 1 y 3. Limitación: solo se cuentan los tokens del intento final;
el intento vacío de Kimi en `f1_cloud_generalista_2` no queda registrado con
tokens.

## 5. Lectura de la sensibilidad

- **Fase 3: Nemotron, sin discusión.** Gana en todos los escenarios, con
  cualquier peso y en el 99 % de los remuestreos: misma calidad que Kimi, más
  constante y 2.7 veces más rápido.
- **Fase 4: Kimi, y lo decide la regla de elegibilidad.** Sin ella, Nemotron
  ganaría con la mitad de los pesos posibles por ser 4 veces más rápido. Pero
  Nemotron falló el contrato en 2 de 3 corridas (`list_items` sin ordenar) y
  Kimi pasó las 34 pruebas ocultas las 3 veces. Un código que no pasa sus
  pruebas no puede avanzar a Testing, así que la regla es la que corresponde.
- **Fase 1: Nemotron, pero es la elección menos firme** (76 % de los pesos,
  71 % de los remuestreos). Kimi gana si se da prioridad casi total a la
  calidad (60/30). La diferencia real entre ambos es de estilo de falla:
  Nemotron es más de 2 veces más rápido y mejor evaluado por el juez, pero inventó un
  valor ("95 %") en 1 de 3 corridas; Kimi nunca inventó. Ese tipo de falla es
  justo el que la plataforma ya detecta (`valores_sin_respaldo` del Mejorador y
  el Evaluador, más la aprobación humana), así que el riesgo de Nemotron es
  controlable. La decisión y sus condiciones están en `SELECCION.md`.
- **El modelo local no es elegible en las fases 1 y 4** con ningún peso: no
  cumplió la tarea en ninguna corrida. En la fase 3 es elegible (2/3), pero
  no gana con ningún perfil de pesos (solo en el 1 % de los remuestreos); además la revisión manual del punto 6 mostró que ese 2/3 está
  sobreestimado (con el criterio de los jueces sería 1/3).
