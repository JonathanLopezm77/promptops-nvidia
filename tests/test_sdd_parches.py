"""Aplicador de los diffs que proponen los modelos (sdd/parches.py), con los
formatos que usaron de verdad en la demostración del punto 8."""

from pathlib import Path

import pytest

from sdd.parches import aplicar

POLITICA = '''# File: src/auth_lockout/politica.py
"""Parámetros."""


class PolicyConfiguration:
    """Docstring original del archivo."""

    max_intentos_fallidos: int = 5
    ventana_minutos: int = 10
    bloqueo_minutos: int = 15

    def validar(self) -> None:
        for nombre in ("max_intentos_fallidos", "bloqueo_minutos"):
            pass
'''


@pytest.fixture
def carpeta(tmp_path: Path) -> Path:
    (tmp_path / "politica.py").write_text(POLITICA, encoding="utf-8")
    (tmp_path / "otro.py").write_text("x = 1\n", encoding="utf-8")
    return tmp_path


def test_hunk_con_dos_ediciones_separadas_y_sin_numeros_de_linea(carpeta):
    salida = ("```diff\n--- a/src/auth_lockout/politica.py\n+++ b/src/auth_lockout/politica.py\n@@\n"
              "     ventana_minutos: int = 10\n-    bloqueo_minutos: int = 15\n+    bloqueo_minutos: int = 30\n \n"
              "     def validar(self) -> None:\n-        for nombre in (\"max_intentos_fallidos\", \"bloqueo_minutos\"):\n"
              "+        for nombre in (\"max_intentos_fallidos\", \"bloqueo_minutos\"):\n```")
    assert aplicar(salida, carpeta) == {"aplicados": ["politica.py:1"], "no_aplicados": []}
    assert "bloqueo_minutos: int = 30" in (carpeta / "politica.py").read_text(encoding="utf-8")


def test_archivo_entero_con_contexto_que_no_calza_aplica_solo_el_cambio(carpeta):
    """El modelo reescribió el archivo de memoria (docstring distinto): se aplica el
    cambio con menos contexto, solo porque la línea a reemplazar es única."""
    salida = ("```diff\n# File: src/auth_lockout/politica.py\n\nclass PolicyConfiguration:\n"
              "    \"\"\"Docstring DISTINTO escrito por el modelo.\"\"\"\n\n    max_intentos_fallidos: int = 5\n"
              "    ventana_minutos: int = 10\n-    bloqueo_minutos: int = 15\n+    bloqueo_minutos: int = 30\n```")
    assert aplicar(salida, carpeta)["aplicados"] == ["politica.py:1"]
    texto = (carpeta / "politica.py").read_text(encoding="utf-8")
    assert "bloqueo_minutos: int = 30" in texto and "Docstring original" in texto


def test_varios_archivos_en_un_bloque(carpeta):
    salida = ("```diff\n--- a/politica.py\n+++ b/politica.py\n@@\n-    bloqueo_minutos: int = 15\n"
              "+    bloqueo_minutos: int = 30\n--- a/otro.py\n+++ b/otro.py\n@@\n-x = 1\n+x = 2\n```")
    assert aplicar(salida, carpeta) == {"aplicados": ["politica.py:1", "otro.py:1"], "no_aplicados": []}


def test_si_el_cambio_no_calza_o_es_ambiguo_no_se_adivina(carpeta):
    no_existe = "```diff\n--- a/politica.py\n+++ b/politica.py\n@@\n-    reintentos: int = 3\n+    reintentos: int = 4\n```"
    ambiguo = "```diff\n--- a/politica.py\n+++ b/politica.py\n@@\n-            pass\n+            continue\n```"
    (carpeta / "politica.py").write_text(POLITICA + "        for x in ():\n            pass\n", encoding="utf-8")
    antes = (carpeta / "politica.py").read_text(encoding="utf-8")
    assert aplicar(no_existe, carpeta)["no_aplicados"] == ["politica.py:1"]
    assert aplicar(ambiguo, carpeta)["no_aplicados"] == ["politica.py:1"]
    assert (carpeta / "politica.py").read_text(encoding="utf-8") == antes
