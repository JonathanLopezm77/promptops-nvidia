"""Calificadores del sondeo de las fases 2, 5, 6 y 7 (punto 7).

El sondeo NO es parte de las 27 ejecuciones del benchmark: es 1 corrida por
modelo y fase para apoyar la selección argumentada con evidencia objetiva.
Cada calificador implementa el Quality Gate que el enunciado define para su
fase (tabla del Componente 3), con chequeos automáticos:

- Fase 2: completitud + consistencia + schema.
- Fase 5: pass rate + cobertura + defectos (validez de la suite contra el
  código correcto, puntaje de mutación, cobertura de líneas, defectos plantados).
- Fase 6: build + seguridad + despliegue reproducible (sin Docker en la
  máquina: estructura, sintaxis YAML, versiones fijas, usuario no root,
  secretos, verificación y rollback).
- Fase 7: regression tests + deuda técnica + trazabilidad (se aplica el cambio
  propuesto y se corren las 34 pruebas ocultas).
"""

import ast
import json
import re
import subprocess
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import yaml

from backend.services.json_extraction import extract_json_block
from benchmarks.calificadores import SUITE_OCULTA, _ejecutar, analisis_estatico
from benchmarks.mutantes import MUTANTES

RAIZ = Path(__file__).resolve().parent.parent
REFERENCIA = (RAIZ / "benchmarks" / "referencia" / "wishlist_service.py").read_text(encoding="utf-8")
_BLOQUE = re.compile(r"```([\w+-]*)[^\n]*\n(.*?)```", re.DOTALL)
_GHERKIN = re.compile(r"\bDado\b.*\bCuando\b.*\bEntonces\b", re.IGNORECASE | re.DOTALL)


def _puntaje(chequeos: dict[str, bool]) -> float:
    return round(100 * sum(chequeos.values()) / len(chequeos), 2)


# ---------------------------------------------------------------------------
# Fase 2 — Especificación
# ---------------------------------------------------------------------------


def calificar_fase2(salida: str, esperado: dict[str, Any]) -> dict[str, Any]:
    try:
        datos = json.loads(extract_json_block(salida))
    except (ValueError, TypeError) as e:
        return {"puntaje": 0.0, "cumple_tarea": False, "schema_ok": False, "chequeos": {},
                "detalle": {"error": f"JSON inválido: {e}"}}
    specs = datos.get("especificaciones") if isinstance(datos, dict) else None
    specs = specs if isinstance(specs, list) else []
    specs = [s for s in specs if isinstance(s, dict)]
    ids = [str(s.get("spec_id", "")) for s in specs]
    por_id = {str(s.get("spec_id")): s for s in specs}
    texto_inconsistencias = json.dumps(datos.get("inconsistencias", []), ensure_ascii=False)
    alertas = datos.get("alertas_cumplimiento", [])
    alertas = alertas if isinstance(alertas, list) else []

    def criterios_ok(s: dict) -> bool:
        cs = s.get("criterios_aceptacion")
        return isinstance(cs, list) and len(cs) >= 2 and all(_GHERKIN.search(str(c)) for c in cs)

    def campos_ok(s: dict) -> bool:
        return all(isinstance(s.get(k), list) for k in ("entradas", "salidas", "reglas_negocio", "dependencias")) \
            and bool(str(s.get("descripcion", "")).strip()) and bool(s.get("reglas_negocio"))

    def origen_ok(s: dict) -> bool:
        return str(s.get("requisito_origen", "")).replace("REQ", "SPEC") == str(s.get("spec_id"))

    spec_dep, req_dep = esperado["dependencia"]
    rota_origen, rota_destino = esperado["referencia_rota"]
    a, b = esperado["contradiccion"]
    inconsistencias = datos.get("inconsistencias", [])
    inconsistencias = inconsistencias if isinstance(inconsistencias, list) else []
    chequeos = {
        "schema: JSON con las 4 claves": isinstance(datos, dict) and all(
            k in datos for k in ("especificaciones", "inconsistencias", "alertas_cumplimiento", "supuestos")),
        "numeración exacta (respeta huecos, sin SPEC inventados)": sorted(ids) == sorted(esperado["ids_spec"])
        and len(ids) == len(set(ids)),
        "cada SPEC con su REQ de origen": bool(specs) and all(origen_ok(s) for s in specs),
        "cada SPEC con campos completos": bool(specs) and all(campos_ok(s) for s in specs),
        "cada SPEC con >= 2 criterios Gherkin": bool(specs) and all(criterios_ok(s) for s in specs),
        f"dependencia {spec_dep} -> {req_dep}": req_dep in json.dumps(
            por_id.get(spec_dep, {}).get("dependencias", []), ensure_ascii=False),
        f"referencia rota {rota_origen} -> {rota_destino}": rota_destino in texto_inconsistencias,
        f"contradicción {a} / {b}": any(
            a in json.dumps(i, ensure_ascii=False) and b in json.dumps(i, ensure_ascii=False)
            for i in inconsistencias),
        f"alerta legal {esperado['alerta_legal']}": any(
            isinstance(x, dict) and esperado["alerta_legal"] in str(x.get("requisito", ""))
            and "legal" in str(x.get("tipo", "")).lower() for x in alertas),
    }
    return {
        "puntaje": _puntaje(chequeos), "chequeos": chequeos,
        "schema_ok": chequeos["schema: JSON con las 4 claves"],
        "cumple_tarea": all(chequeos.values()),
        "detalle": {"ids_spec": ids, "n_inconsistencias": len(inconsistencias), "n_alertas": len(alertas),
                    "n_supuestos": len(datos.get("supuestos", []) or [])},
    }


# ---------------------------------------------------------------------------
# Fase 5 — Testing
# ---------------------------------------------------------------------------


def _suite_generada(salida: str) -> str | None:
    """El bloque de código Python con más funciones test_ (la suite automatizada)."""
    candidatos = [c for lang, c in _BLOQUE.findall(salida)
                  if lang.lower() in ("python", "py", "") and re.search(r"^\s*def test_", c, re.MULTILINE)]
    return max(candidatos, key=lambda c: len(re.findall(r"^\s*def test_", c, re.MULTILINE))) if candidatos else None


def _correr_suite(codigo: str, suite: str, cobertura: bool = False) -> dict[str, Any]:
    """Corre `suite` contra `codigo` (como wishlist_service.py) en una carpeta temporal."""
    with tempfile.TemporaryDirectory() as carpeta:
        d = Path(carpeta)
        (d / "wishlist_service.py").write_text(codigo, encoding="utf-8")
        (d / "test_generada.py").write_text(suite, encoding="utf-8")
        (d / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        xml = d / "r.xml"
        pytest_args = ["-m", "pytest", "-q", "-p", "no:cacheprovider", "-c", str(d / "pytest.ini"),
                       "--rootdir", carpeta, f"--junitxml={xml}", "test_generada.py"]
        args = [sys.executable, "-m", "coverage", "run", "--include=wishlist_service.py", *pytest_args] \
            if cobertura else [sys.executable, *pytest_args]
        try:
            r = _ejecutar(args, carpeta, timeout=120)
            raiz = ET.parse(xml).getroot()
        except (subprocess.TimeoutExpired, ET.ParseError, FileNotFoundError) as e:
            return {"ok": False, "error": type(e).__name__}
        suite_xml = raiz if raiz.tag == "testsuite" else raiz.find("testsuite")
        casos = {c.get("name"): (c.find("failure") is None and c.find("error") is None and c.find("skipped") is None)
                 for c in suite_xml.iter("testcase")}
        res: dict[str, Any] = {"ok": True, "casos": casos, "salida": (r.stdout or "")[-1500:]}
        if cobertura:
            rep = _ejecutar([sys.executable, "-m", "coverage", "json", "-o", "cov.json"], carpeta)
            try:
                res["cobertura_pct"] = json.loads((d / "cov.json").read_text())["totals"]["percent_covered"]
            except (FileNotFoundError, KeyError, ValueError):
                res["cobertura_pct"] = None
                res["error_cobertura"] = (rep.stderr or "")[-300:]
        return res


def calificar_fase5(salida: str, esperado: dict[str, Any]) -> dict[str, Any]:
    suite = _suite_generada(salida)
    base = {"puntaje": 0.0, "cumple_tarea": False, "schema_ok": False, "componentes": {}}
    if suite is None:
        return {**base, "detalle": {"error": "no hay una suite Python con funciones test_"}}
    peligrosos = analisis_estatico(suite).get("peligrosos")
    if peligrosos is None:
        return {**base, "detalle": {"error": "la suite no compila", "estatico": analisis_estatico(suite)}}
    if set(peligrosos) - {"open"}:
        return {**base, "detalle": {"error": f"la suite usa módulos o llamadas no permitidos: {peligrosos}"}}

    ref = _correr_suite(REFERENCIA, suite, cobertura=True)
    if not ref["ok"] or not ref["casos"]:
        return {**base, "detalle": {"error": "la suite no se pudo ejecutar", "ejecucion": ref}}
    validas = {n for n, ok in ref["casos"].items() if ok}
    total = len(ref["casos"])

    def mata(nombre: str) -> bool:
        buscar, reemplazo = MUTANTES[nombre]
        r = _correr_suite(REFERENCIA.replace(buscar, reemplazo), suite)
        return r["ok"] and any(not r["casos"].get(n, False) for n in validas)

    muertos = {n: mata(n) for n in MUTANTES}
    plantados = {n: muertos[n] for n in esperado["defectos_plantados"]}

    seccion_d = re.split(r"(?im)^\W*(?:D[.)]|#+\s*D\b|.*reporte de defectos)", salida)
    texto_d = seccion_d[-1] if len(seccion_d) > 1 else ""
    reportados = {
        "umbral exclusivo (>)": bool(re.search(r">=|≥|mayor o igual|inclusiv|igual al umbral|exactamente", texto_d, re.IGNORECASE)),
        "devuelve la lista interna": bool(re.search(r"copia|lista interna|mutab|referencia|in[- ]place|sort\(\)",
                                                    texto_d, re.IGNORECASE)),
    }
    cobertura = ref.get("cobertura_pct") or 0.0
    nombres_test = re.findall(r"^\s*def (test_\w+)", suite, re.MULTILINE)
    con_id = sum(bool(re.search(r"test_?\d+|test_\w*TEST|TEST[-_]?\d+", n, re.IGNORECASE)) for n in nombres_test)
    componentes = {
        "validez_suite": round(20 * len(validas) / total, 2),
        "mutacion": round(30 * sum(muertos.values()) / len(muertos), 2),
        "defectos_detectados_por_la_suite": 10 * sum(plantados.values()),
        "defectos_reportados_en_texto": 5 * sum(reportados.values()),
        "cobertura_lineas": round(10 * cobertura / 100, 2),
        "trazabilidad": (5 if nombres_test and con_id / len(nombres_test) >= 0.8 else 0)
        + (5 if re.search(r"matriz de cobertura|cobertura.*\|", salida, re.IGNORECASE) else 0),
    }
    return {
        "puntaje": round(sum(componentes.values()), 2), "componentes": componentes,
        "schema_ok": bool(re.search(r"TEST-\d+", salida)) and componentes["trazabilidad"] > 0,
        "cumple_tarea": len(validas) / total >= 0.9 and all(plantados.values()),
        "detalle": {"tests_total": total, "tests_validos_en_referencia": len(validas),
                    "tests_que_fallan_con_codigo_correcto": sorted(set(ref["casos"]) - validas),
                    "mutantes_detectados": muertos, "defectos_plantados_detectados": plantados,
                    "defectos_reportados": reportados, "cobertura_pct": cobertura},
    }


# ---------------------------------------------------------------------------
# Fase 6 — Deployment
# ---------------------------------------------------------------------------

# Lo que NO es un secreto: referencias (${...}, <...>), marcadores como "your_api_key"
# (el propio prompt pide ejemplos en la tabla de variables), nombres de secretos
# (fromSecret: nvidia-api-key) y credenciales falsas de una base de datos de prueba en CI.
_MARCADOR = r"(?!\$|\{|<|\*|your|tu_|su_|example|ejemplo|placeholder|changeme|cambiar|xxx|dummy|replace|reemplaz)"
_SECRETO = re.compile(
    r"nvapi-[A-Za-z0-9_-]{10,}"
    r"|postgres(?:ql)?://[^:\s/]+:" + _MARCADOR
    + r"(?!password|contrase|usuario|user|pass\b|invalid|test|postgres[:@]|ci[:@])[^@\s]{3,}@"
    # clave = valor con aspecto de secreto real: 16+ caracteres con letras y dígitos
    r"|\b(?:password|passwd|secret|api_key|token)\s*[:=]\s*[\"']?" + _MARCADOR
    + r"(?=[A-Za-z0-9/+_-]*\d)(?=[A-Za-z0-9/+_-]*[A-Za-z])[A-Za-z0-9/+_-]{16,}",
    re.IGNORECASE)


def _bloques(salida: str) -> list[tuple[str | None, str, str]]:
    """(ruta declarada en la línea previa, lenguaje, contenido) de cada bloque."""
    res = []
    for m in _BLOQUE.finditer(salida):
        previa = next((x for x in reversed(salida[: m.start()].splitlines()) if x.strip()), "")
        ruta = re.search(r"([\w.\-/]*(?:Dockerfile|\.ya?ml|\.sh|\.toml|\.json|\.env\.example|compose[\w.-]*))",
                         previa, re.IGNORECASE)
        res.append((ruta.group(1) if ruta else None, m.group(1).lower(), m.group(2)))
    return res


def calificar_fase6(salida: str, esperado: dict[str, Any]) -> dict[str, Any]:
    bloques = _bloques(salida)
    dockerfiles = [c for r, lang, c in bloques
                   if (r and r.lower().endswith("dockerfile")) or lang == "dockerfile" or re.match(r"\s*(#.*\n\s*)*FROM\s", c)]
    yamls = [(r, c) for r, lang, c in bloques if lang in ("yaml", "yml") or (r and r.lower().endswith((".yml", ".yaml")))]
    pipeline = [c for r, c in yamls if (r and ".github/workflows" in r) or re.search(r"^\s*jobs\s*:", c, re.MULTILINE)]
    config_entorno = [c for r, c in yamls if c not in pipeline]

    yaml_ok = True
    errores_yaml = []
    for r, c in yamls:
        try:
            list(yaml.safe_load_all(c))
        except yaml.YAMLError as e:
            yaml_ok = False
            errores_yaml.append(f"{r}: {str(e).splitlines()[0]}")

    froms = [ln.split()[1] for d in dockerfiles for ln in d.splitlines()
             if ln.strip().upper().startswith("FROM ") and len(ln.split()) > 1]
    etapas = {ln.split()[-1].lower() for d in dockerfiles for ln in d.splitlines()
              if ln.strip().upper().startswith("FROM ") and " as " in ln.lower()}
    externas = [f for f in froms if f.lower() not in etapas]
    fijadas = bool(externas) and all(":" in f and not f.lower().endswith(":latest") for f in externas)
    usuario = [ln.split()[1] for d in dockerfiles for ln in d.splitlines()
               if ln.strip().upper().startswith("USER ") and len(ln.split()) > 1]
    secretos = sorted({m.group(0)[:40] for m in _SECRETO.finditer(salida)})
    rollback = re.search(r"rollback|reversi[oó]n|volver a la versi[oó]n", salida, re.IGNORECASE)
    tras_rollback = salida[rollback.start():] if rollback else ""

    chequeos = {
        "pipeline de CI/CD": bool(pipeline),
        "Dockerfile": bool(dockerfiles),
        "Dockerfile multietapa": len(froms) >= 2,
        "imágenes base con versión fija (sin latest)": fijadas,
        "contenedor sin root (USER)": any(u.lower() not in ("root", "0") for u in usuario),
        "configuración del entorno (render.yaml u otra)": bool(config_entorno),
        "YAML sintácticamente válido": bool(yamls) and yaml_ok,
        "sin secretos en claro": not secretos,
        "verificación del despliegue (health/smoke)": bool(
            re.search(r"curl[^\n]*(/api/runs|/api/requirements|health)|healthcheck", salida, re.IGNORECASE)),
        "rollback con pasos numerados": bool(re.search(r"^\s*(?:\d+[.)]|[-*]\s*\*?\*?paso)", tras_rollback, re.MULTILINE | re.IGNORECASE)),
        "tabla de variables de entorno": all(v in salida for v in esperado["variables_obligatorias"])
        and bool(re.search(r"^\s*\|.*\|", salida, re.MULTILINE)),
    }
    afirma = re.findall(r"[^\n]*(?:se (?:ha )?validado|validad[oa]s? con|verificad[oa] con|pas[oó] hadolint|"
                        r"sin errores de hadolint|yamllint[^\n]*(?:ok|sin errores))[^\n]*", salida, re.IGNORECASE)
    return {
        "puntaje": _puntaje(chequeos), "chequeos": chequeos,
        "schema_ok": chequeos["pipeline de CI/CD"] and chequeos["Dockerfile"],
        "cumple_tarea": all(chequeos.values()),
        "detalle": {"archivos": [r for r, _, _ in bloques], "froms": froms, "usuario": usuario,
                    "errores_yaml": errores_yaml, "posibles_secretos": secretos,
                    "afirma_validaciones_no_ejecutadas": [a.strip()[:200] for a in afirma]},
    }


# ---------------------------------------------------------------------------
# Fase 7 — Mantenimiento
# ---------------------------------------------------------------------------


def _despues(salida: str) -> list[str]:
    """Código "después" de cada bloque: en un diff, las líneas + y de contexto."""
    res = []
    for lang, c in _BLOQUE.findall(salida):
        lineas = c.splitlines()
        es_diff = lang.lower() in ("diff", "patch") or sum(ln.startswith(("+", "-", "@@")) for ln in lineas) >= 2
        if es_diff:
            nuevas = []
            for ln in lineas:
                if ln.startswith(("+++", "---", "@@", "-", "\\")):
                    continue
                nuevas.append(ln[1:] if ln.startswith(("+", " ")) else ln)
            res.append("\n".join(nuevas))
        elif lang.lower() in ("python", "py", ""):
            res.append(c)
    return res


def _funciones(codigo: str) -> dict[str, str]:
    """Texto (dedentado) de cada función definida en un fragmento, aunque el
    fragmento no sea un módulo completo."""
    lineas = codigo.splitlines()
    res = {}
    for i, ln in enumerate(lineas):
        m = re.match(r"^(\s*)def (\w+)\(", ln)
        if not m:
            continue
        sangria = len(m.group(1))
        fin = i + 1
        while fin < len(lineas) and (not lineas[fin].strip() or len(lineas[fin]) - len(lineas[fin].lstrip()) > sangria
                                     or lineas[fin].lstrip().startswith(")")):
            fin += 1
        texto = textwrap.dedent("\n".join(lineas[i:fin])).rstrip()
        try:
            ast.parse(texto)
        except SyntaxError:
            continue
        res[m.group(2)] = texto
    return res


def _ast(codigo: str) -> str:
    """Forma normalizada de una función: ignora comentarios y formato."""
    return ast.dump(ast.parse(codigo))


def aplicar_cambio(original: str, salida: str) -> tuple[str, list[str]]:
    """Aplica al código original las funciones reescritas en la salida.
    Devuelve (código resultante, funciones cambiadas)."""
    completos = [c for c in _despues(salida) if "class WishlistService" in c and "def detect_price_drops" in c]
    if completos:
        nuevo = completos[-1]
        try:
            ast.parse(nuevo)
            viejas, nuevas = _funciones(original), _funciones(nuevo)
            return nuevo, sorted(n for n in nuevas if n not in viejas or _ast(viejas[n]) != _ast(nuevas[n]))
        except SyntaxError:
            pass
    arbol = ast.parse(original)
    nodos = {n.name: n for n in ast.walk(arbol) if isinstance(n, ast.FunctionDef)}
    lineas = original.splitlines()
    propuestas: dict[str, str] = {}
    for bloque in _despues(salida):
        propuestas.update(_funciones(bloque))  # el último bloque que define una función gana ("después")
    cambios = []
    for nombre, texto in sorted(propuestas.items(), key=lambda kv: -nodos[kv[0]].lineno if kv[0] in nodos else 0):
        if nombre not in nodos:
            continue
        nodo = nodos[nombre]
        viejo = textwrap.dedent("\n".join(lineas[nodo.lineno - 1: nodo.end_lineno]))
        if _ast(viejo) == _ast(texto):
            continue
        sangria = " " * nodo.col_offset
        lineas[nodo.lineno - 1: nodo.end_lineno] = [sangria + x if x else x for x in texto.splitlines()]
        cambios.append(nombre)
    return "\n".join(lineas) + "\n", sorted(cambios)


_SECCIONES_F7 = ["diagn", "cambio propuesto", "impacto", "pruebas de regresi", "deuda t", "trazabilidad", "supuestos"]


def calificar_fase7(salida: str, original: str, esperado: dict[str, Any]) -> dict[str, Any]:
    codigo, cambiadas = aplicar_cambio(original, salida)
    estatico = analisis_estatico(codigo)
    total = pasadas = 0
    fallos: list[str] = []
    if estatico.get("sintaxis_ok") and not estatico.get("peligrosos"):
        with tempfile.TemporaryDirectory() as carpeta:
            d = Path(carpeta)
            (d / "wishlist_service.py").write_text(codigo, encoding="utf-8")
            (d / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
            xml = d / "r.xml"
            try:
                _ejecutar([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c", str(d / "pytest.ini"),
                           "--rootdir", carpeta, f"--junitxml={xml}", str(SUITE_OCULTA)], carpeta)
                raiz = ET.parse(xml).getroot()
                s = raiz if raiz.tag == "testsuite" else raiz.find("testsuite")
                total = int(s.get("tests", 0))
                fallos = [c.get("name") for c in s.iter("testcase")
                          if c.find("failure") is not None or c.find("error") is not None]
                pasadas = total - len(fallos)
            except (subprocess.TimeoutExpired, ET.ParseError, FileNotFoundError):
                fallos = ["la suite no pudo ejecutarse"]
    minimo = cambiadas == [esperado["funcion_afectada"]]
    bajo = salida.lower()
    secciones = sum(s in bajo for s in _SECCIONES_F7)
    ids_inventados = sorted(set(re.findall(r"\bREQ-\d+\b", salida)))
    componentes = {
        "regresion": round(60 * pasadas / total, 2) if total else 0.0,
        "alcance_minimo": 10 if minimo else 0,
        "secciones": round(15 * secciones / len(_SECCIONES_F7), 2),
        "trazabilidad": (7.5 if all(i in salida for i in esperado["ids"]) else 0) + (0 if ids_inventados else 7.5),
    }
    return {
        "puntaje": round(sum(componentes.values()), 2), "componentes": componentes,
        "schema_ok": secciones == len(_SECCIONES_F7),
        "cumple_tarea": total > 0 and pasadas == total and minimo,
        "detalle": {"funciones_cambiadas": cambiadas, "tests_total": total, "tests_pasadas": pasadas,
                    "tests_fallidas": fallos, "secciones_presentes": secciones,
                    "ids_req_inventados": ids_inventados, "codigo_resultante": codigo},
    }
