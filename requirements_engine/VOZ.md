# Subsistema de voz (STT / TTS) — Componente 1, §4.5

El enunciado pide que la voz se implemente y documente **separadamente** y
que se declare si cada componente opera localmente o depende de un servicio
remoto. La voz vive en un solo módulo, `frontend/voz.js`, separado de la
lógica del análisis.

## 1. Stack elegido (opción A)

| Función | Tecnología | Modalidad | Por qué |
|---|---|---|---|
| STT | **Web Speech API** (`SpeechRecognition`) | **Remota**: Chrome envía el audio a servidores de Google; Edge, a los de Microsoft | Funciona en el navegador sin instalar nada ni consumir la RAM/GPU del portátil (la GPU de 6 GB la usa el modelo local del benchmark). El enunciado la permite "para prototipado" |
| TTS | **`window.speechSynthesis`** | **Local o remota según la voz**: las voces "Microsoft …" de Windows son locales (`localService = true`); las "Google …" de Chrome son remotas | Integrada en la interfaz web, sin dependencias |

Idioma: `es-CO`. Para el TTS se prefiere una voz en español **local**
(`localService`), y si no hay, cualquier voz en español.

## 2. Lo que exige el enunciado para esta opción

| Aspecto | Situación |
|---|---|
| **Compatibilidad** | STT: Chrome y Edge (escritorio). Firefox no implementa `SpeechRecognition`: la pantalla lo detecta y muestra "Este navegador no soporta dictado por voz. Usa Chrome o Edge". TTS: todos los navegadores modernos |
| **Conectividad** | El STT necesita internet (el error `network` se explica al usuario). El TTS con voces locales funciona sin conexión |
| **Privacidad** | El audio del dictado **sale del equipo** hacia Google o Microsoft. No usar para requisitos con datos sensibles; para ese caso está la opción B local (§5) |
| **Procesamiento remoto** | Declarado en cada análisis: `stt_metadata.processing = "remote"` y el proveedor según el navegador |
| **Navegador, voz y dependencia del sistema (TTS)** | Cada lectura registra el motor, el nombre de la voz, el idioma y si fue local o remota (`tts_log`). Las voces disponibles dependen del sistema operativo y del navegador |

## 3. Qué se registra (auditoría)

En cada análisis por voz, `stt_metadata` (columna JSONB de
`requirement_analyses`, obligatoria cuando `input_mode = "voice"`):

| Campo | Contenido |
|---|---|
| `engine`, `provider`, `processing` | "Web Speech API (SpeechRecognition)", Google o Microsoft según el navegador, "remote" |
| `language`, `browser` | "es-CO", navegador y versión |
| `recording_ms` | Duración del dictado |
| `transcription_ms` | Tiempo desde que se deja de hablar hasta el texto final (tiempo de transcripción que pide el enunciado) |
| `confidence` | Confianza media que informa el reconocedor (si la da) |
| `recorded_at` | Fecha y hora |

Cada lectura en voz alta se agrega a `tts_log` (`POST /api/requirements/{id}/tts`):
motor, voz, idioma, local/remota y fecha.

## 4. Caso D (requisito por voz)

- Probado por el usuario con micrófono real en la app desplegada en Render
  (dictado, validación, mejora y lectura en voz alta). Análisis
  `c3ba46b4-f217-4ca4-bc01-5fbd04618cf1`.
- **Pendiente:** exportar esa evidencia al repositorio. Requiere la URL de la
  app en Render (no quedó registrada):

  ```bash
  python scripts/casos_requisitos.py --base-url https://<app>.onrender.com voz --id c3ba46b4-f217-4ca4-bc01-5fbd04618cf1
  ```

  El comando guarda el análisis completo (transcripción, `stt_metadata`,
  evaluaciones, mejora y `tts_log`) en `evidence/punto3_casos/corridas/D_1.json`;
  después `python scripts/casos_requisitos.py informe` verifica el caso D y
  actualiza `RESULTADOS.md`.

## 5. Opción B (pendiente, opcional)

STT local con **faster-whisper** (modelo `base` o `small`, INT8 en CPU), la
opción preferida del enunciado, para dictar sin que el audio salga del equipo.
No está implementada: la opción A cumple el flujo y el enunciado la acepta
declarando que es remota, como se hace aquí.
