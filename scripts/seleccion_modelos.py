"""Aplica la función objetivo (benchmarks/seleccion.py) a las 27 ejecuciones.

    python scripts/seleccion_modelos.py

Lee benchmarks/execution_log.csv y el manifiesto del benchmark (para el tamaño
de la máquina) y escribe en evidence/punto7_seleccion/:

- utilidad_por_perfil.csv  criterios, utilidad y elegibilidad por fase, perfil y modelo
- montecarlo_pesos.csv     % de victorias con 20 000 vectores de pesos aleatorios
- bootstrap_corridas.csv   % de victorias remuestreando las corridas (10 000 veces)
- salida.txt               resumen legible (lo mismo que imprime)
"""

import csv
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
from benchmarks.seleccion import (
    CRITERIOS,
    PERFILES,
    Corrida,
    bootstrap_corridas,
    elegir,
    metricas_celda,
    montecarlo_pesos,
)

LOG = RAIZ / "benchmarks" / "execution_log.csv"
MANIFIESTO = RAIZ / "evidence" / "punto6_benchmark" / "manifiesto.json"
PRECIOS = RAIZ / "evidence" / "punto7_seleccion" / "precios_publicos.json"
SALIDA = RAIZ / "evidence" / "punto7_seleccion"
N_MONTECARLO, N_BOOTSTRAP, SEMILLA = 20_000, 10_000, 20260927


def maquina() -> dict[str, float]:
    m = json.loads(MANIFIESTO.read_text(encoding="utf-8"))["sesiones"][-1]["maquina_antes"]
    vram_total = float(re.search(r"(\d+) MiB", m["gpu"]).group(1))
    return {"vram_mb": vram_total, "nucleos": m["nucleos_logicos"], "ram_mb": m["ram_total_gb"] * 1024}


def precios() -> dict[str, tuple[float, float]]:
    """USD por token (entrada, salida) de cada modelo cloud, según precios_publicos.json."""
    datos = json.loads(PRECIOS.read_text(encoding="utf-8"))["modelos"]
    return {m["id"]: (float(m["pricing"]["prompt"]), float(m["pricing"]["completion"])) for m in datos}


def cargar(juez: str = "principal") -> dict[int, dict[str, list[Corrida]]]:
    """`juez="secundario"`: usa el puntaje recalculado con el otro juez (fases 1 y 3)."""
    maq = maquina()
    tarifas = precios()
    datos: dict[int, dict[str, list[Corrida]]] = {}
    with LOG.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            local = bool(r["vram_modelo_mb"])
            fraccion = max(float(r["vram_modelo_mb"]) / maq["vram_mb"],
                           float(r["cpu_proceso_media_pct"]) / (100 * maq["nucleos"]),
                           float(r["ram_proceso_max_mb"]) / maq["ram_mb"]) if local else 0.0
            otro = juez == "secundario" and r["puntaje_otro_juez"]
            c = Corrida(
                fase=int(r["fase"]), modelo=r["modelo_clave"],
                qg=float(r["puntaje_otro_juez"] if otro else r["quality_gate_score"]),
                cumple=r["cumple_tarea"] == "True", schema_ok=r["schema_ok"] == "True",
                violaciones=int(r["n_violaciones"]), supuestos=int(r["n_supuestos_no_sustentados"]),
                duracion_s=float(r["duracion_con_reintentos_s"]),
                costo_usd=float(r["costo_usd"]),
                costo_pago_usd=0.0 if local else int(r["tokens_entrada"]) * tarifas[r["modelo"]][0]
                + int(r["tokens_salida"]) * tarifas[r["modelo"]][1],
                local=local, fraccion_maquina=fraccion,
            )
            datos.setdefault(c.fase, {}).setdefault(c.modelo, []).append(c)
    return datos


def _porcentajes(victorias: dict) -> str:
    return ", ".join(f"{k}={v:.1%}" for k, v in sorted(victorias.items(), key=lambda kv: -kv[1]))


def main() -> None:
    SALIDA.mkdir(parents=True, exist_ok=True)
    datos = cargar()
    datos_otro_juez = cargar("secundario")
    lineas: list[str] = []
    filas_util, filas_mc, filas_bs = [], [], []

    def out(s: str = "") -> None:
        lineas.append(s)
        print(s)

    def escenario(fase: int, nombre: str, celdas: dict, perfil: str, costo: str = "real") -> None:
        ganador, det = elegir(celdas, PERFILES[perfil], costo)
        partes = []
        for k, d in sorted(det.items(), key=lambda kv: -kv[1]["utilidad"]):
            partes.append(f"{k}={d['utilidad']:.3f}{'' if d['elegible'] else ' (no elegible)'}")
            filas_util.append({"fase": fase, "escenario": nombre, "modelo": k,
                               **{c: round(d[c], 4) for c in CRITERIOS},
                               "utilidad": round(d["utilidad"], 4), "elegible": d["elegible"],
                               "ganador": k == ganador})
        out(f"  {nombre:<32} ganador={ganador:<20} {' '.join(partes)}")

    for fase, por_modelo in sorted(datos.items()):
        celdas = {k: metricas_celda(cs) for k, cs in por_modelo.items()}
        out(f"=== Fase {fase}")
        for perfil in PERFILES:
            escenario(fase, perfil, celdas, perfil)
        escenario(fase, "base+costo_con_precio_publico", celdas, "base", "pago")
        escenario(fase, "costo_y_recursos+precio_publico", celdas, "costo_y_recursos", "pago")
        escenario(fase, "base+notas_del_otro_juez",
                  {k: metricas_celda(cs) for k, cs in datos_otro_juez[fase].items()}, "base")
        mc = montecarlo_pesos(celdas, N_MONTECARLO, SEMILLA)
        mc_libre = montecarlo_pesos(celdas, N_MONTECARLO, SEMILLA, exigir_exito=False)
        bs = bootstrap_corridas(por_modelo, PERFILES["base"], N_BOOTSTRAP, SEMILLA)
        out(f"  pesos aleatorios ({N_MONTECARLO}): {_porcentajes(mc)}")
        out(f"  pesos aleatorios SIN regla de elegibilidad: {_porcentajes(mc_libre)}")
        out(f"  bootstrap corridas ({N_BOOTSTRAP}, pesos base): {_porcentajes(bs)}")
        for regla, victorias in ((True, mc), (False, mc_libre)):
            filas_mc += [{"fase": fase, "regla_elegibilidad": regla, "modelo": k, "victorias": round(v, 4)}
                         for k, v in victorias.items()]
        filas_bs += [{"fase": fase, "modelo": k, "victorias": round(v, 4)} for k, v in bs.items()]
        out()

    for nombre, filas in (("utilidad_por_perfil.csv", filas_util), ("montecarlo_pesos.csv", filas_mc),
                          ("bootstrap_corridas.csv", filas_bs)):
        with (SALIDA / nombre).open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(filas[0].keys()))
            w.writeheader()
            w.writerows(filas)
    (SALIDA / "salida.txt").write_text("\n".join(lineas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
