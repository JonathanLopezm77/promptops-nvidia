"""Función objetivo para elegir el modelo de cada fase (punto 7).

Diseño y justificación de cada término: evidence/punto7_seleccion/FUNCION_OBJETIVO.md.

Cada ejecución de benchmarks/execution_log.csv aporta sus métricas; por
celda (fase, modelo) se calculan 5 criterios normalizados a [0, 1] (1 = mejor):

- calidad       = (media(QG) - DE(QG)) / 100: la calidad esperada descontando
                  la variabilidad entre corridas (Consistency Across Runs).
- cumplimiento  = 0.5 * TaskSuccess + 0.5 * media(1 - ViolationRate,
                  1 - HallucinationRate, SchemaCompliance).
- latencia      = menor duración media de la fase / duración media del modelo
                  (duración con reintentos: lo que espera el usuario).
- costo         = menor costo de la fase / costo del modelo; si todos cuestan
                  0 (caso real: capa gratuita de NVIDIA) vale 1 para todos.
                  Variante `pago`: costo de cada ejecución con los precios
                  públicos por token de entrada y de salida (el local no paga
                  por token; su costo de hardware está en `recursos`).
- recursos      = 1 - fracción máxima de la máquina que ocupa el modelo
                  (VRAM, CPU, RAM); 1 para los modelos cloud.

Utilidad = suma ponderada. Elegibilidad: TaskSuccess >= 0.5 (el modelo cumple
la tarea en la mayoría de las corridas); un modelo no elegible no gana aunque
su utilidad sea alta.
"""

import random
import statistics
from dataclasses import dataclass

CRITERIOS = ("calidad", "cumplimiento", "latencia", "costo", "recursos")
UMBRAL_EXITO = 0.5

PERFILES: dict[str, dict[str, float]] = {
    "base": {"calidad": 0.40, "cumplimiento": 0.30, "latencia": 0.15, "costo": 0.10, "recursos": 0.05},
    "calidad_primero": {"calidad": 0.60, "cumplimiento": 0.30, "latencia": 0.05, "costo": 0.05, "recursos": 0.00},
    "interactivo": {"calidad": 0.30, "cumplimiento": 0.20, "latencia": 0.40, "costo": 0.05, "recursos": 0.05},
    "costo_y_recursos": {"calidad": 0.30, "cumplimiento": 0.20, "latencia": 0.10, "costo": 0.20, "recursos": 0.20},
    "iguales": {c: 0.20 for c in CRITERIOS},
}


@dataclass(frozen=True)
class Corrida:
    fase: int
    modelo: str
    qg: float
    cumple: bool
    schema_ok: bool
    violaciones: int
    supuestos: int
    duracion_s: float
    costo_usd: float
    costo_pago_usd: float  # con precios públicos por token; 0 para el local
    local: bool
    fraccion_maquina: float  # 0 para cloud


def _sd(v: list[float]) -> float:
    return statistics.stdev(v) if len(v) > 1 else 0.0


def metricas_celda(corridas: list[Corrida]) -> dict[str, float]:
    n = len(corridas)
    qg = [c.qg for c in corridas]
    return {
        "n": n,
        "qg_media": statistics.mean(qg),
        "qg_sd": _sd(qg),
        "exito": sum(c.cumple for c in corridas) / n,
        "violacion": sum(c.violaciones > 0 for c in corridas) / n,
        "supuestos": sum(c.supuestos > 0 for c in corridas) / n,
        "schema": sum(c.schema_ok for c in corridas) / n,
        "duracion_s": statistics.mean(c.duracion_s for c in corridas),
        "costo_usd": statistics.mean(c.costo_usd for c in corridas),
        "costo_pago_usd": statistics.mean(c.costo_pago_usd for c in corridas),
        "local": corridas[0].local,
        "fraccion_maquina": max(c.fraccion_maquina for c in corridas),
    }


def criterios_fase(celdas: dict[str, dict], costo: str = "real") -> dict[str, dict[str, float]]:
    """Criterios normalizados de todos los modelos de UNA fase (la latencia y el
    costo son relativos al mejor de la fase)."""
    min_dur = min(m["duracion_s"] for m in celdas.values())

    costos = {k: m["costo_pago_usd" if costo == "pago" else "costo_usd"] for k, m in celdas.items()}
    pagos = [c for c in costos.values() if c > 0]
    min_costo = min(pagos) if pagos else 0.0
    salida = {}
    for k, m in celdas.items():
        salida[k] = {
            "calidad": max(0.0, min(1.0, (m["qg_media"] - m["qg_sd"]) / 100)),
            "cumplimiento": 0.5 * m["exito"] + 0.5 * statistics.mean(
                [1 - m["violacion"], 1 - m["supuestos"], m["schema"]]),
            "latencia": min_dur / m["duracion_s"],
            "costo": 1.0 if costos[k] == 0 else min_costo / costos[k],
            "recursos": 1 - m["fraccion_maquina"],
        }
    return salida


def utilidad(criterios: dict[str, float], pesos: dict[str, float]) -> float:
    total = sum(pesos.values())
    return sum(criterios[c] * pesos[c] for c in CRITERIOS) / total


def elegir(celdas: dict[str, dict], pesos: dict[str, float], costo: str = "real",
           exigir_exito: bool = True) -> tuple[str | None, dict]:
    """Devuelve (ganador entre los elegibles, detalle por modelo).
    `exigir_exito=False` desactiva la regla de elegibilidad (análisis de sensibilidad)."""
    crit = criterios_fase(celdas, costo)
    detalle = {k: {**crit[k], "utilidad": utilidad(crit[k], pesos),
                   "elegible": not exigir_exito or celdas[k]["exito"] >= UMBRAL_EXITO} for k in celdas}
    elegibles = {k: d for k, d in detalle.items() if d["elegible"]}
    ganador = max(elegibles, key=lambda k: elegibles[k]["utilidad"]) if elegibles else None
    return ganador, detalle


def pesos_aleatorios(rng: random.Random) -> dict[str, float]:
    """Pesos uniformes sobre el simplex (Dirichlet(1, ..., 1))."""
    v = [rng.expovariate(1.0) for _ in CRITERIOS]
    s = sum(v)
    return {c: x / s for c, x in zip(CRITERIOS, v)}


def montecarlo_pesos(celdas: dict[str, dict], n: int, semilla: int,
                     exigir_exito: bool = True) -> dict[str | None, float]:
    rng = random.Random(semilla)
    victorias: dict[str | None, int] = {}
    for _ in range(n):
        g, _ = elegir(celdas, pesos_aleatorios(rng), exigir_exito=exigir_exito)
        victorias[g] = victorias.get(g, 0) + 1
    return {k: v / n for k, v in victorias.items()}


def bootstrap_corridas(por_modelo: dict[str, list[Corrida]], pesos: dict[str, float],
                       n: int, semilla: int) -> dict[str | None, float]:
    """Remuestrea con reemplazo las corridas de cada modelo y recalcula el ganador:
    mide cuánto depende la elección de qué corridas salieron."""
    rng = random.Random(semilla)
    victorias: dict[str | None, int] = {}
    for _ in range(n):
        celdas = {k: metricas_celda([rng.choice(cs) for _ in cs]) for k, cs in por_modelo.items()}
        g, _ = elegir(celdas, pesos)
        victorias[g] = victorias.get(g, 0) + 1
    return {k: v / n for k, v in victorias.items()}
