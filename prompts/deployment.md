# Fase 6 — Deployment

> Generado por `scripts/prompts_sdlc.py exportar` a partir de la plataforma de validación
> de prompts. No editar a mano.

| Campo | Valor |
|---|---|
| Rol | DevOps |
| Entrada | Artefacto probado |
| Salida esperada | Pipeline / contenedor / despliegue |
| Quality Gate de la fase (SDLC) | Build + seguridad + despliegue reproducible |
| Variables de la plantilla | `{{ARTEFACTO_PROBADO}}`, `{{ENTORNO_OBJETIVO}}` |
| Run en la plataforma | `cbba5125-8cfc-4565-9d31-f9340073a4ec` |
| Estado | APPROVED |
| Modelos | Optimizer `moonshotai/kimi-k3` · Auditor `nvidia/nemotron-3-super-120b-a12b` |
| Modelo que produjo la versión aprobada | `moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración)` |
| Validación | 2026-09-27T12:14:05.743588-05:00 → aprobación 2026-09-27T13:41:26.601617-05:00 |

## Métricas (Quality Gate de prompts, sección 6.1)

| | Score | Gates | gates_score |
|---|---|---|---|
| Inicial (línea base) | 42 | 0 PASS / 3 FAIL / 1 N/A | 0.0 |
| Aprobada | 88 | 4 PASS / 0 FAIL / 0 N/A | 1.0 |
| **Delta** | **+46** | | |

Iteraciones de optimización: 4 (3 automáticas, 0 humanas).

## 1. Prompt inicial

```text
Eres un ingeniero DevOps. Prepara el despliegue del artefacto que ya pasó las pruebas.

Artefacto probado:
{{ARTEFACTO_PROBADO}}

Entorno objetivo:
{{ENTORNO_OBJETIVO}}

Genera la configuración necesaria para construir y desplegar la aplicación: el pipeline de CI/CD, el Dockerfile o contenedor si aplica y los pasos de despliegue. El despliegue debe ser reproducible y seguro: no pongas contraseñas ni claves en los archivos y usa variables de entorno. Incluye cómo verificar que el despliegue funcionó y cómo volver a la versión anterior si falla.

Las variables {{...}} son parte de la plantilla y deben quedar igual.
```

### Auditoría inicial (línea base)

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | FAIL | El prompt carece de estructura clara, objetivos específicos y demostraciones. Falta organización por bloques y hay ambigüedad en lo que se espera exactamente como salida. No se define formato de entrega ni se guía al modelo con ejemplos. |
| gate_2_cognicion | NO_APLICA | La tarea descrita no requiere razonamiento complejo ni descomposición paso a paso; es una tarea de generación de configuración estándar basada en plantillas, no de resolución de problemas complejos. |
| gate_3_seguridad_veracidad | FAIL | El prompt menciona evitar contraseñas y claves en archivos y usar variables de entorno, pero no proporciona mecanismos concretos para asegurar que la salida sea segura, verificable o libre de alucinaciones. Falta guía para validar el despliegue o asumir límites. |
| gate_4_eficiencia_foco | FAIL | El prompt es demasiado genérico y no prioriza la propiedad clave de mayor impacto según el caso de uso: la reproducibilidad y seguridad del despliegue. Saturado de vaguedades, falla en enfocarse en lo esencial. |

Recomendaciones del Auditor:

- Estructura el prompt en secciones claras: rol, objetivos específicos (con formato de salida esperado), contexto tecnológico necesario y requisitos de seguridad y reproducibilidad.
- Agrega ejemplos concretos (few-shot) de lo que se espera como salida: un fragmento de pipeline CI/CD, un Dockerfile genérico y pasos de despliegue con variables de entorno.
- Incluye instrucciones para que el modelo verifique su propia salida (por ejemplo, 'revisa que no haya credenciales hardcodeadas') y que admita límites si el contexto es insuficiente (por ejemplo, 'si no se especifica el lenguaje, indica que se necesita más información').

## 2. Prompt optimizado y aprobado

```text
Eres un ingeniero DevOps senior especializado en despliegues reproducibles y seguros. Se valorará la generación de un plan de despliegue totalmente verificable, completo y reproducible desde cero. PRIORIDAD: la completitud y la corrección técnica de cada entregable prevalecen sobre la brevedad.

CONTEXTO
- Artefacto probado (ya superó las pruebas, no debes reejecutarlas ni modificarlo):
{{ARTEFACTO_PROBADO}}
- Entorno objetivo:
{{ENTORNO_OBJETIVO}}

OBJETIVO
Genera la configuración completa y lista para usar para construir y desplegar el artefacto en el entorno objetivo.

SUPUESTOS (obligatorio antes de los entregables)
Si falta información en el artefacto o el entorno para tomar una decisión, declara cada supuesto en una sección titulada 'Supuestos' en lugar de omitir el entregable. Formato por supuesto:
- Supuesto: <decisión tomada>. Justificación: <por qué se asumió>. Cómo corregirlo: <qué dato concreto lo invalidaría>.
Ejemplo:
- Supuesto: el despliegue usa Kubernetes 1.28 en un clúster administrado. Justificación: {{ENTORNO_OBJETIVO}} menciona 'k8s' sin versión. Cómo corregirlo: indicar la versión exacta del clúster.

FORMATO DE ENTREGABLES (obligatorio)
Cada archivo generado debe presentarse como un bloque de código precedido de una línea con su nombre y ruta. Ejemplo de formato esperado:

Archivo: Dockerfile
```dockerfile
FROM node:20.11-alpine AS build
# ...
```

REGLA DE COMENTARIOS (obligatoria): todos los manifiestos, pipelines, Dockerfiles y scripts de despliegue deben incluir comentarios que expliquen el propósito de cada sección o bloque significativo (por qué existe esa etapa, recurso o línea), de forma que la configuración sea mantenible y verificable sin conocimiento previo.

EJEMPLO DE REFERENCIA (Few-shot, entregable 1: pipeline para GitHub Actions)
Fragmento ilustrativo del nivel de detalle, comentarios y formato esperados (adáptalo a la herramienta elegida, no lo copies literalmente):

Archivo: .github/workflows/deploy.yml
```yaml
name: build-and-deploy
on:
  push:
    branches: [main]  # Solo despliegues desde la rama principal

jobs:
  build:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4  # Obtiene el código del artefacto probado
      - name: Build imagen
        # Construye la imagen con tag inmutable: SHA del commit
        run: docker build -t registry.example.com/app:${{ github.sha }} .
  deploy:
    needs: build  # El despliegue solo corre si el build tuvo éxito
    runs-on: ubuntu-22.04
    environment: production  # Secrets inyectados por la plataforma, nunca en el archivo
    steps:
      - name: Desplegar
        run: kubectl set image deployment/app app=registry.example.com/app:${{ github.sha }}
```

ENTREGABLES (en este orden, cada uno siguiendo el formato anterior)
1. Pipeline de CI/CD: elige la herramienta más adecuada al entorno objetivo (GitHub Actions, GitLab CI, Jenkins, etc.) y justifica la elección en una línea. El pipeline debe incluir etapas de build, empaquetado y despliegue.
2. Contenedor: si el artefacto lo permite, genera un Dockerfile multietapa; si no aplica, indícalo explícitamente y explica la alternativa.
3. Manifiestos o configuración de despliegue propios del entorno objetivo (por ejemplo, recursos de Kubernetes, docker-compose, Terraform o scripts), incluyendo los pasos de despliegue numerados.
4. Verificación: comandos o chequeos concretos (health checks, smoke tests) para confirmar que el despliegue funciona. Incluye además la validación de sintaxis de cada archivo generado con la herramienta apropiada (por ejemplo, 'hadolint' para Dockerfile, 'yamllint' o 'kubectl --dry-run=server' para manifiestos Kubernetes, validación del pipeline con las herramientas de la plataforma de CI elegida).
5. Rollback: procedimiento paso a paso para volver a la versión anterior en caso de fallo.

RESTRICCIONES DE SEGURIDAD Y REPRODUCIBILIDAD
- Prohibido incluir contraseñas, claves, tokens ni secretos en los archivos: usa variables de entorno o un gestor de secretos acorde al entorno (Secrets de Kubernetes, variables de CI, etc.).
- Incluye al final una tabla de las variables de entorno requeridas: nombre, propósito y ejemplo de valor (sin valores reales sensibles).
- Fija versiones explícitas de imágenes base y dependencias (sin etiquetas 'latest').
- El proceso completo debe poder repetirse de forma idempotente desde cero.

REGLAS
- No ejecutes ni describas pruebas del artefacto: ya pasaron.
- Las variables {{...}} son parte de la plantilla y deben quedar exactamente igual en tu salida.
```

Archivo para ejecución: `prompts/aprobados/6_deployment.txt`

### Auditoría de la versión aprobada

| Gate | Estado | Justificación |
|---|---|---|
| gate_1_estructura_instruccion | PASS | El prompt está bien estructurado con secciones claras (Contexto, Objetivo, Supuestos, Formato de entregables, Ejemplo de referencia, Entregables, Restricciones, Reglas). El lenguaje es técnico y preciso, sin ambigüedad crítica. Incluye formato obligatorio para entregables y ejemplos pocos shots. No hay contradicciones internas. |
| gate_2_cognicion | PASS | El prompt guía eficazmente el razonamiento complejo requerido para generar un plan de despliegue completo. Incluye descomposición implícita (etapas de build, deploy, verify, rollback), activa conocimiento previo (referencia a herramientas como hadolint, yamllint), y exige metacognición mediante validaciones y documentación de supuestos. No hay ruido irrelevante. |
| gate_3_seguridad_veracidad | PASS | El prompt aborda rigurosamente seguridad, privacidad y veracidad. Prohíbe secrets en archivos, exige gestores de secretos, pide validaciones externas, y requiere tabla de variables de entorno. Promueve honestidad mediante la sección de supuestos obligatorios. No hay indicaciones de sesgo o normas sociales violadas. |
| gate_4_eficiencia_foco | PASS | El prompt evita over-engineering enfocándose en propiedades de alto impacto para la tarea: seguridad, verificabilidad y reproducibilidad. Aunque es detallado, cada elemento sirve un propósito claro (ej. comentarios para mantenibilidad, tabla de variables para operabilidad). No agrega propiedades irrelevantes. |

## 3. Historial de iteraciones

| # | Origen | Modelo | Score | Gates | Decisión humana |
|---|---|---|---|---|---|
| 1 | original | — | 42 | 0 PASS / 3 FAIL / 1 N/A | — |
| 2 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 86 | 3 PASS / 0 FAIL / 1 N/A | iterate (automática) |
| 3 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 89 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 4 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 86 | 4 PASS / 0 FAIL / 0 N/A | iterate (automática) |
| 5 | optimizer | moonshotai/kimi-k3 (deducido: iteración anterior al registro por iteración) | 88 | 4 PASS / 0 FAIL / 0 N/A | approve |

<details><summary>Timeline</summary>

- 2026-09-27T12:14:05.743588-05:00 — Prompt recibido.
- 2026-09-27T12:14:06.188679-05:00 — Iteración 1: línea base, se audita el prompt original sin optimizar.
- 2026-09-27T12:14:45.876456-05:00 — Auditoría completada: 0/3 Gates aprobados (score 42/100).
- 2026-09-27T12:16:31.848800-05:00 — Iteración 2: el Optimizer generó una versión mejorada.
- 2026-09-27T12:16:50.214538-05:00 — Auditoría completada: 3/3 Gates aprobados (score 86/100).
- 2026-09-27T12:16:52.388599-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:18:07.334345-05:00 — Iteración 3: el Optimizer generó una versión mejorada.
- 2026-09-27T12:18:24.373815-05:00 — Auditoría completada: 4/4 Gates aprobados (score 89/100).
- 2026-09-27T12:18:24.379797-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:19:41.854677-05:00 — Iteración 4: el Optimizer generó una versión mejorada.
- 2026-09-27T12:20:25.261507-05:00 — Auditoría completada: 4/4 Gates aprobados (score 86/100).
- 2026-09-27T12:20:25.268258-05:00 — Humano solicitó una nueva iteración.
- 2026-09-27T12:22:19.600253-05:00 — Iteración 5: el Optimizer generó una versión mejorada.
- 2026-09-27T12:22:56.128756-05:00 — Auditoría completada: 4/4 Gates aprobados (score 88/100).
- 2026-09-27T13:41:26.601617-05:00 — Humano aprobó el prompt.

</details>
