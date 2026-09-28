# Generada por la fase de Testing (Kimi K3, prompt aprobado 5_testing) en la cadena SDD:
# evidence/punto8_sdd/ejecuciones/5_pruebas.json. El modelo la nombró tests/test_auth_lockout.py;
# se ubica en tests/sdd/ junto a la cadena. Único cambio: un "noqa: DTZ001" en la prueba que
# construye a propósito un instante sin zona horaria.
# tests/test_auth_lockout.py
# Verifica REQ-AUT-03 / SPEC-AUT-03. Ejecutar: pytest tests/ -v
from datetime import datetime, timedelta, timezone

import pytest

from auth_lockout import (
    InMemoryAccountStateRepository,
    LoginAttemptProcessor,
    PolicyConfiguration,
    ResultadoAutenticacion,
)

T0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
A = "a@t.com"
B = "b@t.com"


@pytest.fixture()
def proc():
    return LoginAttemptProcessor(InMemoryAccountStateRepository())


def fallar(proc, cuenta, instante):
    return proc.procesar_intento(cuenta, False, instante)


def bloquear(proc, cuenta=A, base=T0):
    for i in range(5):
        r = fallar(proc, cuenta, base + timedelta(minutes=i))
    return r  # resultado del 5.º intento (bloqueo)


# TEST-01 — AC-AUT-03-01: quinto fallo bloquea 15 minutos
def test_01_quinto_fallo_bloquea_cuenta(proc):
    for i in range(4):
        r = fallar(proc, A, T0 + timedelta(minutes=i))
        assert r.resultado_autenticacion == ResultadoAutenticacion.CREDENCIALES_INVALIDAS
        assert r.contador_intentos_fallidos == i + 1
        assert r.cuenta_bloqueada_hasta is None
    r = fallar(proc, A, T0 + timedelta(minutes=4))
    assert r.resultado_autenticacion == ResultadoAutenticacion.CUENTA_BLOQUEADA
    assert r.contador_intentos_fallidos == 5
    assert r.cuenta_bloqueada_hasta == T0 + timedelta(minutes=19)


# TEST-02 — AC-AUT-03-02: contraseña correcta no desbloquea
def test_02_contrasena_correcta_no_desbloquea(proc):
    bloquear(proc)
    r = proc.procesar_intento(A, True, T0 + timedelta(minutes=5))
    assert r.resultado_autenticacion == ResultadoAutenticacion.CUENTA_BLOQUEADA
    assert r.cuenta_bloqueada_hasta == T0 + timedelta(minutes=19)


# TEST-03 — AC-AUT-03-03: exactamente 15 minutos después, login exitoso (borde inclusivo)
def test_03_bloqueo_expira_exactamente_a_los_15_minutos(proc):
    bloquear(proc)
    r = proc.procesar_intento(A, True, T0 + timedelta(minutes=19))
    assert r.resultado_autenticacion == ResultadoAutenticacion.EXITOSO
    assert r.contador_intentos_fallidos == 0
    assert r.cuenta_bloqueada_hasta is None


# TEST-04 — AC-AUT-03-03: más de 15 minutos después
def test_04_login_exitoso_despues_de_expirar_bloqueo(proc):
    bloquear(proc)
    r = proc.procesar_intento(A, True, T0 + timedelta(minutes=30))
    assert r.resultado_autenticacion == ResultadoAutenticacion.EXITOSO
    assert r.contador_intentos_fallidos == 0


# TEST-05 — AC-AUT-03-04: éxito reinicia el contador
def test_05_exito_reinicia_contador(proc):
    for i in range(4):
        fallar(proc, A, T0 + timedelta(minutes=i))
    r = proc.procesar_intento(A, True, T0 + timedelta(minutes=4))
    assert r.resultado_autenticacion == ResultadoAutenticacion.EXITOSO
    assert r.contador_intentos_fallidos == 0
    r = fallar(proc, A, T0 + timedelta(minutes=5))
    assert r.contador_intentos_fallidos == 1  # racha reiniciada, no bloquea


# TEST-06 — AC-AUT-03-05: intento de hace MÁS de 10 min se descarta
def test_06_intento_fuera_de_ventana_se_descarta(proc):
    fallar(proc, A, T0 - timedelta(minutes=11))
    for m in (3, 2, 1):
        fallar(proc, A, T0 - timedelta(minutes=m))
    r = fallar(proc, A, T0)
    assert r.resultado_autenticacion == ResultadoAutenticacion.CREDENCIALES_INVALIDAS
    assert r.contador_intentos_fallidos == 4
    assert r.cuenta_bloqueada_hasta is None


# TEST-07 — D-02: intento de EXACTAMENTE 10 min todavía cuenta
def test_07_intento_de_exactamente_10_minutos_cuenta(proc):
    fallar(proc, A, T0 - timedelta(minutes=10))
    for m in (3, 2, 1):
        fallar(proc, A, T0 - timedelta(minutes=m))
    r = fallar(proc, A, T0)
    assert r.resultado_autenticacion == ResultadoAutenticacion.CUENTA_BLOQUEADA
    assert r.cuenta_bloqueada_hasta == T0 + timedelta(minutes=15)


# TEST-08 — AC-AUT-03-06: el bloqueo es por cuenta
def test_08_bloqueo_no_afecta_a_otras_cuentas(proc):
    bloquear(proc, A)
    r = proc.procesar_intento(B, True, T0 + timedelta(minutes=5))
    assert r.resultado_autenticacion == ResultadoAutenticacion.EXITOSO
    assert r.contador_intentos_fallidos == 0
    r_a = fallar(proc, A, T0 + timedelta(minutes=6))
    assert r_a.resultado_autenticacion == ResultadoAutenticacion.CUENTA_BLOQUEADA


# TEST-09 — AC-AUT-03-07: intentos durante el bloqueo no lo modifican ni cuentan
def test_09_intentos_durante_bloqueo_no_modifican_nada(proc):
    bloquear(proc)
    fin = T0 + timedelta(minutes=19)
    r = fallar(proc, A, T0 + timedelta(minutes=5))
    assert r.resultado_autenticacion == ResultadoAutenticacion.CUENTA_BLOQUEADA
    assert r.cuenta_bloqueada_hasta == fin  # no se extiende
    r = proc.procesar_intento(A, True, fin)
    assert r.resultado_autenticacion == ResultadoAutenticacion.EXITOSO
    r = fallar(proc, A, fin + timedelta(minutes=1))
    assert r.contador_intentos_fallidos == 1  # el intento durante el bloqueo no contó


# TEST-10 — validación de identificador_cuenta
def test_10_identificador_invalido(proc):
    with pytest.raises(ValueError):
        proc.procesar_intento("", True, T0)
    with pytest.raises(ValueError):
        proc.procesar_intento("   ", True, T0)
    with pytest.raises(TypeError):
        proc.procesar_intento(123, True, T0)


# TEST-11 — validación de instante (D-07)
def test_11_instante_invalido(proc):
    with pytest.raises(ValueError):
        proc.procesar_intento(A, True, datetime(2026, 1, 1))  # naive  # noqa: DTZ001 (instante sin zona horaria a propósito: debe rechazarse)
    with pytest.raises(ValueError):
        proc.procesar_intento(A, True, datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2))))
    with pytest.raises(TypeError):
        proc.procesar_intento(A, True, "2026-01-01T00:00:00Z")


# TEST-12 — contrasena_correcta debe ser bool
def test_12_contrasena_correcta_debe_ser_bool(proc):
    with pytest.raises(TypeError):
        proc.procesar_intento(A, 1, T0)


# TEST-13 — serialización como_dict con claves y formato de SPEC-AUT-03
def test_13_como_dict_formato_salidas(proc):
    r = bloquear(proc)
    d = r.como_dict()
    assert d == {
        "resultado_autenticacion": "CUENTA_BLOQUEADA",
        "cuenta_bloqueada_hasta": "2026-01-01T00:19:00Z",
        "contador_intentos_fallidos": 5,
        "mensaje": d["mensaje"],
    }
    assert d["mensaje"]


# TEST-14 — validación de PolicyConfiguration
def test_14_policy_configuration_invalida():
    with pytest.raises(ValueError):
        PolicyConfiguration(max_intentos_fallidos=0)
    with pytest.raises(ValueError):
        PolicyConfiguration(ventana_minutos=True)
    with pytest.raises(ValueError):
        PolicyConfiguration(bloqueo_minutos="15")
    p = PolicyConfiguration()
    assert (p.max_intentos_fallidos, p.ventana_minutos, p.bloqueo_minutos) == (5, 10, 15)


# TEST-15 — un segundo antes del fin del bloqueo aún rechaza
def test_15_un_segundo_antes_del_fin_aun_bloqueado(proc):
    bloquear(proc)
    r = proc.procesar_intento(A, True, T0 + timedelta(minutes=19) - timedelta(seconds=1))
    assert r.resultado_autenticacion == ResultadoAutenticacion.CUENTA_BLOQUEADA


# TEST-16 — RB-7: contador acumulativo por cuenta (sin dimensión dispositivo/IP)
def test_16_contador_acumulativo_por_cuenta(proc):
    for i in range(3):
        fallar(proc, A, T0 + timedelta(minutes=i))
    fallar(proc, A, T0 + timedelta(minutes=3))
    r = fallar(proc, A, T0 + timedelta(minutes=4))
    assert r.resultado_autenticacion == ResultadoAutenticacion.CUENTA_BLOQUEADA
