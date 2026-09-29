# Punto 3 — Revisión manual de la ejecución final

Complementa a `RESULTADOS.md`, que se genera automáticamente. Las
verificaciones automáticas no pueden detectar todo, en particular los
**datos inventados que no son números** (actores, formatos, canales,
comportamientos nuevos). Esta revisión lee cada salida completa de
`corridas/` y anota lo que el script no ve.

Revisión asistida por IA (Claude) sobre los JSON de esta carpeta; el equipo
debe validarla antes de la entrega.

## Nota sobre el manifiesto

`manifiesto.json` marca `"cambios_sin_commit": true`. El código ejecutado
es exactamente el del commit `a7a1ded`: el único archivo sin commit en ese
momento era la carpeta `evidence/punto3_casos_exploratorio/` (no
rastreada), que no se ejecuta. El script contaba también los archivos no
rastreados; se corrigió después para contar solo cambios en archivos
versionados. El manifiesto no se editó a mano.

## Caso A — Requisito claro (3/3 cumplen)

- Las 3 corridas reconocen alta calidad (92, 100 y 100) y **no modifican**
  el requisito; ninguna hace preguntas ni marca términos ambiguos.
- Observación: dos corridas dan 10 en los 10 criterios. El requisito se
  escribió para ser de alta calidad, pero un 100/100 sugiere un posible
  **efecto techo** del Evaluador con requisitos bien redactados. La
  corrida 1 (92) señaló detalles razonables (trazabilidad 8).

## Caso B — Requisito ambiguo (3/3 cumplen)

**Detección:** las 3 corridas marcan como ambiguos "rápida/o" y
"sencilla/o"; la corrida 1 no listó "relevantes" entre los términos
ambiguos, aunque sí lo trató (REQ-4 y su pregunta de aclaración).

**Mejora sin datos del stakeholder** (puntaje 52 → 67 en promedio):

- Ninguna corrida inventa valores numéricos ni actores: cada dato faltante
  queda como `[POR DEFINIR: ...]`.
- Algunos marcadores incluyen **sugerencias** ("p. ej. 2 segundos",
  "p. ej. nombre, categoría, marca", "popularidad, disponibilidad"). No son
  requisitos, pero pueden sesgar al stakeholder; conviene tenerlo en
  cuenta al presentarlos.
- La corrida 1 interpreta "sencilla" como un número máximo de
  interacciones, que es una interpretación razonable dejada como
  `[POR DEFINIR]`, no un dato inventado.

**Tras responder las preguntas** (puntaje final 79, 90 y 86):

- Las 3 versiones usan fielmente los datos del stakeholder: un cuadro de
  texto en la parte superior, búsqueda por nombre/marca/categoría, sin
  iniciar sesión ni filtros, clientes registrados e invitados, 2 segundos
  con 20000 productos y el orden de resultados.
- La corrida 1 introdujo al principio algún valor sin respaldo; el
  detector pidió la corrección (`unsupported_retry: true`) y la versión
  final no tiene valores sin respaldo.
- **Hallazgo sobre nuestra propia entrada:** la respuesta del stakeholder
  era ambigua ("primero las coincidencias en el nombre y luego las demás,
  ordenadas por unidades vendidas": ¿el orden por ventas aplica a todas o
  solo al resto?, ¿de mayor a menor?). Las corridas la interpretaron
  distinto, y en la corrida 1 la reevaluación lo preguntó explícitamente.
  El sistema detectó una ambigüedad que no era del requisito sino de la
  aclaración.
- La corrida 1 usó `[POR DEFINIR: identificador único ...]` en lugar de
  REQ-n; las corridas 2 y 3 numeraron REQ-1 a REQ-4.

## Caso C — Contradictorio o incompleto (3/3 cumplen)

- Las 3 corridas **detectan la contradicción** (consistencia 2/10, con el
  hallazgo "automático cada día" frente a "solo cuando el gerente lo
  solicite") y la **dejan pendiente** en REQ-1 sin elegir un lado.
- Ninguna inventa valores numéricos; "los datos necesarios" queda siempre
  como `[POR DEFINIR]`. El único dato concreto agregado ("desde la web")
  viene del contexto del proyecto.
- **Desviaciones menores respecto a la regla "no agregues requisitos":**
  - Corridas 1 y 2 agregan una dimensión de **formato** del reporte, y la
    corrida 2 un comportamiento de **almacenamiento** ("almacenar el
    reporte en [POR DEFINIR: ubicación]"). No inventan valores (quedan por
    definir), pero sí introducen aspectos que el original no pedía.
  - Corrida 1 agrega **zona horaria** y un REQ condicional para cada
    alternativa de la contradicción; es razonable, pero anticipa diseño.
  - Corrida 2 escribe "el reporte de ventas **diario**" antes del marcador
    de la contradicción, lo que inclina levemente hacia una de las dos
    opciones.
- El delta varía bastante entre corridas (+17, +9, +26): la magnitud de la
  mejora depende de cuántos aspectos nuevos quedan por definir.

## Observaciones generales

- **Consistencia entre corridas:** el puntaje del requisito original es muy
  estable (A 97 ± 5, B 52 ± 1, C 31 ± 2); el del mejorado varía más
  (B ± 6, C ± 10), porque cada corrida produce una redacción distinta.
- **Independencia:** evalúa `nemotron-3-super-120b` y mejora `kimi-k3`, de
  familias distintas; ningún modelo califica su propio texto.
- **Modelo de respaldo:** no se usó en ninguno de los 9 análisis que
  requirieron mejora (3 de B, 3 de C y 3 aclaraciones): kimi-k3 produjo
  una respuesta usable en todos. Los reintentos internos del cliente ante
  respuestas vacías no se registran, así que no se sabe si alguno hizo
  falta.
- **Latencia:** A ≈ 18 s (una sola evaluación); B ≈ 170 s y C ≈ 129 s
  (evaluación + mejora + reevaluación), más ≈ 1.5-4 min por aclaración.

## Caso D — Requisito por voz (1/1 cumple)

Dictado por el usuario con micrófono real en la app desplegada en Render
(`https://promptops-nvidia.onrender.com`) el 2026-09-27; exportado con
`python scripts/casos_requisitos.py --base-url https://promptops-nvidia.onrender.com voz --id c3ba46b4-f217-4ca4-bc01-5fbd04618cf1`.

- **Transcribe:** "Oye necesito que me des un login", con la Web Speech API
  de Chrome (servicio **remoto** de Google, declarado en `stt_metadata`),
  confianza 0.915, 3.4 s de dictado y 103 ms de transcripción. El usuario no
  corrigió la transcripción.
- **Valida:** 17/100, el puntaje más bajo de todos los casos, coherente con
  un pedido de cinco palabras sin actor, condición ni criterio de éxito.
  Hace 3 preguntas de aclaración pertinentes (flujo, usuarios, qué pasa tras
  el acceso o ante un error).
- **Mejora sin inventar:** 60/100 (+43). Usa el contexto que dio el usuario
  ("login simple de una página de ropa") y marca con `[POR DEFINIR]` lo que
  no se sabe (tipo de credenciales, destino tras el acceso, límite de
  intentos) en vez de rellenarlo. No llega a alta calidad, que es lo esperado
  sin las respuestas del usuario.
- **Retroalimentación hablada:** leída con la voz "Microsoft Helena - Spanish
  (Spain)", **local** del sistema, registrada en `tts_log`.

**Diferencia con A, B y C:** en Render el evaluador era
`nvidia/nemotron-3.5-lightning-30b-a3b` (configuración de la app desplegada),
no `nemotron-3-super` como en las corridas locales. El caso D demuestra el
flujo de voz; sus puntajes no son comparables con los de A-C. El informe
(`RESULTADOS.md`) lista ambos evaluadores.
