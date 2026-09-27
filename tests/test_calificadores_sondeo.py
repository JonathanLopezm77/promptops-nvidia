"""Calificadores del sondeo de las fases 2, 5, 6 y 7 (benchmarks/calificadores_sondeo.py)."""

import json
from pathlib import Path

import pytest

from benchmarks.calificadores_sondeo import (
    aplicar_cambio,
    calificar_fase2,
    calificar_fase5,
    calificar_fase6,
    calificar_fase7,
)

RAIZ = Path(__file__).resolve().parent.parent
CASOS = RAIZ / "benchmarks" / "casos_sondeo"


def _caso(nombre: str) -> dict:
    return json.loads((CASOS / nombre).read_text(encoding="utf-8"))


# --- Fase 2 -----------------------------------------------------------------

def _spec(n: str, deps=()) -> dict:
    return {"spec_id": f"SPEC-{n}", "requisito_origen": f"REQ-{n}", "descripcion": "d",
            "entradas": [], "salidas": [], "reglas_negocio": ["RB-1: r"],
            "dependencias": [{"requisito_referenciado": d, "elementos_heredados": "x"} for d in deps],
            "criterios_aceptacion": ["Dado a, Cuando b, Entonces c", "Dado x, Cuando y, Entonces error"]}


def _f2_perfecta() -> dict:
    ids = ["01", "02", "03", "05", "06", "07", "08", "10"]
    return {"especificaciones": [_spec(n, ("REQ-02",) if n == "06" else ()) for n in ids],
            "inconsistencias": [{"requisitos": ["REQ-07"], "descripcion": "REQ-09 no existe"},
                                {"requisitos": ["REQ-03", "REQ-08"], "descripcion": "límite contradictorio"}],
            "alertas_cumplimiento": [{"requisito": "REQ-10", "tipo": "legal", "descripcion": "d", "recomendacion": "r"}],
            "supuestos": []}


def test_fase2_salida_perfecta_obtiene_100():
    r = calificar_fase2(json.dumps(_f2_perfecta()), _caso("fase2_especificacion.json")["esperado"])
    assert r["puntaje"] == 100 and r["cumple_tarea"], r["chequeos"]


def test_fase2_renumerar_y_omitir_hallazgos_se_penaliza():
    datos = _f2_perfecta()
    datos["especificaciones"] = [_spec(f"{i:02d}") for i in range(1, 9)]  # cierra los huecos
    datos["inconsistencias"], datos["alertas_cumplimiento"] = [], []
    r = calificar_fase2(json.dumps(datos), _caso("fase2_especificacion.json")["esperado"])
    fallidos = {k for k, v in r["chequeos"].items() if not v}
    assert "numeración exacta (respeta huecos, sin SPEC inventados)" in fallidos
    assert "alerta legal REQ-10" in fallidos and not r["cumple_tarea"]


def test_fase2_json_invalido_es_cero():
    assert calificar_fase2("no es json", _caso("fase2_especificacion.json")["esperado"])["puntaje"] == 0


# --- Fase 5 -----------------------------------------------------------------

def test_fase5_la_suite_oculta_como_suite_generada_es_perfecta():
    suite = (RAIZ / "benchmarks" / "pruebas_ocultas" / "test_wishlist_service.py").read_text(encoding="utf-8")
    salida = ("A. casos TEST-01\n```python\n" + suite + "\n```\nC. Matriz de cobertura\n| SPEC-01 | TEST-01 |\n"
              "D. Reporte de defectos\nDEF-01: el umbral usa > en lugar de >=.\n"
              "DEF-02: list_items devuelve la lista interna, no una copia.\n")
    r = calificar_fase5(salida, _caso("fase5_testing.json")["esperado"])
    d = r["detalle"]
    assert d["tests_validos_en_referencia"] == d["tests_total"] == 34
    assert all(d["mutantes_detectados"].values()) and all(d["defectos_plantados_detectados"].values())
    assert d["cobertura_pct"] == 100 and all(d["defectos_reportados"].values())
    assert r["cumple_tarea"]


def test_fase5_suite_debil_no_detecta_defectos():
    suite = ("from decimal import Decimal\nfrom datetime import datetime\nimport wishlist_service as w\n\n"
             "def test_01_agrega():\n    s = w.WishlistService()\n"
             "    assert s.add_item('c', 'p', Decimal('1'), datetime(2026, 1, 1)).product_id == 'p'\n")
    r = calificar_fase5(f"```python\n{suite}```", _caso("fase5_testing.json")["esperado"])
    assert r["detalle"]["tests_validos_en_referencia"] == 1
    assert not any(r["detalle"]["defectos_plantados_detectados"].values()) and not r["cumple_tarea"]


def test_fase5_sin_suite_es_cero():
    assert calificar_fase5("solo texto", _caso("fase5_testing.json")["esperado"])["puntaje"] == 0


# --- Fase 6 -----------------------------------------------------------------

_F6_BUENA = """Supuestos
- Supuesto: x. Justificación: y. Cómo corregirlo: z.

Archivo: .github/workflows/ci.yml
```yaml
name: ci
on: {push: {branches: [main]}}
jobs:
  test:
    runs-on: ubuntu-22.04
    steps:
      - uses: actions/checkout@v4
```

Archivo: Dockerfile
```dockerfile
FROM python:3.12.2-slim AS build
RUN pip install -r requirements.txt
FROM python:3.12.2-slim
USER app
```

Archivo: render.yaml
```yaml
services:
  - type: web
    name: promptops
```

Verificación: curl -f https://app.onrender.com/api/runs

Rollback
1. En Render, elegir el deploy anterior.
2. Pulsar Rollback.

| Variable | Propósito |
|---|---|
| DATABASE_URL | conexión |
| NVIDIA_API_KEY | clave |
"""


def test_fase6_salida_completa_cumple_todo():
    r = calificar_fase6(_F6_BUENA, _caso("fase6_deployment.json")["esperado"])
    assert r["cumple_tarea"], {k: v for k, v in r["chequeos"].items() if not v}


@pytest.mark.parametrize("cambio, chequeo", [
    (("FROM python:3.12.2-slim\nUSER", "FROM python:latest\nUSER"), "imágenes base con versión fija (sin latest)"),
    (("USER app", "USER root"), "contenedor sin root (USER)"),
    (("| NVIDIA_API_KEY | clave |", "| NVIDIA_API_KEY | clave |\nNVIDIA_API_KEY=nvapi-abcdefghijklmnop123"),
     "sin secretos en claro"),
    (("  test:\n", "  test:\n   mal: [\n"), "YAML sintácticamente válido"),
])
def test_fase6_detecta_cada_incumplimiento(cambio, chequeo):
    r = calificar_fase6(_F6_BUENA.replace(*cambio), _caso("fase6_deployment.json")["esperado"])
    assert not r["chequeos"][chequeo] and not r["cumple_tarea"]


def test_fase6_no_confunde_referencias_a_secretos_con_secretos():
    texto = _F6_BUENA + ("\nDATABASE_URL=postgresql://usuario:${DB_PASSWORD}@host/db\ntoken: ${{ secrets.RENDER_TOKEN }}\n"
                         "API_KEY: your_api_key\nNVIDIA_API_KEY=<tu_clave_de_nvidia>\n"
                         # casos reales del sondeo: valores falsos para un smoke test y nombres de secretos
                         '-e DATABASE_URL="postgresql://invalid:invalid@localhost:1/invalid" '
                         '-e NVIDIA_API_KEY="ci-placeholder"\n'
                         "      - key: NVIDIA_API_KEY\n        fromSecret: nvidia-api-key\n")
    assert calificar_fase6(texto, _caso("fase6_deployment.json")["esperado"])["chequeos"]["sin secretos en claro"]


# --- Fase 7 -----------------------------------------------------------------

ORIGINAL = (CASOS / "fase7_codigo_actual.py").read_text(encoding="utf-8")
_SECCIONES = ("1. Diagnóstico / causa raíz\n2. Cambio propuesto\n{cambio}\n3. Impacto\n4. Pruebas de regresión\n"
              "5. Deuda técnica\n6. Trazabilidad\n| SPEC-03 | SPEC | cumplido |\n| ARCH-01 | ARCH | sin cambios |\n"
              "7. Supuestos y dudas\n")
_DIFF = """```diff
     def list_items(self, customer_id: str) -> list[WishlistItem]:
-        # La lista interna conserva el orden de inserción, que coincide con el orden por fecha.
-        return list(self._listas.get(customer_id, []))
+        return sorted(self._listas.get(customer_id, []), key=lambda item: item.added_at)
```"""


def test_fase7_diff_correcto_pasa_las_34_pruebas():
    r = calificar_fase7(_SECCIONES.format(cambio=_DIFF), ORIGINAL, _caso("fase7_mantenimiento.json")["esperado"])
    assert r["detalle"]["funciones_cambiadas"] == ["list_items"]
    assert r["detalle"]["tests_pasadas"] == 34 and r["cumple_tarea"] and r["puntaje"] == 100


def test_fase7_antes_y_despues_usa_el_despues():
    cambio = ("Antes:\n```python\n    def list_items(self, customer_id):\n        return list(self._listas.get(customer_id, []))\n```\n"
              "Después:\n```python\n    def list_items(self, customer_id):\n"
              "        return sorted(self._listas.get(customer_id, []), key=lambda i: i.added_at)\n```")
    codigo, cambios = aplicar_cambio(ORIGINAL, cambio)
    assert cambios == ["list_items"] and "sorted(" in codigo


def test_fase7_ordenar_sin_estabilidad_rompe_el_desempate():
    malo = _DIFF.replace("key=lambda item: item.added_at)", "key=lambda item: (item.added_at, item.product_id))")
    r = calificar_fase7(_SECCIONES.format(cambio=malo), ORIGINAL, _caso("fase7_mantenimiento.json")["esperado"])
    assert "test_spec03_empate_conserva_orden_de_insercion" in r["detalle"]["tests_fallidas"]
    assert not r["cumple_tarea"]


def test_fase7_inventar_ids_req_se_penaliza():
    texto = _SECCIONES.format(cambio=_DIFF) + "| REQ-07 | REQ | cumplido |\n"
    r = calificar_fase7(texto, ORIGINAL, _caso("fase7_mantenimiento.json")["esperado"])
    assert r["detalle"]["ids_req_inventados"] == ["REQ-07"] and r["componentes"]["trazabilidad"] == 7.5


@pytest.mark.parametrize("secreto", [
    "NVIDIA_API_KEY=nvapi-Xy12abcdEFGH5678",
    "DATABASE_URL=postgresql://admin:S3cr3tP4ss@db.render.com/app",
    "token: ghp_1a2b3c4d5e6f7g8h9i0jKLMN",
])
def test_fase6_detecta_secretos_reales(secreto):
    r = calificar_fase6(_F6_BUENA + "\n" + secreto + "\n", _caso("fase6_deployment.json")["esperado"])
    assert not r["chequeos"]["sin secretos en claro"]
