# Punto 5 — Proveedores de modelos y medición (preparación del benchmark)

Objetivo: dejar lista la infraestructura que exige la sección 7 del
enunciado antes de ejecutar las 27 corridas: un modelo local servido por
Ollama y dos modelos cloud (NVIDIA), invocados con los **mismos parámetros**,
midiendo **TTFT, latencia total, tokens y recursos locales**, y registrando
**modelo, versión, parámetros y fecha** de cada ejecución.

## Qué se construyó

| Archivo | Contenido |
|---|---|
| `benchmarks/proveedores.py` | `generar()` para Ollama (API nativa) y NVIDIA (streaming SSE); TTFT al primer token y al primer token de respuesta; tokens de entrada/salida/razonamiento; `MonitorRecursos` (RAM/CPU del proceso de Ollama, VRAM y uso de GPU, VRAM exacta del modelo); `generar_con_reintentos()`; detección de respuestas vacías y degeneradas; `version_modelo()` |
| `benchmarks/modelos.json` | Los 3 modelos, los parámetros comunes, la política de reintentos y la justificación de cada decisión |
| `scripts/probar_proveedores.py` | Prueba de los 3 modelos con una tarea corta de la fase 1; guarda todo en `prueba_<fecha>.json` |
| `tests/test_benchmark_proveedores.py` | 28 tests con respuestas simuladas en el formato real de cada servicio |

## Configuración

| Clave | Tipo (enunciado) | Modelo | Proveedor |
|---|---|---|---|
| `local` | Local / open-weight on-premise | `qwen2.5-coder:7b` (digest `dae161e27b0e…`, Q4_K_M, 7.6B) | Ollama 0.34.4 en la RTX 3050 6 GB |
| `cloud_generalista` | Cloud generalista | `moonshotai/kimi-k3` | NVIDIA |
| `cloud_razonamiento` | Cloud de razonamiento / código | `nvidia/nemotron-3-super-120b-a12b` (razonamiento activado) | NVIDIA |

Parámetros comunes: `temperature 0.2`, `top_p 0.95`, `max_tokens 8192`, sin
`seed`. Local: `num_ctx 16384`, `keep_alive 60m`.

## Hallazgos que justificaron cada decisión

Todos con su script y su salida en `experimentos/`.

1. **Ollama usa 4096 tokens de contexto por defecto** (el modelo admite
   32768) y los prompts aprobados miden 500-900 palabras más la entrada:
   se recortarían sin aviso. Se usa la API nativa, la única que acepta
   `num_ctx`, con 16384.
2. **La primera llamada al modelo local tardó 20 s en cargarlo** en la GPU
   (`load_duration`). Se registra aparte y se calienta el modelo antes de
   medir, para no sumarlo al TTFT.
3. **kimi-k3 en streaming devuelve respuestas vacías** (matriz: 2 correctas
   de 9 en streaming frente a 5 de 6 sin streaming; con `seed`, 0 de 3). El
   TTFT exige streaming, así que no se envía `seed` y se aplica una política
   de reintentos registrados (hasta 3, solo por fallos del servicio, igual
   para los 3 modelos).
4. **Alternativas a kimi-k3 como generalista** (caso real de la fase 1, 3
   llamadas cada una): `openai/gpt-oss-20b` respondió 3 de 3 pero en 68 a
   335 s; `nvidia/nemotron-3.5-lightning` llegó al límite de 4096 tokens en
   las 3 (respuesta probablemente truncada), tardó 180-367 s y en una la
   respuesta tuvo solo 6 caracteres. Ese experimento no guardó el texto ni
   el finish_reason, así que no se evaluó la calidad de esas respuestas. Se
   mantuvo kimi-k3 (~56 s).
5. **Respuesta degenerada contada como correcta:** en la primera prueba,
   kimi-k3 devolvió `!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!` como respuesta (no
   como razonamiento) y el código la contó como OK porque solo comprobaba
   que no estuviera vacía. Se agregó la detección de salidas degeneradas;
   esa prueba se conserva en `experimentos/prueba_1_degenerada_contada_como_ok.json`.
6. **El razonamiento de nemotron-3-super** se desactiva con
   `chat_template_kwargs: {"thinking": false}` (verificado), pero en el
   benchmark se deja activado porque define su categoría. NVIDIA **no
   informa sus tokens de razonamiento** (kimi-k3 sí): se registran los
   caracteres de razonamiento, sin estimar tokens.
7. **El catálogo de NVIDIA devuelve la misma fecha (1993-04-26) como
   `created` para todos los modelos**: no sirve como versión. Los modelos
   cloud se identifican por su id y la fecha de ejecución.
8. **Windows no informa la VRAM por proceso** (`nvidia-smi` muestra N/A).
   Se usa `/api/ps` de Ollama, que da la VRAM exacta del modelo, y además la
   VRAM total de la GPU (que incluye otros programas).

## Prueba final (`prueba_20260927_141734.json`, 3 ejecuciones por modelo)

| Modelo | Correctas | Llamadas | Latencia total | Primer token de respuesta | Tokens de salida |
|---|---|---|---|---|---|
| local | 3/3 | 3 | 6.0-8.2 s | 0.1 s (modelo ya cargado) | 97-110 |
| cloud_generalista | 3/3 | 3 | 34.7-44.3 s | 28.0-36.7 s | 202-222 |
| cloud_razonamiento | 3/3 | 4 (un reintento por respuesta cortada) | 4.1-7.3 s | 1.3-6.7 s | 240-409 |

Recursos del modelo local con `num_ctx 16384`: 5.5 GB en total, **4.05 GB en
la GPU (73 %)** y el resto en CPU; proceso `llama-server` con ~2.0 GB de RAM y
CPU media de 450-520 % (≈ 4-5 núcleos de 12); uso de GPU máximo 43-58 %.

## Condiciones que el benchmark debe cuidar (punto 6)

- **Cerrar programas que usen la GPU y la RAM** (durante estas pruebas
  estaban abiertos un juego y LM Studio; en una consulta previa la GPU tenía
  5.6 GB de 6 ocupados con el modelo sin cargar, en otra 1.4 GB, y quedaban
  solo 3.6-5.3 GB de RAM libres). Con otros programas
  compitiendo, los tiempos y recursos locales no son reproducibles.
- Calentar el modelo local antes de medir y registrar si ya estaba cargado.
- La tarea de esta prueba es corta: las del benchmark (prompts aprobados de
  500-900 palabras más la entrada) serán bastante más lentas, sobre todo en
  el modelo local, que tendrá parte en CPU.
