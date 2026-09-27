"""Tests de benchmarks/calificadores.py con salidas simuladas. Si un
calificador estuviera mal, los resultados del benchmark serían falsos."""

from pathlib import Path

import pytest

from benchmarks.calificadores import (
    analisis_estatico,
    calificar_fase1,
    calificar_fase3,
    calificar_fase4,
    extraer_archivos,
)

RAIZ = Path(__file__).resolve().parent.parent
ENTRADA_F1 = {"necesidad": "lista de deseos y aviso rápido; lista no demasiado grande",
              "contexto": "catálogo de 20000 productos; invitados y registrados; correo existente"}
IDS_SPEC = ["SPEC-01", "SPEC-02", "SPEC-03", "SPEC-04", "SPEC-05", "SPEC-06"]

F1_BUENA = """## Requisitos funcionales
RF-01: El sistema deberá permitir a un cliente registrado agregar un producto a su lista de deseos.
Criterio de aceptación: El producto aparece en la lista y se muestra "Producto agregado".
RF-02: El sistema deberá enviar un correo al cliente cuando baje el precio de un producto de su lista.
Criterio de aceptación: Al registrar un precio menor se envía un correo con el precio anterior y el nuevo.

## Requisitos no funcionales
Sin elementos

## Información faltante
- ¿Cuál es el tiempo máximo aceptable entre el cambio de precio y el aviso?
- ¿Cuál es el número máximo de productos que puede tener una lista?

## Aclaraciones sobre información ambigua
- ¿Los clientes invitados pueden usar la lista de deseos o solo los registrados?"""

F1_MALA = """Aquí están los requisitos:
## Requisitos funcionales
RF-01: El sistema deberá gestionar la lista de deseos de forma rápida.
RF-03: El sistema deberá avisar en menos de 5 minutos, con un máximo de 100 productos.
Criterio de aceptación: El 95% de los avisos llega a tiempo.

## Información faltante
Sin elementos"""


# --- Fase 1 ----------------------------------------------------------------------


def test_fase1_buena_cumple_y_puntua_segun_las_reglas():
    r = calificar_fase1(F1_BUENA, ENTRADA_F1, juez_score=80)
    assert r["schema_ok"] and r["cumple_tarea"]
    assert r["violaciones"] == [] and r["supuestos_no_sustentados"] == []
    assert r["componentes"] == {"quality_score": 40.0, "verificabilidad": 20.0, "trazabilidad": 15.0, "no_inventar": 15}
    assert r["puntaje"] == 90.0
    assert sorted(r["detalle"]["huecos_preguntados"]) == ["clientes invitados", "plazo del aviso", "tamaño de la lista"]


def test_fase1_mala_detecta_cada_problema():
    r = calificar_fase1(F1_MALA, ENTRADA_F1, juez_score=40)
    assert not r["schema_ok"] and not r["cumple_tarea"]
    assert r["supuestos_no_sustentados"] == ["5", "100", "95"]
    assert r["componentes"]["no_inventar"] == 0
    assert any("gestionar" in v for v in r["violaciones"]) and any("rápid" in v for v in r["violaciones"])
    assert r["detalle"]["verificabilidad"] == 0.5  # RF-01 sin criterio
    assert r["detalle"]["trazabilidad"] == 0.5  # RF-03 debería ser RF-02
    assert r["detalle"]["huecos_preguntados"] == []


def test_fase1_sin_juez_no_inventa_un_puntaje():
    r = calificar_fase1(F1_BUENA, ENTRADA_F1, juez_score=None)
    assert r["puntaje"] is None and r["componentes"]["quality_score"] is None


@pytest.mark.parametrize(("pregunta", "esperado"), [
    ("- ¿Cuál es el tiempo máximo del aviso?", ["plazo del aviso"]),  # "máximo" no es tamaño
    ("- ¿Qué pasa ahora con los precios antiguos?", []),  # "ahora" no es "hora"
    ("- ¿Cuántos productos puede guardar cada cliente?", ["tamaño de la lista"]),
    ("- ¿Se avisa ante cualquier baja o solo desde un 10 %?", ["umbral de baja"]),
])
def test_fase1_deteccion_de_huecos_es_precisa(pregunta, esperado):
    salida = f"## Requisitos funcionales\nRF-01: El sistema deberá x.\nCriterio de aceptación: y.\n## Información faltante\n{pregunta}"
    assert calificar_fase1(salida, ENTRADA_F1, 50)["detalle"]["huecos_preguntados"] == esperado


# --- Fase 3 ----------------------------------------------------------------------


def _doc_f3(extra=""):
    return f"""## 1. Resumen de la arquitectura
Monolito modular.
## 2. Componentes
- ARCH-01 Lista de deseos: cubre SPEC-01, SPEC-02, SPEC-03, SPEC-06.
- ARCH-02 Detector de bajas: cubre SPEC-04.
- ARCH-03 Notificador: cubre SPEC-05.
## 3. Contratos de interfaces
POST /wishlist ...
## 4. Decisiones de diseño
Se descarta Redis por R2.
## 5. Verificación de restricciones
R1 a R6 cumplidas.
## 6. Diagrama de arquitectura en Mermaid
```mermaid
flowchart LR
  ARCH01["ARCH-01"] --> ARCH02["ARCH-02"] --> ARCH03["ARCH-03"]
```
## 7. Supuestos y riesgos
Ninguno.
## 8. Brechas de cobertura
Ninguna.
## 9. Lista de comprobación final
- [x] Todos los IDs ARCH son secuenciales.
{extra}"""


def _juez(violadas=(), funcionalidades=(), puntaje=8):
    return {
        "restricciones": [{"id": f"R{i}", "cumple": f"R{i}" not in violadas, "evidencia": "e"} for i in range(1, 7)],
        "specs": [{"id": s, "cubierto": True, "evidencia": "e"} for s in IDS_SPEC],
        "funcionalidades_inventadas": list(funcionalidades), "datos_inventados": [],
        "contratos_completos": True, "puntaje_revision": puntaje, "justificacion": "j",
    }


def test_fase3_buena_cumple_con_puntaje_maximo_de_estructura():
    r = calificar_fase3(_doc_f3(), IDS_SPEC, _juez())
    assert r["schema_ok"] and r["cumple_tarea"]
    assert r["componentes"] == {"cobertura_spec": 25.0, "estructura": 15.0, "identificadores": 10,
                                "restricciones": 20, "revision": 24}
    assert r["puntaje"] == 94.0
    assert r["violaciones"] == [] and r["supuestos_no_sustentados"] == []


def test_fase3_detecta_afirmaciones_de_verificacion_no_realizada():
    r = calificar_fase3(_doc_f3("- [x] Se verificó el diagrama con un linter de Mermaid."), IDS_SPEC, _juez())
    assert len(r["detalle"]["afirma_verificacion_no_realizada"]) == 1
    assert r["supuestos_no_sustentados"]


def test_fase3_violaciones_del_juez_y_codigo_de_implementacion():
    doc = _doc_f3("```python\ndef f():\n    pass\n```")
    r = calificar_fase3(doc, IDS_SPEC, _juez(violadas=("R2",), funcionalidades=("SMS",)))
    assert not r["schema_ok"] and not r["cumple_tarea"]
    assert r["componentes"]["restricciones"] == 13
    assert any(v.startswith("R2") for v in r["violaciones"]) and any("implementación" in v for v in r["violaciones"])
    assert "funcionalidad inventada: SMS" in r["supuestos_no_sustentados"]


def test_fase3_ids_no_secuenciales_y_spec_faltante():
    doc = _doc_f3().replace("ARCH-03", "ARCH-05").replace("ARCH03", "ARCH05").replace("SPEC-06", "")
    r = calificar_fase3(doc, IDS_SPEC, _juez())
    assert not r["detalle"]["arch_secuenciales"]
    assert r["detalle"]["specs_cubiertos"] == IDS_SPEC[:5]
    assert r["componentes"]["cobertura_spec"] == pytest.approx(20.83, abs=0.01)


# --- Fase 4 ----------------------------------------------------------------------

REFERENCIA = (RAIZ / "benchmarks" / "referencia" / "wishlist_service.py").read_text(encoding="utf-8")


def _salida(codigo, lenguaje="python"):
    return f"```{lenguaje}\n{codigo}\n```"


def test_fase4_la_referencia_saca_100():
    r = calificar_fase4(_salida(REFERENCIA))
    assert r["detalle"]["tests_pasadas"] == r["detalle"]["tests_total"] == 34
    assert r["detalle"]["avisos_lint"] == []
    assert r["puntaje"] == 100.0 and r["cumple_tarea"] and r["schema_ok"]


def test_fase4_un_error_sutil_baja_el_puntaje():
    mutante = REFERENCIA.replace("ROUND_HALF_UP", "ROUND_HALF_EVEN")  # redondeo bancario
    r = calificar_fase4(_salida(mutante))
    assert r["detalle"]["tests_pasadas"] == 33 and not r["cumple_tarea"]
    assert r["puntaje"] < 100


def test_fase4_no_ejecuta_codigo_con_acceso_a_disco():
    r = calificar_fase4(_salida("# File: wishlist_service.py\nimport os\nos.remove('x')\n"))
    assert r["puntaje"] == 0.0 and r["detalle"]["ejecutado"] is False
    assert any("red/disco" in v for v in r["violaciones"])


def test_fase4_threading_no_se_bloquea():
    assert analisis_estatico("import threading\nLOCK = threading.Lock()\n")["peligrosos"] == []


def test_fase4_ejecucion_dinamica_se_bloquea():
    assert analisis_estatico("x = __import__('decimal')\n")["peligrosos"] == ["__import__"]


def test_fase4_sin_modulo_o_sin_sintaxis_valida():
    assert calificar_fase4("no hay código")["detalle"]["error"].startswith("no se encontró")
    r = calificar_fase4(_salida("# File: wishlist_service.py\ndef roto(:\n"))
    assert r["puntaje"] == 0.0 and r["detalle"]["compila"] is False


def test_fase4_pruebas_incluidas_y_encabezado_faltante():
    sin_encabezado = REFERENCIA.replace("# File: wishlist_service.py\n", "")
    salida = _salida(sin_encabezado) + "\n" + _salida("# File: test_wishlist.py\ndef test_x():\n    assert True\n")
    r = calificar_fase4(salida)
    assert any("pruebas" in v for v in r["violaciones"])
    # Sin encabezado pero es el único bloque de implementación: se califica igual.
    assert r["detalle"]["tests_pasadas"] == 34
    assert r["detalle"]["encabezado_file"] is False and r["componentes"]["formato"] == 10


def test_fase4_codigo_sin_bloques_marcados_se_califica():
    # Caso real del ensayo: nemotron devolvió el código sin ``` y empezando
    # directamente por "# File: wishlist_service.py"; se había calificado con 0.
    r = calificar_fase4(REFERENCIA)
    assert r["detalle"]["tests_pasadas"] == 34 and r["detalle"]["encabezado_file"] is True
    assert r["puntaje"] == 100.0


def test_fase4_ruta_en_la_linea_anterior_al_bloque():
    sin_encabezado = REFERENCIA.replace("# File: wishlist_service.py\n", "")
    r = calificar_fase4(f"**wishlist_service.py**\n```python\n{sin_encabezado}\n```")
    assert r["detalle"]["encabezado_file"] is True and r["detalle"]["tests_pasadas"] == 34


def test_extraer_archivos_sin_marcas_divide_por_file():
    salida = "# File: a.py\nx = 1\n# File: wishlist_service.py\ny = 2\n"
    assert [(a[0], a[1], a[2]) for a in extraer_archivos(salida)] == [
        ("a.py", "python", "# File: a.py\nx = 1"), ("wishlist_service.py", "python", "# File: wishlist_service.py\ny = 2")]


def test_extraer_archivos_lee_la_ruta_declarada():
    archivos = extraer_archivos("```python\n# File: src/wishlist_service.py\nx = 1\n```\n```ts\n// File: a.ts\n```")
    assert [(a[0], a[1]) for a in archivos] == [("src/wishlist_service.py", "python"), ("a.ts", "ts")]
