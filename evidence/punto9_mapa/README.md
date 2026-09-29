# Punto 9 — Mapa mental: del Prompt Engineering al SDD (Componente 2)

**Mapa interactivo (público):** https://promptops-nvidia.onrender.com/mapa.html
(archivo fuente: `frontend/mapa.html`, HTML + CSS + JavaScript sin dependencias).

Cubre las 4 ramas del enunciado y su condición de calidad (relaciones
causales, no solo definiciones):

| Rama del enunciado | Dónde está en el mapa |
|---|---|
| Conceptos (18: LLM, SLM, Prompt y Context Engineering, agente, subagente, agentic loop, harness, guardrails, MCP, Skills, Specification, SDD, sistemas multiagente, Human-in-the-loop, Quality Gate, observabilidad, gobernanza) | Pestaña **Conceptos**: 5 capas (Prompt → Context → Harness → Specification → Governance) con las relaciones dibujadas y una ficha por concepto |
| Metodologías (8, del desarrollo tradicional al multiagente) | Pestaña **Metodologías**, con el cambio del rol del ingeniero |
| Herramientas | Pestaña **Herramientas**, agrupadas por capa y marcadas como usadas o no en el proyecto |
| Beneficios y riesgos **por concepto** | Pestaña **Beneficios y riesgos**: problema, beneficio, riesgo y qué controla el ingeniero, para los 18 |
| Relaciones causales: qué pedimos, qué sabe el modelo, cómo actúa, qué se construye, cómo se controla | Las líneas entre capas y el botón **Recorrer la cadena** |

Cada concepto tiene un ejemplo real tomado de la evidencia de los puntos 3 a 8.

## Versiones estáticas (también con código)

| Archivo | Herramienta | Uso |
|---|---|---|
| `mapa_mental_markmap.md` → `mapa_mental.png` | [Markmap](https://markmap.js.org/repl) | Mapa mental en árbol con las 4 ramas |
| `mapa_relaciones.mmd` → `mapa_relaciones.png` | [Mermaid](https://mermaid.live) | Diagrama de las 5 capas y sus relaciones |
