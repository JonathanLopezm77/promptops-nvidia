# Selección de modelo por fase del SDLC

Principio del enunciado (§7.1): no hay un "mejor modelo" universal; para cada
fase se elige el más conveniente bajo una función objetivo explícita de
calidad, cumplimiento, latencia, costo y recursos.

- **Fases 1, 3 y 4** (benchmark de 27 ejecuciones): la elección sale de la
  función objetivo y su análisis de sensibilidad (`FUNCION_OBJETIVO.md`).
- **Fases 2, 5, 6 y 7**: selección argumentada con documentación técnica de
  los modelos, costo y recursos, hallazgos transferibles del benchmark y un
  sondeo de 1 corrida por modelo (`SONDEO.md`).

## 1. Resumen

| Fase | Modelo elegido | Condiciones de uso | Alternativa |
|---|---|---|---|
| 1 Requisitos | **Nemotron 3 Super** (razonamiento activado) | Con el detector de valores sin respaldo y la aprobación humana de la plataforma | Kimi K3 si se prioriza la calidad por encima de todo |
| 2 Especificación | **Kimi K3** | Validar el JSON contra la estructura pedida | Nemotron solo con `max_tokens` ≥ 16384 y reintento si la salida no valida |
| 3 Arquitectura | **Nemotron 3 Super** | Corregir el prompt aprobado (pide afirmar verificaciones no hechas) | Kimi K3 (misma calidad, 2.7 veces más lento) |
| 4 Implementación | **Kimi K3** | Compilación + lint + pruebas como Quality Gate obligatorio | Ninguna elegible en el benchmark |
| 5 Testing / QA | **Kimi K3** | Ejecución asíncrona (tarda ~8 min) | Nemotron para iteraciones rápidas (detecta 8/12 mutantes) |
| 6 Deployment | **Kimi K3** | Revisión humana y `docker build` real en CI antes de desplegar | Ninguna sin revisión: Nemotron entregó un contenedor que no arranca |
| 7 Mantenimiento | **Nemotron 3 Super** | Suite de regresión como Quality Gate | Local (qwen2.5-coder:7b) para correcciones pequeñas cuando el código no puede salir de la organización |

El resultado es un **enrutamiento por fase**, no un modelo único:

- **Kimi K3** en las fases cuyo entregable se verifica ejecutándolo contra un
  contrato preciso (especificación JSON, código, pruebas, despliegue): fue el
  único que no falló ninguno de esos contratos.
- **Nemotron 3 Super** en las fases de análisis y diseño revisadas por una
  persona (requisitos, arquitectura) y en cambios acotados (mantenimiento):
  misma calidad o casi, 2.4-4.3 veces más rápido y 14-39 veces más barato por
  ejecución con precios públicos.
- **El modelo local** no es la primera opción en ninguna fase: falló la tarea
  en requisitos e implementación (0/3), inventa valores y afirma resultados
  que no verificó. Su lugar es la corrección puntual de código on-premise.

Configuración lista para usar en el punto 8: `benchmarks/seleccion_por_fase.json`.

## 2. Características de los modelos (documentación oficial)

| | qwen2.5-coder:7b (local) | Kimi K3 | Nemotron 3 Super 120B-A12B |
|---|---|---|---|
| Tipo | Local / open-weight | Cloud generalista (pesos abiertos) | Cloud de razonamiento y agentes (pesos abiertos) |
| Parámetros | 7.61 B (Q4_K_M en Ollama) | MoE: 2.8 T totales, 104 B activos | Híbrido Mamba-2 + MoE + atención (LatentMoE): 120 B totales, 12 B activos |
| Contexto | 32 768 por defecto (128 K con YaRN); aquí `num_ctx 16384` | 1 048 576 | Hasta 1 M (262 144 en OpenRouter) |
| Razonamiento | No | **Siempre activo** (esfuerzo low / high / max) | Activable (`enable_thinking`) |
| Licencia | Apache 2.0 | Kimi K3 License | NVIDIA Nemotron Open Model License |
| Precio público (USD por millón de tokens de entrada / salida) | 0 (hardware propio) | 3.00 / 15.00 | 0.08 / 0.45 |
| Uso previsto por el fabricante | Generación, razonamiento y corrección de código | Agentes, código, contexto largo | Flujos agénticos, contexto largo, cargas de alto volumen |

Fuentes: fichas de Hugging Face de
[Qwen2.5-Coder-7B-Instruct](https://huggingface.co/Qwen/Qwen2.5-Coder-7B-Instruct),
[Kimi-K3](https://huggingface.co/moonshotai/Kimi-K3) y
[NVIDIA-Nemotron-3-Super-120B-A12B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Super-120B-A12B-BF16);
precios de la API pública de OpenRouter consultada el 2026-09-27
(`precios_publicos.json`). En el benchmark los modelos cloud se usaron en la
capa gratuita de NVIDIA (costo real 0 USD).

Dos características explican buena parte de los resultados:

- **Kimi siempre razona** y fue el más lento en total en las 7 fases (64-480 s
  por ejecución), aun en la corrección de una línea (90 s); su razonamiento
  obligatorio es la explicación más probable.
- **El razonamiento de Nemotron consume `max_tokens`**: 2676-6347 tokens de
  salida en el benchmark, y en la especificación agotó los 8192.

## 3. Hallazgos del benchmark que se transfieren a otras fases

| Hallazgo (punto 6) | Evidencia | Se transfiere a |
|---|---|---|
| Kimi cumple contratos precisos sin fallar: 34/34 pruebas en las 3 corridas, 0 avisos de lint | F4: 100 / 100 / 100 | Fases 2, 5 y 6: su entregable también se valida contra un contrato |
| Nemotron comete errores sutiles de contrato con supuestos no verificados (`list_items` "ya está ordenada") | F4: falla en 2 de 3 corridas | Fase 5 (una suite con esos huecos deja pasar defectos) y fase 6 |
| Nemotron iguala a Kimi en análisis y diseño, más rápido y constante | F3: 92 vs 93, DE 1.7 vs 3.5, 70 s vs 188 s | Fase 7 (diagnóstico y cambio acotado) |
| El modelo local inventa valores y afirma verificaciones o resultados sin hacerlos | F1: inventa en 3/3; F3: "R1 cumplida" con microservicios | Fases 2 y 5: en el sondeo omitió todas las inconsistencias y declaró "sin defectos" con un defecto que su propia prueba detecta |
| Los modelos cloud afirman haber usado herramientas que no tienen (linter de Mermaid) | F3: 6/6 salidas cloud | Fase 6 (el prompt pide validar con hadolint/yamllint): toda afirmación de validación debe comprobarse |
| El costo de Kimi por ejecución es 14-24 veces el de Nemotron | Precios públicos, §4 de `FUNCION_OBJETIVO.md` | Todas: se elige Kimi solo donde su ventaja de calidad es clara |

## 4. Justificación por fase

La conclusión de cada fase sigue la forma que pide el enunciado.

### Fase 1 — Requisitos → Nemotron 3 Super

Utilidad con los pesos base: Nemotron 0.866, Kimi 0.831; el local no es
elegible (0/3). Nemotron gana en 7 de los 8 escenarios de la sensibilidad, en el 76 % de los
pesos aleatorios y en el 71 % de los remuestreos; con precio público su
ventaja crece (0.866 vs 0.738). Kimi gana solo si la calidad pesa 60 % o más.
Nemotron inventó un valor en 1 de 3 corridas: es exactamente la falla que la
plataforma ya detecta (`valores_sin_respaldo` en el Evaluador y el Mejorador)
y que la aprobación humana filtra, por eso la condición de uso.

> Para requisitos a partir de una necesidad de stakeholder, con el prompt
> aprobado y el Quality Gate de la fase (Quality Score, verificabilidad,
> trazabilidad, no inventar), **Nemotron 3 Super mostró el mejor equilibrio**:
> Quality Gate 88.8 (el más alto), 30 s por ejecución (2.4 veces más rápido
> que Kimi con reintentos) y 0.0016 USD con precio público, a cambio de un
> valor inventado en 1 de 3 corridas que la plataforma detecta.

### Fase 2 — Especificación → Kimi K3

Kimi fue el único que cumplió los 9 chequeos del Quality Gate: numeración con
huecos, dependencia, referencia rota, contradicción y alerta legal. El local
no detectó ninguna inconsistencia ni alerta (66.7). Nemotron no entregó la
especificación con los parámetros del benchmark (agotó 8192 tokens
razonando); con 16384 la entregó 2 de 2 veces, pero cumplió en 1 (88.9 y 100).
El entregable de esta fase es el contrato del que dependen arquitectura, código
y pruebas (cadena REQ → SPEC → ARCH → CODE → TEST), y un error en él se
propaga a todas las siguientes. Por eso aquí se da más peso al cumplimiento
que a los 282 s de Kimi. Se transfiere además el hallazgo de F4: Kimi no falló
ningún contrato.

> Para convertir requisitos aprobados en una especificación JSON trazable,
> con el prompt aprobado y un Quality Gate de completitud, consistencia y
> schema, **Kimi K3 mostró el mejor equilibrio**: único con 9/9 chequeos, a
> costa de 282 s y 0.087 USD por ejecución; Nemotron requiere el doble de
> presupuesto de tokens y aun así no fue estable.

### Fase 3 — Arquitectura → Nemotron 3 Super

Gana en todos los escenarios de la sensibilidad (100 % de los pesos
aleatorios, 99 % de los remuestreos): misma calidad que Kimi (92.0 vs 93.0),
más constante (DE 1.7 vs 3.5), 2.7 veces más rápido y unas 23 veces más barato
por ejecución. Ambos marcan como hecha una verificación con linter que no
hicieron; es un problema del prompt aprobado (se corrige en el punto 8), no
del modelo.

> Para diseñar la arquitectura a partir de una especificación con 6 SPEC y 6
> restricciones técnicas, **Nemotron 3 Super mostró el mejor equilibrio**:
> Quality Gate 92.0 con la menor variabilidad, ninguna restricción violada,
> 70 s y 0.003 USD por ejecución.

### Fase 4 — Implementación → Kimi K3

Kimi pasó las 34 pruebas ocultas con 0 avisos de lint en las 3 corridas
(100 en las 3). Nemotron es 4 veces más rápido, pero falló el contrato en 2 de
3 corridas, así que no es elegible (un código que no pasa sus pruebas no puede
avanzar a Testing). Sin esa regla, la elección dependería de los pesos (55 % /
45 %); con ella es Kimi en el 100 % de los pesos y el 96 % de los remuestreos.

> Para implementar un módulo Python a partir de un diseño con contratos
> exactos, con compilación, lint y 34 pruebas ocultas como Quality Gate,
> **Kimi K3 mostró el mejor equilibrio**: el único que cumplió la tarea en las
> 3 corridas, a cambio de 82 s y 0.032 USD por ejecución.

### Fase 5 — Testing / QA → Kimi K3

En el sondeo, la suite de Kimi detectó los 12 mutantes, los 2 defectos
plantados, con cobertura 100 % y sin falsos positivos; la de Nemotron, 8 de 12
mutantes (sin probar el redondeo HALF_UP ni el orden de validaciones, justo
el tipo de detalle de contrato que Nemotron también omitió al implementar en
F4). El local declaró "sin defectos" con un defecto presente. El valor de una
suite es cuántos errores detecta, y la diferencia (100 % vs 67 % de mutantes)
pesa más que la latencia: 480 s es mucho para una sesión interactiva, pero la
generación de pruebas puede correr en segundo plano, como los análisis de la
plataforma.

> Para generar casos y una suite automatizada a partir de requisitos y
> código, con pass rate, cobertura y detección de defectos como Quality Gate,
> **Kimi K3 mostró el mejor equilibrio**: 100 % de mutantes detectados y los
> dos defectos plantados reportados, a costa de 480 s y 0.13 USD; Nemotron es
> la opción para iteraciones rápidas (63 s, 8/12 mutantes).

### Fase 6 — Deployment → Kimi K3

El puntaje automático empató a Kimi y Nemotron (11/11 chequeos), pero la
revisión manual los separó: el contenedor de Nemotron no arrancaría (no copia
el ejecutable `uvicorn`) y su `render.yaml` usa una clave que Render no
admite (`fromSecret`); el de Kimi es válido, respeta "validar en CI antes de
desplegar" (`autoDeploy: false` y deploy hook) y solo tiene defectos menores
(un `COPY *.sql` innecesario y un smoke test que no puede fallar). El local no
desplegaría. En esta fase un error llega a producción, así que la condición
de uso es no desplegar sin `docker build` real en CI y revisión humana.

> Para generar el pipeline, el contenedor y la configuración de despliegue de
> esta plataforma en Render, **Kimi K3 mostró el mejor equilibrio**: la única
> configuración desplegable tras la revisión manual, a costa de 217 s y 0.08
> USD por ejecución.

### Fase 7 — Mantenimiento → Nemotron 3 Super

Los tres modelos resolvieron la incidencia real (el defecto de Nemotron en F4)
con el cambio mínimo correcto: 34/34 pruebas de regresión, alcance limitado a
la función afectada y trazabilidad correcta. Con la calidad empatada, deciden
latencia y costo: Nemotron tardó 21 s (Kimi 90 s) y cuesta 0.0008 USD
(Kimi 0.031). El modelo local también lo resolvió (solo dejó un comentario
desactualizado): es una opción real para correcciones pequeñas de código que
no puede salir de la organización, siempre detrás de la suite de regresión.
Su fracaso en F4 (0/3) indica que no debe usarse para cambios amplios.

> Para diagnosticar y corregir una incidencia localizada con código, métricas
> y suite de regresión, **Nemotron 3 Super mostró el mejor equilibrio**:
> corrección mínima que pasa 34/34 pruebas, en 21 s y por 0.0008 USD.

## 5. Límites de estas conclusiones

- Fases 1, 3 y 4: 3 corridas por combinación y una entrada por fase
  (DISENO.md §6). Fases 2, 5, 6 y 7: 1 corrida, así que detectan diferencias
  grandes y modos de falla, pero no miden consistencia.
- Un solo dominio (lista de deseos). En otro dominio o con otro lenguaje
  puede cambiar el orden.
- La latencia de los modelos cloud depende de la carga del servicio gratuito
  de NVIDIA en el momento de la ejecución.
- Los pesos de la función objetivo son una decisión del equipo; la
  sensibilidad muestra que solo la fase 1 depende de ellos de forma relevante.
- Kimi se usó con su esfuerzo de razonamiento por defecto: bajarlo ("low")
  podría reducir su latencia en las fases 5 y 6, pero no se midió.
