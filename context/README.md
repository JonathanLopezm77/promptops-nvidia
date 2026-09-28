# /context

Paquetes de contexto (Context Engineering): lo que recibe cada fase del SDLC
además de su prompt aprobado. La regla es que cada fase reciba la salida
**validada** de la fase anterior más la información del dominio necesaria, y
nada más.

| Contexto | Lo recibe | Dónde |
|---|---|---|
| Restricciones técnicas R1-R6 de la cadena SDD | Fase 3 (arquitectura) del punto 8 | `context/sdd_restricciones_tecnicas.md` |
| Especificación, requisito y criterios aprobados | Fases 3, 4 y 5 del punto 8 | `specs/` (se leen de ahí, no de una conversación) |
| Casos del benchmark (necesidad + contexto, especificación + restricciones, diseño + contratos) | Fases 1, 3 y 4 del punto 6 | `benchmarks/casos/` |
| Casos del sondeo (requisitos con trampas, código con defectos, artefacto y entorno, incidencia y métricas reales) | Fases 2, 5, 6 y 7 del punto 7 | `benchmarks/casos_sondeo/` |
| Contexto del proyecto de cada requisito | Motor de requisitos (punto 3) | `scripts/casos_requisitos.py` y `specs/requirements.md` |
