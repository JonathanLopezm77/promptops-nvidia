# Diseño del benchmark (Parcial 1, Componente 4)

3 modelos × 3 fases × 3 ejecuciones = **27 ejecuciones auditables**.
Todo lo que aquí se fija se definió **antes** de ejecutar el benchmark.

## 1. Qué se mantiene constante (sección 7 del enunciado)

| Elemento | Cómo se fija |
|---|---|
| Prompt | La versión **aprobada** de cada fase (`prompts/aprobados/1_, 3_, 4_*.txt`), sin cambios |
| Input y contexto | Un caso fijo por fase (`benchmarks/casos/fase*.json`), idéntico para los 3 modelos; mismo dominio en las 3 fases (lista de deseos con aviso de baja de precio) |
| Formato de salida | El que exige cada prompt aprobado |
| Parámetros | `temperature 0.2`, `top_p 0.95`, `max_tokens 8192`, sin `seed` (`benchmarks/modelos.json`) |
| Quality Gate | Las reglas de la sección 3, iguales para los 3 modelos |

Los prompts aprobados tienen los problemas documentados en
`evidence/punto4_prompts/REVISION_MANUAL.md` (p. ej. Requisitos numera
RF/RNF y Arquitectura pide afirmar el uso de un linter). **No se corrigen**:
el enunciado exige usar la versión aprobada, y afectan por igual a los 3
modelos. Sus efectos se miden (ver "afirma verificaciones no realizadas").

## 2. Modelos

| Clave | Tipo exigido | Modelo |
|---|---|---|
| local | Local / open-weight on-premise | `qwen2.5-coder:7b` (Ollama, `num_ctx 16384`) |
| cloud_generalista | Cloud generalista | `moonshotai/kimi-k3` |
| cloud_razonamiento | Cloud razonamiento / código | `nvidia/nemotron-3-super-120b-a12b` (razonamiento activado) |

Ejecución: las 27 corridas en orden aleatorio con semilla fija (para no
favorecer a ningún modelo por el momento del día), el modelo local calentado
antes de medir, y la PC sin otros programas que usen la GPU.

## 3. Quality Gate de cada fase (puntaje 0-100)

### Fase 1 — Requisitos (enunciado: Quality Score + verificabilidad + trazabilidad)

| Componente | Peso | Cómo se mide |
|---|---|---|
| Quality Score | 50 | Requirements Quality Score (10 criterios ISO/IEC/IEEE 29148) de la lista generada, calculado por el Evaluador de la plataforma con el **juez** (sección 4) |
| Verificabilidad | 20 | Proporción de requisitos RF/RNF seguidos de una línea `Criterio de aceptación:` |
| Trazabilidad | 15 | Proporción de identificadores bien formados, únicos y secuenciales por tipo (RF-01…, RNF-01…) |
| No inventar | 15 | 15 − 5 por cada valor numérico no sustentado por la entrada (mínimo 0) |

- **Schema compliance:** las 4 secciones del formato obligatorio, en orden, y al menos un RF.
- **Constraint violations:** verbos prohibidos por el prompt (gestionar, procesar, manejar, administrar, ofrecer soporte) o términos vagos (rápido, fácil, adecuado, demasiado) dentro de un RF/RNF.
- **Supuestos no sustentados:** números que no aparecen en la entrada (solo `20000`), con el detector de la plataforma.
- **Huecos detectados (informativo):** cuántos de los 4 huecos plantados se preguntan en lugar de inventarse (plazo del aviso, tamaño de la lista, umbral de baja, invitados).
- **Cumple la tarea:** schema correcto, ≥1 RF, verificabilidad ≥ 80 %, ningún valor inventado y ≥ 2 huecos preguntados.

### Fase 3 — Arquitectura (enunciado: restricciones + trazabilidad + revisión)

| Componente | Peso | Cómo se mide |
|---|---|---|
| Cobertura de SPEC | 25 | Proporción de SPEC-01…SPEC-06 que aparecen en la salida (el juez además indica, como dato informativo, si cada SPEC está cubierto de forma concreta) |
| Estructura | 15 | Proporción de las 9 secciones obligatorias presentes |
| Identificadores | 10 | ARCH-01… secuenciales sin huecos (5) y todos presentes en el diagrama Mermaid (5) |
| Restricciones | 20 | 20 − 7 por cada restricción R1-R6 que el **juez** marca como violada (mínimo 0) |
| Revisión | 30 | Puntaje de revisión 1-10 del **juez** con una rúbrica fija (× 3) |

- **Schema compliance:** 9 secciones, un bloque Mermaid y ningún bloque de código de implementación.
- **Constraint violations:** restricciones violadas según el juez, o código de implementación incluido.
- **Supuestos no sustentados:** funcionalidades o datos inventados según el juez (p. ej. SMS, push, pagos), y **afirmar verificaciones no realizadas** (marcar como hecho el uso de un linter o un script).
- **Cumple la tarea:** 6/6 SPEC cubiertos, schema correcto y ninguna restricción violada.

### Fase 4 — Implementación (enunciado: compilación + lint + tests)

| Componente | Peso | Cómo se mide |
|---|---|---|
| Compilación | puerta | Se extrae `wishlist_service.py` de la salida y se compila (`py_compile`); si no compila, el puntaje es 0 |
| Tests | 70 | Proporción de las **34 pruebas ocultas** que pasan (× 70) |
| Lint | 15 | `ruff check --isolated` con la configuración por defecto de ruff 0.16.9 (`--isolated` hace que el resultado no dependa de archivos de configuración de la máquina): 15 − 1.5 por aviso (mínimo 0). Esa configuración por defecto es amplia: incluye, entre otras, las familias `UP` (modernización: `list` en vez de `typing.List`) e `I` (orden de imports). La implementación de referencia la pasa sin avisos |
| Formato y trazabilidad | 15 | Encabezado `# File: wishlist_service.py` (5), comentario `Implements:` con ARCH y SPEC (5), un único archivo de implementación (5) |

- **Pruebas ocultas:** los modelos no las ven. Pasan al 100 % contra la implementación de referencia y detectan los 12 errores sutiles introducidos a propósito (`evidence/punto6_benchmark/experimentos/mutantes_*`).
- **Schema compliance:** bloques con encabezado `# File:` y el módulo pedido presente.
- **Constraint violations:** imports fuera de la biblioteca estándar o de acceso a red/disco/procesos, o pruebas incluidas cuando el diseño dice que no se requieren.
- **Supuestos no sustentados (informativo):** nombres públicos que no están en el contrato y comentarios `ASSUMPTION`.
- **Cumple la tarea:** compila y pasa las 34 pruebas.
- **Seguridad:** el código generado solo se ejecuta si no importa módulos de red, disco o procesos; corre en una carpeta temporal, con límite de tiempo.

## 4. Juez de calidad (fases 1 y 3)

Dos jueces califican cada salida:

- **Principal: `openai/gpt-oss-20b`** — no compite en el benchmark (neutral).
- **Secundario: `nvidia/nemotron-3-super-120b-a12b`** — es el Evaluador de la plataforma, pero **compite**: sus notas sobre sus propias salidas son autoevaluación.

gpt-oss-20b se usa con `reasoning_effort: "low"`: con su valor por defecto
agotó el límite de ~300 s del servidor de NVIDIA (HTTP 504) al juzgar una
salida del ensayo, y con "low" respondió 2 de 2 veces en 170-178 s
(`experimentos/juez_esfuerzo_razonamiento*`). Cada juicio tiene hasta 3
intentos ante errores transitorios.

Se usa la nota del juez principal; si falla, la del secundario, marcada.
Reportar ambas permite medir si el modelo que compite se favorece a sí mismo.
Prueba previa (`experimentos/juez_neutral*`): ambos distinguen una lista buena
(79-88) de una mala (33-43); gpt-oss-20b tardó 150-545 s y agotó el tiempo en
1 de 4 llamadas, nemotron 13-25 s.

## 5. Métricas que se reportan (sección 7 del enunciado)

| Métrica | Definición en este benchmark |
|---|---|
| Task Success Rate | % de ejecuciones que "cumplen la tarea" según la fase (sección 3) |
| Quality Gate Score | Puntaje 0-100 de la fase |
| Constraint Violation Rate | % de ejecuciones con al menos una violación |
| Unsupported Assumption / Hallucination Rate | % de ejecuciones con al menos un supuesto no sustentado |
| Schema Compliance | % de ejecuciones con el formato de salida correcto |
| Consistency Across Runs | Desviación estándar del Quality Gate Score entre las 3 corridas |
| TTFT / Latencia total | Primer token, primer token de respuesta y total (streaming) |
| Tokens y costo | Tokens de entrada/salida (y de razonamiento cuando el servicio los informa). Costo: 0 en la capa gratuita de NVIDIA y en el modelo local (sin precio publicado; no se inventa uno) |
| Recursos locales | RAM/CPU del proceso de Ollama, VRAM del modelo y uso de GPU |
| Confiabilidad del servicio (adicional) | Intentos por ejecución y fallos (vacía, degenerada, cortada) |

## 6. Lo que NO mide este benchmark

- Una sola entrada por fase: los resultados valen para esta tarea, no para
  cualquier requisito, arquitectura o código.
- 3 corridas por combinación: suficiente para ver variabilidad, no para
  afirmar diferencias estadísticamente significativas.
- La calidad de las fases 1 y 3 depende en parte de un juez de IA; se
  reportan dos jueces y sus diferencias.
