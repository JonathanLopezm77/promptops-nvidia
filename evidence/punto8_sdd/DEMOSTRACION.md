# ¿Qué cambia cuando la especificación es la fuente de verdad?

El Componente 5 pide "demostrar qué cambia cuando la especificación se
convierte en la fuente de verdad del desarrollo" y "comprender la diferencia
entre una instrucción temporal y una especificación persistente". Se
demostró con un cambio real, hecho de dos formas sobre la misma cadena
aprobada y con los mismos modelos y prompts aprobados.

**Cambio pedido por el equipo de seguridad:** el bloqueo pasa de 15 a 30 minutos.

- Script: `scripts/sdd_demo_cambio.py` (cada ruta trabaja sobre una copia
  temporal de specs/, src/, tests/sdd/ y sdd/; la cadena aprobada no se toca).
- Evidencia completa: `demostracion/demostracion.json` (prompts, salidas de los
  modelos, parches aplicados, resultado de cada Quality Gate, diff del código)
  y `demostracion/demostracion.log`. Ejecutada el 2026-09-28.

## Ruta A — Instrucción temporal (el cambio va directo al código)

Al modelo de mantenimiento (Nemotron 3 Super, prompt aprobado de la fase 7)
se le pide: *"El equipo de seguridad pide que la cuenta quede bloqueada 30
minutos en lugar de 15. Hacer el cambio en el código."*

| Paso | Resultado |
|---|---|
| A0 Cadena aprobada | 30/30 pruebas, trazabilidad sin problemas |
| A1 El modelo cambia `bloqueo_minutos: int = 15` → `30` en `politica.py` | **Rechazado por dos puertas independientes**: 13 pruebas fallan (las de conformidad leen 15 de la especificación; las generadas esperan 15) y el verificador de trazabilidad marca `politica.py: el código cambió después de su aprobación` |

El cambio "funciona" (el código bloquea 30 minutos), pero **nada más en el
proyecto lo sabe**: el requisito, los criterios de aceptación, la
especificación, la documentación y las pruebas siguen diciendo 15. Con un
flujo basado solo en prompts, esta divergencia pasaría inadvertida. Aquí la
cadena la detecta y bloquea el cambio.

## Ruta B — Especificación primero

| Paso | Qué se hace | Quality Gates |
|---|---|---|
| B1 | El requisito cambia a REQ-AUT-03 v2 ("30 minutos") y pasa por el **motor de requisitos**, como cualquier requisito | Análisis `8d3149ee`: **100**, alta calidad |
| B2 | La especificación pasa a **v1.1.0** (`bloqueo_minutos: 30` y los textos que lo mencionan) y se regeneran specification.md, acceptance_criteria.md y el .feature | El sistema señala **exactamente** lo que quedó desalineado: 4 pruebas de conformidad (las que dependen del bloqueo) y los 4 módulos con el sello de v1.0.1 |
| B3 | El modelo de mantenimiento recibe como incidencia **la diferencia de la especificación** (CHG-AUT-03-01) y cambia 1 línea de `politica.py` | Pasan las de conformidad; **fallan 8 pruebas generadas**, que tenían el 15 escrito: también derivan de la especificación anterior |
| B3b | La fase de Testing (Kimi K3, prompt aprobado de la fase 5) **regenera la suite** desde la especificación v1.1.0 | **35/35 pruebas** |
| B4 | Revisión y sello contra v1.1.0 (`--sellar`) | **CONFORME, 0 problemas** |

Diff final del código: una línea de comportamiento (`15` → `30` en
`politica.py`) más los 4 sellos que emite la herramienta. El requisito, la
especificación, la documentación generada, las pruebas y el código quedan
coherentes y versionados.

## Qué cambió al hacer de la especificación la fuente de verdad

| | Instrucción temporal (prompt) | Especificación persistente (SDD) |
|---|---|---|
| Dónde vive la decisión "30 minutos" | En una conversación con un modelo | En `specs/specification.json` v1.1.0, validada y versionada |
| Qué se actualiza | Solo el código | Requisito → especificación → documentación → código → pruebas |
| Cómo se detecta una divergencia | No se detecta | Pruebas de conformidad (leen la especificación) y el sello del verificador |
| Impacto de un cambio | Hay que adivinarlo | El sistema lo señala: qué pruebas, qué módulos |
| Aprobación | Implícita (quien corre el prompt) | Explícita: el sello solo lo emite la herramienta tras pruebas y revisión |
| Reproducibilidad | Depende del prompt y del modelo del momento | Cualquier modelo que regenere el código se verifica contra el mismo contrato |

## Hallazgos que dejó la demostración

1. **Las pruebas también derivan de la especificación.** La suite generada en
   la cadena tenía los valores escritos (15 minutos): en B2 siguió pasando
   aunque el comportamiento especificado había cambiado, y en B3 falló contra
   el código correcto. Solo las pruebas de conformidad, que leen los valores de
   la especificación, siguieron la fuente de verdad. Consecuencia: al cambiar
   la especificación hay que regenerar también las pruebas (B3b).
2. **Un modelo puede intentar "autoaprobarse".** En 2 de las corridas previas
   (`demostracion/descartadas/`) el modelo de mantenimiento reescribió la línea
   de sello de los módulos con la versión y la huella de la especificación
   nueva. Con el sello original eso habría pasado la verificación en un módulo
   sin cambios. Se endureció el sello (huella del código ligada a la de la
   especificación, `DECISIONES.md` §6) y se agregó una prueba con ese caso
   exacto. En la corrida definitiva el modelo no lo intentó.
3. **Un cambio solo en el código no lo veía el verificador** en la primera
   versión del sello (solo las pruebas). Ahora lo detectan ambos (A1).

## Corridas descartadas (conservadas como evidencia)

| Archivo | Por qué se descartó |
|---|---|
| `demostracion_aplicador_con_errores.*` | El aplicador de parches del arnés no manejaba varios archivos en un bloque y la entrada al modelo duplicaba la línea `# File:`. Aquí se vio el primer intento de autoaprobación |
| `demostracion_sin_regenerar_pruebas.*` | Faltaba el paso B3b; B4 no selló (correcto) porque las pruebas generadas fallaban |
| `demostracion_aplicador_no_contiguo.*` | El aplicador no aplicaba hunks con cambios no contiguos; segundo intento de autoaprobación |
| `demostracion_corte_servidor_local.log` | Corte momentáneo al consultar el servidor local; se agregó reintento |

En todas, los modelos propusieron el mismo cambio correcto (15 → 30); las
fallas fueron del arnés de la demostración, que se corrigió y se probó
(`tests/test_sdd_parches.py`) antes de la corrida definitiva.
