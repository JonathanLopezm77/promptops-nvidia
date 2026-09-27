# Revisión manual del benchmark

Las calificaciones automáticas no se aceptaron sin mirar: se leyeron las
salidas y se contrastaron con los puntajes. Esto es lo que se encontró.

## 1. Las fallas de código son reales, no del calificador

- **Local** (`f4_local_*`, el mismo error en las 3 corridas): `round(…, 2, ROUND_HALF_UP)` lanza
  `TypeError: round() takes at most 2 arguments`, lo que hace fallar las
  5-6 pruebas de SPEC-04 que llegan a calcular una baja. `list_items` devuelve la lista interna
  (sin copia) y sin ordenar. Las 7-8 pruebas fallidas son consecuencia de eso.
- **Nemotron** (`f4_cloud_razonamiento_1` y `_3`): `list_items` devuelve
  `list(wishlist)` con el comentario "el orden de inserción coincide con el
  orden requerido". Es un supuesto falso: `now` es un parámetro y la prueba
  agrega productos con fechas desordenadas. El contrato dice "ordenada por
  added_at ascendente".
- Las pruebas ocultas pasan 34/34 con la implementación de referencia y
  detectan los 12 errores introducidos a propósito
  (`experimentos/mutantes_pruebas_ocultas_salida.txt`).

## 2. Afirmaciones de verificación no realizada (fase 3)

Las 6 salidas cloud cierran con un `[x]` que afirma haber verificado el
diagrama con un linter de Mermaid y la trazabilidad con un script. Ningún
modelo tiene esas herramientas. El prompt aprobado lo induce (su checklist
final lo pide; problema ya registrado en `evidence/punto4_prompts/REVISION_MANUAL.md`).

- 4 salidas lo afirman textualmente ("Se ha verificado el diagrama con un
  linter de Mermaid…").
- `f3_cloud_generalista_2` dice que aplicó un criterio "equivalente a
  mermaid-cli", revisándolo a mano.
- `f3_cloud_generalista_1` es el caso límite: marca `[x]`, pero aclara que
  "no se dispone de ejecución de herramientas externas" y que la
  correspondencia de IDs se verificó leyendo el documento. Es más honesto que
  los demás. El detector lo cuenta igual y **no se cambió la regla después de
  ejecutar**, pero se deja constancia.

Esto sube la tasa de supuestos de los cloud al 100 % en fase 3, pero **no
resta puntaje** (así se definió en DISENO.md §3). Corrección propuesta para
el punto 8: cambiar el checklist del prompt de Arquitectura por "Recomienda
verificar con…" en lugar de pedir marcarlo como hecho.

Un caso que el detector no captura: `f3_local_1` eligió microservicios y en
su sección de verificación declara "R1 (monolito modular): cumplida por la
arquitectura de microservicios". Es una autoverificación falsa, que los dos
jueces sí detectaron como violación de R1.

## 3. Criterio de "cumple la tarea" en fase 3: más laxo que los jueces

El criterio fijado antes de ejecutar cuenta un SPEC como cubierto si aparece
su identificador. En `f3_local_3` aparecen los 6, así que "cumple", pero
**ambos jueces** dicen que SPEC-01, 04, 05 y 06 no están cubiertos de forma
concreta (revisión 3/10). Leyendo la salida se confirma: son componentes
genéricos (API Gateway, Servicio de Autenticación…) con los SPEC listados en
"Trazabilidad" sin contratos que los resuelvan. Su puntaje (79) sí refleja
el problema a través de la nota de revisión (9 de 30), pero el éxito de la
tarea del modelo local en fase 3 (2/3) está sobreestimado: con el criterio de
los jueces sería 1/3. No se cambia el criterio a posteriori; se informa.

## 4. Recalificación de `f3_local_2`

En la calificación completa, gpt-oss-20b devolvió una respuesta vacía
(`finish_reason='stop'`, sin contenido) en los 3 intentos, y el script usó al
juez secundario, como estaba previsto. Como las otras 17 notas de las fases 1
y 3 eran del juez neutral, se recalificó solo esa ejecución
(`--solo f3_local_2 calificar --forzar`) para que todas usen el mismo juez.

- Primera calificación (Nemotron): revisión 7/10, puntaje 91. Guardada en
  `calificaciones_descartadas/f3_local_2_intento1.json`.
- Segunda (gpt-oss): revisión 7/10, puntaje 91. Nemotron, en la misma pasada,
  le dio 3/10.

El puntaje final no cambió, pero se ve que **el juez secundario dio 7 y 3 a la
misma salida**: la nota de un juez de IA tiene ruido, y por eso se reportan
dos jueces y 3 corridas.

## 5. Lo que se revisó y estaba bien

- Las 27 salidas terminaron con `finish_reason='stop'` (ninguna cortada por
  `max_tokens`), sin respuestas degeneradas.
- Los números marcados como inventados en fase 1 se comprobaron uno a uno en
  el texto (p. ej. "El 95 % de las búsquedas… con 10.000 usuarios
  simultáneos responde en ≤2 segundos" en `f1_local_3`); ninguno aparece en la
  entrada.
- Los huecos que Kimi y Nemotron preguntan (plazo del aviso, tamaño de la
  lista, umbral, invitados) coinciden con los 4 plantados en el caso.
- `f3_local_1` realmente propone microservicios (violación de R1 que marcan
  ambos jueces).
- El 0 de lint de Nemotron y Local corresponde a ≥ 10 avisos reales de ruff
  (Nemotron: 10 de `UP035`, `UP006`, `I001`; Local: 11, incluido un import sin usar `F401`), no a un error de ejecución de ruff.
