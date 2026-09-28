"""Quality Gate de la cadena SDD (punto 8) y pruebas de sus herramientas.

La primera prueba hace que una ruptura de la trazabilidad REQ → AC → SPEC →
ARCH → CODE → TEST haga fallar toda la suite (y por lo tanto el commit).
"""

import json
import re
import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from sdd import trazabilidad
from sdd.esquema import Especificacion, huella

RAIZ = Path(__file__).resolve().parent.parent


def test_la_cadena_sdd_del_repositorio_es_conforme():
    _, r = trazabilidad.verificar()
    assert r.errores == []


@pytest.fixture
def copia(tmp_path: Path) -> Path:
    """Copia de la cadena (specs, src, tests/sdd) para romperla sin tocar el repositorio."""
    for parte in ("specs", "src", "tests/sdd"):
        shutil.copytree(RAIZ / parte, tmp_path / parte, ignore=shutil.ignore_patterns("__pycache__"))
    return tmp_path


def _spec(raiz: Path) -> dict:
    return json.loads((raiz / "specs" / "specification.json").read_text(encoding="utf-8"))


def _guardar(raiz: Path, datos: dict) -> None:
    (raiz / "specs" / "specification.json").write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")


def test_cambiar_la_especificacion_deja_el_codigo_sin_aprobar(copia):
    datos = _spec(copia)
    datos["parametros"]["bloqueo_minutos"] = 30
    _guardar(copia, datos)
    _, r = trazabilidad.verificar(copia)
    assert r.errores and all("revisar y volver a sellar" in e for e in r.errores)


def test_un_criterio_sin_prueba_rompe_la_cadena(copia):
    datos = _spec(copia)
    nuevo = dict(datos["criterios_aceptacion"][0], id="AC-AUT-03-99")
    datos["criterios_aceptacion"].append(nuevo)
    _guardar(copia, datos)
    _, r = trazabilidad.verificar(copia)
    assert "AC-AUT-03-99: ninguna prueba lo verifica" in r.errores


def test_codigo_que_declara_un_arch_inexistente(copia):
    modulo = copia / "src" / "auth_lockout" / "politica.py"
    modulo.write_text(modulo.read_text(encoding="utf-8").replace("ARCH-03", "ARCH-09", 1), encoding="utf-8")
    _, r = trazabilidad.verificar(copia)
    assert any("declara ARCH-09, que el contrato no define" in e for e in r.errores)
    assert any("ARCH-03" in e and "no lo declara" in e for e in r.errores)


def test_la_huella_ignora_el_formato_pero_no_el_contenido(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text('{"x": 1, "y": [1, 2]}', encoding="utf-8")
    b.write_text('{\n  "y": [1, 2],\n  "x": 1\n}', encoding="utf-8")
    assert huella(a) == huella(b)
    b.write_text('{"x": 2, "y": [1, 2]}', encoding="utf-8")
    assert huella(a) != huella(b)


def test_el_esquema_rechaza_reglas_sin_criterio_y_numeracion_distinta():
    datos = _spec(RAIZ)
    sin_criterio = json.loads(json.dumps(datos))
    sin_criterio["reglas_negocio"].append({"id": "RB-99", "texto": "x", "origen": "prueba"})
    with pytest.raises(ValidationError, match="RB-99"):
        Especificacion.model_validate(sin_criterio)
    otra_numeracion = json.loads(json.dumps(datos))
    otra_numeracion["id"] = "SPEC-AUT-04"
    with pytest.raises(ValidationError, match="numeración"):
        Especificacion.model_validate(otra_numeracion)


def test_modificar_el_codigo_despues_de_sellar_se_detecta(copia):
    """Ruta A de la demostración: el cambio va directo al código, sin tocar la especificación."""
    modulo = copia / "src" / "auth_lockout" / "politica.py"
    modulo.write_text(modulo.read_text(encoding="utf-8").replace("bloqueo_minutos: int = 15", "bloqueo_minutos: int = 30"),
                      encoding="utf-8")
    _, r = trazabilidad.verificar(copia)
    assert r.errores == [("src/auth_lockout/politica.py: el código cambió después de su aprobación "
                          "(o el sello no lo emitió la herramienta): revisar y volver a sellar")]


def test_un_sello_escrito_a_mano_o_por_un_modelo_no_vale(copia):
    """Visto en la demostración: el modelo de mantenimiento reescribió el sello con la huella nueva."""
    datos = _spec(copia)
    datos["version"], datos["parametros"]["bloqueo_minutos"] = "1.1.0", 30
    _guardar(copia, datos)
    h = huella(copia / "specs" / "specification.json")
    for modulo in (copia / "src" / "auth_lockout").glob("*.py"):
        texto = modulo.read_text(encoding="utf-8")
        modulo.write_text(re.sub(r"^# Spec: .*$", f"# Spec: SPEC-AUT-03 v1.1.0 huella {h}", texto, flags=re.MULTILINE),
                          encoding="utf-8")
    _, r = trazabilidad.verificar(copia)
    assert len(r.errores) == 4 and all("el código cambió después de su aprobación" in e for e in r.errores)


def test_sello_falsificado_en_un_modulo_sin_cambios_no_vale(copia):
    """Caso real de la demostración: el modelo cambió versión y huella de la especificación
    en el sello de __init__.py (sin cambiar su código) y conservó la huella de código vieja."""
    datos = _spec(copia)
    datos["version"], datos["parametros"]["bloqueo_minutos"] = "1.1.0", 30
    _guardar(copia, datos)
    h = huella(copia / "specs" / "specification.json")
    modulo = copia / "src" / "auth_lockout" / "__init__.py"
    texto = modulo.read_text(encoding="utf-8")
    modulo.write_text(re.sub(r"(# Spec: SPEC-AUT-03) v\S+ huella \S+", rf"\1 v1.1.0 huella {h}", texto), encoding="utf-8")
    _, r = trazabilidad.verificar(copia)
    assert any(e.startswith("src/auth_lockout/__init__.py: el código cambió después de su aprobación") for e in r.errores)
