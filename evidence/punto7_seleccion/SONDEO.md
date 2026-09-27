# Sondeo de las fases 2, 5, 6 y 7

El enunciado no exige corridas en estas fases: pide una "selección argumentada
del modelo, apoyada en documentación técnica, características del modelo,
restricciones de costo/recursos y hallazgos transferibles del benchmark"
(§7.1). Para no argumentar solo en abstracto se hizo además un **sondeo**:
**1 corrida por modelo y fase** (12 en total), con los prompts aprobados del
punto 4, los mismos 3 modelos y los mismos parámetros del benchmark
(`temperature 0.2`, `top_p 0.95`, `max_tokens 8192`), y un calificador
automático por fase que implementa su Quality Gate del Componente 3.

**No forma parte de las 27 ejecuciones** y tiene una sola corrida por
combinación: sirve para detectar diferencias grandes y modos de falla, no para
medir consistencia.

- Casos: `benchmarks/casos_sondeo/` · Calificadores: `benchmarks/calificadores_sondeo.py`
  (19 pruebas en `tests/test_calificadores_sondeo.py`) · Script: `scripts/sondeo_fases.py`
- Evidencia: `sondeo/ejecuciones/` (prompt y salida completos), `sondeo/calificaciones/`,
  `sondeo/sondeo.csv`, `sondeo/manifiesto.json`.

## 1. Casos y Quality Gates

| Fase | Entrada | Quality Gate (enunciado) → cómo se mide |
|---|---|---|
| 2 Especificación | 8 requisitos REQ de la lista de deseos con trampas: huecos de numeración (no hay REQ-04 ni REQ-09), una referencia válida (REQ-06 → REQ-02), una rota (REQ-07 → REQ-09), una contradicción (REQ-03: máximo 50 vs REQ-08: sin límite) y un requisito con riesgo legal (REQ-10: conservar datos de cuentas eliminadas para marketing) | *Completitud + consistencia + schema* → 9 chequeos: JSON con la estructura exacta, numeración SPEC idéntica a la REQ, origen, campos completos, ≥ 2 criterios Gherkin por SPEC, la dependencia, la referencia rota, la contradicción y la alerta legal |
| 5 Testing | El contrato de la fase 4 y la implementación de referencia con **2 defectos plantados**: umbral con `>` en lugar de `>=` y `list_items` que devuelve la lista interna | *Pass rate + cobertura + defectos* → la suite generada se ejecuta: validez contra el código correcto (20), puntaje de mutación con los 12 mutantes del punto 6 (30), defectos plantados que la suite detecta (20) y que el reporte menciona (10), cobertura de líneas con coverage.py (10), trazabilidad TEST-XX y matriz (10) |
| 6 Deployment | **Esta plataforma** (FastAPI, PostgreSQL, variables de entorno) a desplegar en **Render** con Docker y validación previa en GitHub Actions | *Build + seguridad + despliegue reproducible* → 11 chequeos: pipeline, Dockerfile multietapa, imágenes con versión fija, usuario no root, configuración del entorno, YAML válido, sin secretos en claro, verificación del despliegue, rollback, tabla de variables. **No hay Docker en la máquina**: no se construye la imagen (se compensa con la revisión manual, §3) |
| 7 Mantenimiento | El código con **el defecto real que cometió Nemotron en el punto 6** (`list_items` sin ordenar), la incidencia y **métricas medidas de verdad** (33/34 pruebas, cobertura 100 %, ruff 0, complejidad máx. 5) | *Regression tests + deuda técnica + trazabilidad* → se aplica el cambio propuesto al código y se corren las 34 pruebas ocultas (60), alcance mínimo: solo cambia la función afectada (10), las 7 secciones (15), trazabilidad SPEC-03 / ARCH-01 sin inventar REQ (15) |

## 2. Resultados

| Fase | Modelo | Puntaje | Cumple | Duración | Tokens entrada / salida | USD con precio público |
|---|---|---|---|---|---|---|
| 2 | **Kimi** | **100** | **sí** | 282 s | 2430 / 5333 | 0.0873 |
| 2 | Nemotron | 0 | no: agotó los 8192 tokens razonando | 70 s | 2180 / 8192 | 0.0039 |
| 2 | Local | 66.7 | no | 207 s | 2194 / 2652 | 0 |
| 5 | **Kimi** | **100** | **sí** | 480 s | 2909 / 8039 | 0.1293 |
| 5 | Nemotron | 85.0 | sí | 63 s | 2716 / 7607 | 0.0036 |
| 5 | Local | 54.7 | no | 298 s | 2693 / 3681 | 0 |
| 6 | Kimi | 100 | sí (ver §3) | 217 s | 1805 / 5071 | 0.0815 |
| 6 | Nemotron | 100 | sí (ver §3) | 41 s | 1585 / 5297 | 0.0025 |
| 6 | Local | 72.7 | no | 92 s | 1654 / 1312 | 0 |
| 7 | Kimi | 100 | sí | 90 s | 2435 / 1550 | 0.0306 |
| 7 | **Nemotron** | **100** | **sí** | **21 s** | 2191 / 1370 | 0.0008 |
| 7 | Local | 100 | sí | 67 s | 2234 / 906 | 0 |

Las 12 ejecuciones respondieron al primer intento. Durante el sondeo la PC
tenía otro programa abierto (3 GB de RAM libres, 5.5 GB de VRAM ocupados): las
**duraciones del modelo local no son comparables** con las del benchmark; su
calidad sí.

### Detalle por fase

**Fase 2.** Kimi cumplió los 9 chequeos: respetó los huecos (SPEC-01, 02, 03,
05, 06, 07, 08, 10), registró la dependencia de REQ-06, la referencia rota a
REQ-09, la contradicción REQ-03/REQ-08 y la alerta legal de REQ-10. El local
numeró bien pero no reportó **ninguna** inconsistencia ni alerta (0 y 0).
Nemotron gastó los 8192 tokens en su razonamiento y nunca escribió el JSON; el
servidor de NVIDIA devolvió ese razonamiento como respuesta (`finish_reason =
length`), así que se califica 0. **Variante** (`experimentos/nemotron_f2_presupuesto*`):
con `max_tokens 16384`, 2 corridas: 88.9 (un criterio Gherkin quedó cortado a
la mitad) y 100. La segunda usó solo 7084 tokens, así que el largo de su
razonamiento varía mucho (7 000 a más de 11 000 tokens) entre corridas iguales.

**Fase 5.** Kimi: 28 pruebas, todas válidas contra el código correcto,
**detectan los 12 mutantes**, los 2 defectos plantados, cobertura 100 % y los
dos defectos descritos en su reporte. Nemotron: 23 pruebas válidas, detecta
los 2 defectos plantados y los reporta, pero solo 8 de 12 mutantes (no prueba
el redondeo HALF_UP, el orden de validaciones, el valor por defecto de
`max_items` ni el límite de 100 %). Local: 14 pruebas, 4 de 12 mutantes, solo 1
de los 2 defectos; y **su reporte dice "No se han encontrado defectos"**
aunque una de sus propias pruebas detecta el del umbral (no ejecutó la suite y
concluyó algo falso).

**Fase 7.** Los tres encontraron la causa raíz y propusieron el mismo cambio
mínimo (`sorted` estable por `added_at` en `list_items`), que pasa las 34
pruebas ocultas, con las 7 secciones y la trazabilidad correcta. Única
diferencia (revisión manual): el local **dejó el comentario original**, que
tras el cambio es falso ("la lista interna conserva el orden de inserción, que
coincide con el orden por fecha"); Kimi y Nemotron lo reemplazaron por uno
correcto. Es un defecto localizado de una línea: el caso es fácil y no separa
a los modelos en calidad, solo en tiempo y costo.

## 3. Revisión manual (fase 6)

El calificador automático no construye la imagen ni valida el esquema de
Render, así que se revisaron a mano los 3 despliegues (claves de `render.yaml`
contrastadas con la documentación oficial: <https://render.com/docs/blueprint-spec>).

| | Kimi | Nemotron | Local |
|---|---|---|---|
| `render.yaml` | Válido: `runtime: docker`, `healthCheckPath`, `fromDatabase`, `sync: false` para secretos, `autoDeploy: false` (Render despliega solo tras pasar CI, como pide el entorno) | **Inválido**: usa `fromSecret`, clave que no existe en Render (las válidas son `value`, `fromService`, `fromDatabase`, `generateValue`, `sync`, `previewValue`) | **Inválido**: archivo `.render.yaml`, `services` como mapa y no lista, claves inexistentes (`ports`), variables con valores de ejemplo escritos en el archivo |
| Dockerfile | Multietapa, versión exacta (`3.12.7-slim-bookworm`), usuario no root, `HEALTHCHECK`, puerto desde `PORT`. Defecto: `COPY *.sql ./` busca SQL en la raíz, donde no hay (están en `backend/`, que ya se copia); según el constructor de Docker puede fallar | **El contenedor no arrancaría**: la etapa final copia solo `site-packages` y no `/usr/local/bin`, donde queda el ejecutable `uvicorn` que usa el `CMD` | Una sola etapa, sin usuario no root |
| Pipeline | Build con caché y despliegue por deploy hook solo en `main`. Debilidad: el smoke test termina en `|| true`, no puede fallar | Reejecuta `pytest` aunque el prompt lo prohíbe ("ya pasaron"); hace un `git commit` en CI sin push, que no tiene efecto | Sin verificación del despliegue |

Conclusión manual: el puntaje automático empata a Kimi y Nemotron (100), pero
**solo el de Kimi es desplegable con correcciones menores**; el de Nemotron
falla al arrancar y su configuración de Render no es válida. Los tres
confirman que en Deployment la revisión humana y un `docker build` real en CI
son imprescindibles (el propio pipeline de Kimi lo haría).

## 4. Límites

- 1 corrida por combinación (2 extra para la variante de Nemotron): no mide
  consistencia. Las fases 2, 5 y 6 muestran diferencias grandes; la 7 empata.
- Un caso por fase, del mismo dominio que el benchmark.
- La fase 6 no se construyó ni desplegó; la revisión manual lo compensa en parte.
