"""Pruebas de conformidad: el código contra la ESPECIFICACIÓN (fuente de verdad).

Los valores no están escritos aquí: se leen de specs/specification.json. Si la
especificación cambia (por ejemplo, el bloqueo pasa a 30 minutos) y el código
no, estas pruebas fallan; si el código cambia sin que cambie la
especificación, también. Cada prueba declara el criterio de aceptación que
verifica (AC-AUT-03-NN) para la matriz de trazabilidad.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from auth_lockout import (
    InMemoryAccountStateRepository,
    LoginAttemptProcessor,
    PolicyConfiguration,
    ResultadoAutenticacion,
)
from sdd.esquema import cargar

SPEC = cargar(Path(__file__).resolve().parents[2] / "specs" / "specification.json")
M = SPEC.parametros.max_intentos_fallidos
V = timedelta(minutes=SPEC.parametros.ventana_minutos)
B = timedelta(minutes=SPEC.parametros.bloqueo_minutos)
T0 = datetime(2026, 9, 27, 12, 0, tzinfo=UTC)
BLOQUEADA, EXITOSO, INVALIDAS = (ResultadoAutenticacion.CUENTA_BLOQUEADA, ResultadoAutenticacion.EXITOSO,
                                 ResultadoAutenticacion.CREDENCIALES_INVALIDAS)


@pytest.fixture
def proc() -> LoginAttemptProcessor:
    # Sin política explícita: se prueban los valores PREDETERMINADOS del código.
    return LoginAttemptProcessor(InMemoryAccountStateRepository())


def _fallar(proc, n: int, inicio: datetime = T0, paso: timedelta = timedelta(seconds=30), cuenta: str = "a@x.co"):
    return [proc.procesar_intento(cuenta, False, inicio + i * paso) for i in range(n)]


def test_parametros_predeterminados_iguales_a_la_especificacion():
    """SPEC-AUT-03 parametros (R5): el código usa los valores de la especificación."""
    p = PolicyConfiguration()
    assert (p.max_intentos_fallidos, p.ventana_minutos, p.bloqueo_minutos) == (
        SPEC.parametros.max_intentos_fallidos, SPEC.parametros.ventana_minutos, SPEC.parametros.bloqueo_minutos)


def test_ac01_el_intento_M_dentro_de_la_ventana_bloquea_durante_B(proc):
    """AC-AUT-03-01"""
    previos = _fallar(proc, M - 1)
    assert all(r.resultado_autenticacion == INVALIDAS for r in previos)
    ultimo = T0 + (M - 1) * timedelta(seconds=30)
    r = proc.procesar_intento("a@x.co", False, ultimo)
    assert r.resultado_autenticacion == BLOQUEADA
    assert r.cuenta_bloqueada_hasta == ultimo + B
    assert r.como_dict()["cuenta_bloqueada_hasta"] == (ultimo + B).strftime("%Y-%m-%dT%H:%M:%SZ")


def test_ac02_durante_el_bloqueo_se_rechaza_la_contrasena_correcta(proc):
    """AC-AUT-03-02"""
    _fallar(proc, M)
    fin = T0 + (M - 1) * timedelta(seconds=30) + B
    r = proc.procesar_intento("a@x.co", True, fin - timedelta(seconds=1))
    assert r.resultado_autenticacion == BLOQUEADA and r.cuenta_bloqueada_hasta == fin
    assert r.contador_intentos_fallidos == M  # decisión D-10


def test_ac03_al_cumplirse_B_exactos_el_ingreso_es_exitoso_y_el_contador_vuelve_a_0(proc):
    """AC-AUT-03-03 (límite exacto: decisión D-03)"""
    _fallar(proc, M)
    fin = T0 + (M - 1) * timedelta(seconds=30) + B
    r = proc.procesar_intento("a@x.co", True, fin)
    assert r.resultado_autenticacion == EXITOSO and r.contador_intentos_fallidos == 0
    # Contador realmente en 0: harían falta M fallos nuevos para volver a bloquear.
    assert _fallar(proc, M - 1, inicio=fin + timedelta(seconds=1))[-1].resultado_autenticacion == INVALIDAS


def test_ac04_un_exito_con_M_menos_1_fallos_reinicia_el_contador(proc):
    """AC-AUT-03-04"""
    _fallar(proc, M - 1)
    r = proc.procesar_intento("a@x.co", True, T0 + timedelta(minutes=1))
    assert r.resultado_autenticacion == EXITOSO and r.contador_intentos_fallidos == 0
    siguiente = proc.procesar_intento("a@x.co", False, T0 + timedelta(minutes=2))
    assert siguiente.resultado_autenticacion == INVALIDAS and siguiente.contador_intentos_fallidos == 1


def test_ac05_un_fallo_de_hace_mas_de_V_sale_de_la_ventana(proc):
    """AC-AUT-03-05"""
    proc.procesar_intento("a@x.co", False, T0)                      # el más antiguo
    _fallar(proc, M - 2, inicio=T0 + V - timedelta(minutes=1))      # M-2 recientes
    r = proc.procesar_intento("a@x.co", False, T0 + V + timedelta(seconds=1))
    assert r.resultado_autenticacion == INVALIDAS and r.contador_intentos_fallidos == M - 1


def test_ac05_un_fallo_de_exactamente_V_todavia_cuenta(proc):
    """AC-AUT-03-05 (límite exacto: decisión D-02)"""
    proc.procesar_intento("a@x.co", False, T0)
    _fallar(proc, M - 2, inicio=T0 + V - timedelta(minutes=1))
    assert proc.procesar_intento("a@x.co", False, T0 + V).resultado_autenticacion == BLOQUEADA


def test_ac06_las_cuentas_son_independientes(proc):
    """AC-AUT-03-06"""
    _fallar(proc, M, cuenta="a@x.co")
    r = proc.procesar_intento("b@x.co", True, T0 + timedelta(minutes=5))
    assert r.resultado_autenticacion == EXITOSO
    assert proc.procesar_intento("a@x.co", True, T0 + timedelta(minutes=5)).resultado_autenticacion == BLOQUEADA


def test_ac07_los_intentos_durante_el_bloqueo_no_lo_modifican(proc):
    """AC-AUT-03-07 (decisión D-08)"""
    _fallar(proc, M)
    fin = T0 + (M - 1) * timedelta(seconds=30) + B
    for k in range(M + 2):
        r = proc.procesar_intento("a@x.co", False, T0 + timedelta(minutes=5, seconds=k))
        assert r.resultado_autenticacion == BLOQUEADA and r.cuenta_bloqueada_hasta == fin
    # Al vencer, esos intentos no cuentan: un fallo deja el contador en 1, no bloquea.
    r = proc.procesar_intento("a@x.co", False, fin)
    assert r.resultado_autenticacion == INVALIDAS and r.contador_intentos_fallidos == 1
