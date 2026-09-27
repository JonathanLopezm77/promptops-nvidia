# Punto 4 — Revisión manual de los 7 prompts del SDLC

Complementa el catálogo generado automáticamente (`prompts/*.md` y
`prompts/validation_metrics.csv`). El Auditor de la plataforma evalúa
cada prompt **por separado** con las 21 propiedades oficiales; esta
revisión mira lo que el Auditor no ve: la coherencia de la **cadena** de
prompts, los cambios de alcance y el costo. Revisión asistida por IA
(Claude) sobre los JSON de `runs/`; el equipo debe validarla.

## Resumen

| Fase | Inicial | Aprobada | Delta | Mejor alcanzado | Palabras (inicial → aprobada) |
|---|---|---|---|---|---|
| 1. Requerimientos | 76 | 86 | +10 | 87 | 94 → 498 |
| 2. Análisis / Especificación | 75 | 88 | +13 | 89 | 82 → 905 |
| 3. Arquitectura / Diseño | 79 | 88 | +9 | 88 | 80 → 606 |
| 4. Implementación | 42 | 86 | +44 | 86 | 80 → 828 |
| 5. Testing / QA | 42 | 91 | +49 | 91 | 87 → 537 |
| 6. Deployment | 42 | 88 | +46 | 89 | 93 → 630 |
| 7. Mantenimiento | 76 | 90 | +14 | 90 | 90 → 555 |

Las 7 versiones aprobadas pasan los 4 Quality Gates y conservan todas las
variables de su plantilla (`{{...}}`).

## Cómo se aprobaron (importante para la sustentación)

- **Requerimientos y Arquitectura:** aprobadas por el usuario en la
  interfaz.
- **Análisis, Implementación, Testing, Deployment y Mantenimiento:**
  aprobadas por el asistente (Claude) **por instrucción explícita del
  usuario**, sin una revisión previa del usuario de cada prompt. Queda
  registrado en `manifiesto.json` (`aprobaciones_delegadas`). La plataforma
  las muestra como decisiones humanas "approve"; esta nota aclara quién las
  ejecutó.
- Arquitectura además se **ejecutó** (no lo exige el punto 4); ver
  `INCIDENTES.md`.
- En todos los casos se aprobó la **última** iteración (la plataforma
  aprueba siempre la última). En Requerimientos, Análisis y Deployment la
  última quedó 1 punto por debajo de la mejor alcanzada.

## Hallazgos que el Auditor no detectó

### 1. La cadena REQ → SPEC queda rota (Requerimientos)
La versión aprobada de Requerimientos numera **RF-01 / RNF-01** en lugar
de **REQ-01**, pero la de Análisis exige "por cada requisito REQ-XX, una
SPEC-XX con la misma numeración". Se señaló antes de aprobar y se aprobó
sin corregir. **Consecuencia para el punto 8 (SDD):** al encadenar las
fases hay que corregir el prompt de Requerimientos (nueva iteración con ese
feedback) o traducir RF/RNF a REQ antes de pasar a Análisis.

### 2. Cambio de alcance (Análisis)
La versión aprobada define el rol como "especializado en especificación
de requisitos **y en contextos regulados**". El proyecto no indica ningún
dominio regulado: es un supuesto agregado por el Optimizer.

### 3. El Optimizer "juega para el Auditor" (Arquitectura)
La versión aprobada de Arquitectura:
- pide marcar como hecho "Se ha verificado el diagrama **con un linter de
  Mermaid** y se ha corroborado la correspondencia de IDs **mediante un
  script de trazabilidad**", cosas que el modelo no puede ejecutar: lo
  empuja a declarar verificaciones que no hizo;
- agrega un "**Incentivo de calidad**: ... recibirá una evaluación
  positiva".

Ambos elementos responden literalmente a propiedades del Auditor (P10
Metacognición, P12 Recompensas/Incentivos): el Optimizer optimiza la
métrica, no necesariamente la calidad real (ley de Goodhart).

### 4. Autoevaluación en Arquitectura
La versión aprobada de Arquitectura (iteración 5) la produjo el **modelo
de respaldo** `nemotron-3-super-120b`, porque `kimi-k3` degeneró. Ese
modelo es también el **Auditor**: en esa iteración el mismo modelo
escribió y calificó el prompt (posible sesgo de autoevaluación).

### 5. Los prompts crecen de 6 a 11 veces
De ~80-94 palabras a 498-905. Mejora la estructura (secciones, formato,
reglas, ejemplos) pero multiplica los tokens de entrada de cada ejecución,
lo que el benchmark (punto 6) debe medir como costo y latencia. El Gate 4
(Eficiencia y Foco) no lo penalizó.

## Observaciones sobre el Auditor

- **Puntaje total agrupado:** Implementación, Testing y Deployment
  recibieron exactamente **42** en la línea base, con puntajes por
  propiedad y recomendaciones distintos. El `total_score` es un juicio
  holístico del modelo (no un cálculo) y tiende a repetir el mismo valor
  para perfiles parecidos (3 Gates en FAIL).
- **Variabilidad:** el mismo prompt inicial de Arquitectura obtuvo 82 en
  la primera validación y 79 en la segunda.
- **Las auto-iteraciones no son monótonas:** p. ej. Implementación
  82 → 85 → 82 → 86; Requerimientos 87 → 86 → 84 → 86.

## Recomendaciones antes de usar los prompts en el benchmark y en SDD

1. Corregir Requerimientos (REQ-XX) para no romper la cadena.
2. Quitar de Arquitectura la afirmación de verificación con herramientas
   y el "incentivo".
3. Considerar dar al Optimizer un límite de longitud, o pedir al Auditor
   que penalice el crecimiento (P1, Cantidad de tokens).
