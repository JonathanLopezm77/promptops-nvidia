"""Función objetivo del punto 7 (benchmarks/seleccion.py)."""

import random

import pytest

from benchmarks.seleccion import (
    PERFILES,
    Corrida,
    bootstrap_corridas,
    criterios_fase,
    elegir,
    metricas_celda,
    pesos_aleatorios,
)


def _c(modelo="m", qg=80.0, cumple=True, dur=10.0, pago=0.01, local=False, fraccion=0.0,
       violaciones=0, supuestos=0, schema=True) -> Corrida:
    return Corrida(fase=1, modelo=modelo, qg=qg, cumple=cumple, schema_ok=schema, violaciones=violaciones,
                   supuestos=supuestos, duracion_s=dur, costo_usd=0.0,
                   costo_pago_usd=0.0 if local else pago, local=local, fraccion_maquina=fraccion)


def test_calidad_descuenta_la_variabilidad_entre_corridas():
    estable = metricas_celda([_c(qg=80), _c(qg=80), _c(qg=80)])
    variable = metricas_celda([_c(qg=70), _c(qg=80), _c(qg=90)])
    crit = criterios_fase({"estable": estable, "variable": variable})
    assert crit["estable"]["calidad"] == pytest.approx(0.80)
    assert crit["variable"]["calidad"] == pytest.approx(0.70)  # media 80 - DE 10


def test_cumplimiento_combina_exito_violaciones_supuestos_y_schema():
    m = metricas_celda([_c(cumple=True), _c(cumple=False, supuestos=1), _c(cumple=True, violaciones=2)])
    crit = criterios_fase({"a": m})["a"]
    # 0.5 * 2/3 + 0.5 * media(1 - 1/3, 1 - 1/3, 1)
    assert crit["cumplimiento"] == pytest.approx(0.5 * 2 / 3 + 0.5 * (2 / 3 + 2 / 3 + 1) / 3)


def test_latencia_y_costo_son_relativos_al_mejor_de_la_fase():
    celdas = {"rapido": metricas_celda([_c(dur=10, pago=0.04)]),
              "lento": metricas_celda([_c(dur=40, pago=0.01)]),
              "local": metricas_celda([_c(dur=20, local=True, fraccion=0.6)])}
    real = criterios_fase(celdas)
    assert real["rapido"]["latencia"] == 1 and real["lento"]["latencia"] == pytest.approx(0.25)
    assert all(v["costo"] == 1 for v in real.values())  # todo cuesta 0 USD
    assert real["local"]["recursos"] == pytest.approx(0.4) and real["rapido"]["recursos"] == 1
    pago = criterios_fase(celdas, costo="pago")
    assert pago["lento"]["costo"] == 1 and pago["rapido"]["costo"] == pytest.approx(0.25)
    assert pago["local"]["costo"] == 1  # el local no paga por token


def test_un_modelo_que_falla_la_mayoria_de_corridas_no_puede_ganar():
    celdas = {"rapido_pero_falla": metricas_celda([_c(cumple=False, dur=1), _c(cumple=False, dur=1), _c(dur=1)]),
              "lento_y_correcto": metricas_celda([_c(dur=100)] * 3)}
    ganador, det = elegir(celdas, PERFILES["interactivo"])
    assert ganador == "lento_y_correcto"
    assert det["rapido_pero_falla"]["utilidad"] > det["lento_y_correcto"]["utilidad"]
    assert elegir(celdas, PERFILES["interactivo"], exigir_exito=False)[0] == "rapido_pero_falla"


def test_sin_modelos_elegibles_no_hay_ganador():
    assert elegir({"a": metricas_celda([_c(cumple=False)] * 3)}, PERFILES["base"])[0] is None


def test_perfiles_y_pesos_aleatorios_suman_uno():
    for pesos in PERFILES.values():
        assert sum(pesos.values()) == pytest.approx(1)
    rng = random.Random(1)
    for _ in range(50):
        p = pesos_aleatorios(rng)
        assert sum(p.values()) == pytest.approx(1) and min(p.values()) >= 0


def test_bootstrap_es_reproducible_y_suma_uno():
    por_modelo = {"a": [_c(qg=90), _c(qg=60), _c(qg=85)], "b": [_c(qg=80), _c(qg=82), _c(qg=78)]}
    r1 = bootstrap_corridas(por_modelo, PERFILES["base"], 500, semilla=7)
    assert r1 == bootstrap_corridas(por_modelo, PERFILES["base"], 500, semilla=7)
    assert sum(r1.values()) == pytest.approx(1)
