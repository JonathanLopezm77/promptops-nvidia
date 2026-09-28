# /specs — Especificación SDD (Componente 5)

Cadena trazable de un requisito validado hasta el código y sus pruebas:

```
NEC-AUT-01 → REQ-AUT-03 → AC-AUT-03-01..07 → SPEC-AUT-03 → ARCH-01..03 → src/auth_lockout → tests/sdd
 necesidad    requisito    criterios          especificación  contrato      código             pruebas
```

| Archivo | Qué es | Quién lo escribe |
|---|---|---|
| `requirements.md` | Necesidad y requisito fuente REQ-AUT-03, con su validación | Equipo (validado con el motor de requisitos) |
| **`specification.json`** | **La especificación: única fuente de verdad** (parámetros, reglas, criterios, decisiones) | Fase 2 (Kimi K3) + revisión humana |
| `schemas/specification.schema.json` | JSON Schema de la especificación (generado desde `sdd/esquema.py`) | Herramienta |
| `specification.md` | Vista legible de la especificación | **Generado**: `python -m sdd.render` |
| `acceptance_criteria.md` | Criterios de aceptación en Gherkin | **Generado** |
| `acceptance/REQ-AUT-03.feature` | Los mismos criterios en un archivo Gherkin | **Generado** |
| `architecture_contract.md` | Componentes ARCH y contrato normativo del código | Fase 3 (Nemotron 3 Super) + revisión humana |
| `traceability_matrix.md` | Matriz REQ → AC → SPEC → ARCH → CODE → TEST y estado de la cadena | **Generado**: `python -m sdd.trazabilidad` |

Los archivos generados no se editan a mano: se cambia `specification.json` y
se regeneran (el verificador detecta si alguien los editó).

## Cómo se cambia algo (especificación primero)

1. Cambiar el requisito y validarlo con el motor de requisitos.
2. Cambiar `specification.json` (nueva versión) y `python -m sdd.render`.
3. `python -m sdd.trazabilidad` marca el código como **no conforme** (su sello
   apunta a la versión anterior) y las pruebas de conformidad, que leen los
   valores de la especificación, muestran qué comportamiento cambió.
4. Adecuar el código y regenerar las pruebas con las fases 4/7 y 5.
5. Si todas las pruebas pasan y la revisión humana lo aprueba:
   `python -m sdd.trazabilidad --sellar`.

`pytest` ejecuta el verificador (`tests/test_sdd_trazabilidad.py`): una cadena
rota hace fallar la suite. Evidencia completa del punto 8: `evidence/punto8_sdd/`.
