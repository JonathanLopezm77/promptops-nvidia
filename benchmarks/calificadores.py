"""Calificadores deterministas de cada fase del benchmark. Implementan las
reglas de benchmarks/DISENO.md §3. Las partes que dependen de un juez de IA
(Quality Score de la fase 1, restricciones y revisión de la fase 3) llegan
como argumento: estas funciones solo combinan y verifican.

Todas devuelven un dict con: puntaje (0-100), componentes, cumple_tarea,
schema_ok, violaciones (lista), supuestos_no_sustentados (lista) y detalle.
"""

import ast
import json
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from backend.schemas.requirements import valores_sin_respaldo

RAIZ = Path(__file__).resolve().parent.parent
SUITE_OCULTA = RAIZ / "benchmarks" / "pruebas_ocultas" / "test_wishlist_service.py"

# ---------------------------------------------------------------------------
# Fase 1 — Requisitos
# ---------------------------------------------------------------------------

_SECCIONES_F1 = [
    "requisitos funcionales",
    "requisitos no funcionales",
    "información faltante",
    "aclaraciones sobre información ambigua",
]
_REQ = re.compile(r"^\s*(?:[-*]\s*)?\**(R(?:N)?F)[-‑](\d+)\**\s*:\s*(.+)$", re.IGNORECASE)
_CRITERIO = re.compile(r"^\s*(?:[-*]\s*)?\**criterio de aceptaci[oó]n\**\s*:", re.IGNORECASE)
_VERBOS_PROHIBIDOS = ["gestionar", "procesar", "manejar", "administrar", "ofrecer soporte"]
_TERMINOS_VAGOS = ["rápid", "fácil", "adecuad", "demasiado"]
# Patrones por hueco plantado en la entrada. Se aplican a cada pregunta por
# separado. Precisos a propósito: "hora" no debe coincidir con "ahora", ni
# "tiempo máximo" contar como pregunta sobre el tamaño de la lista.
_HUECOS = {
    "plazo del aviso": re.compile(r"\b(tiempo|plazo|minutos?|horas?|inmediat\w*|demora|latencia|r[aá]pid\w*)\b", re.I),
    "tamaño de la lista": re.compile(
        r"(cantidad|cu[aá]ntos productos|n[uú]mero (m[aá]ximo )?de productos|tama[ñn]o|grande|"
        r"l[ií]mite de productos|m[aá]ximo de productos|productos como m[aá]ximo)", re.I),
    "umbral de baja": re.compile(
        r"(umbral|porcentaje|cu[aá]nto (debe )?baj|reducci[oó]n m[ií]nima|baja m[ií]nima|monto m[ií]nimo|"
        r"disminuci[oó]n m[ií]nima|cualquier (baja|disminuci|reducci)|\d+\s?%)", re.I),
    "clientes invitados": re.compile(r"(invitad|sin cuenta|no registrad)", re.I),
}


def _secciones(texto: str) -> dict[str, list[str]]:
    """Divide la salida por encabezados Markdown (#...) y devuelve {titulo: lineas}."""
    actual, partes = "_preambulo", {"_preambulo": []}
    for linea in texto.splitlines():
        m = re.match(r"^\s*#{1,6}\s*(.+?)\s*#*\s*$", linea)
        if m:
            actual = m.group(1).strip().strip("*").lower()
            partes[actual] = []
        else:
            partes[actual].append(linea)
    return partes


def calificar_fase1(salida: str, entrada: dict[str, str], juez_score: int | None) -> dict[str, Any]:
    secciones = _secciones(salida)
    # Secciones obligatorias en el orden en que aparecen los títulos.
    encontradas = [s for t in secciones if t != "_preambulo" for s in _SECCIONES_F1 if s in t]
    presentes = [s for s in _SECCIONES_F1 if s in encontradas]
    en_orden = encontradas == presentes  # mismo orden que el formato y sin repetidas

    lineas = salida.splitlines()
    requisitos = []  # (tipo, numero, texto, tiene_criterio)
    for i, linea in enumerate(lineas):
        m = _REQ.match(linea)
        if not m:
            continue
        siguiente = next((x for x in lineas[i + 1:] if x.strip()), "")
        requisitos.append((m.group(1).upper(), int(m.group(2)), m.group(3), bool(_CRITERIO.match(siguiente))))
    n_rf = sum(1 for r in requisitos if r[0] == "RF")

    # Verificabilidad
    verificabilidad = sum(r[3] for r in requisitos) / len(requisitos) if requisitos else 0.0

    # Trazabilidad: por tipo, números únicos y secuenciales desde 1
    ids_ok = 0
    for tipo in ("RF", "RNF"):
        nums = [r[1] for r in requisitos if r[0] == tipo]
        esperado = list(range(1, len(nums) + 1))
        ids_ok += sum(1 for a, b in zip(nums, esperado) if a == b)
    trazabilidad = ids_ok / len(requisitos) if requisitos else 0.0

    # Supuestos no sustentados: números en requisitos y criterios que no están en la entrada
    texto_req = "\n".join(
        linea for linea in lineas if _REQ.match(linea) or _CRITERIO.match(linea)
    )
    inventados = valores_sin_respaldo(texto_req, *entrada.values())

    # Violaciones del prompt: verbos prohibidos o términos vagos en RF/RNF
    violaciones = []
    for tipo, num, texto, _ in requisitos:
        t = texto.lower()
        for v in _VERBOS_PROHIBIDOS:
            if re.search(rf"\b{v}", t):
                violaciones.append(f"{tipo}-{num:02d}: verbo prohibido '{v}'")
        for v in _TERMINOS_VAGOS:
            if v in t:
                violaciones.append(f"{tipo}-{num:02d}: término vago '{v}'")

    # Huecos preguntados: cada pregunta de las secciones de preguntas se
    # compara con los patrones de cada hueco plantado.
    preguntas = [
        linea for t, ls in secciones.items() if "faltante" in t or "ambigua" in t for linea in ls if linea.strip()
    ]
    huecos = [h for h, patron in _HUECOS.items() if any(patron.search(p) for p in preguntas)]

    schema_ok = len(presentes) == 4 and en_orden and n_rf >= 1
    componentes = {
        "quality_score": round(0.5 * juez_score, 2) if juez_score is not None else None,
        "verificabilidad": round(20 * verificabilidad, 2),
        "trazabilidad": round(15 * trazabilidad, 2),
        "no_inventar": max(0, 15 - 5 * len(inventados)),
    }
    puntaje = None if juez_score is None else round(sum(componentes.values()), 2)
    return {
        "puntaje": puntaje, "componentes": componentes,
        "cumple_tarea": schema_ok and verificabilidad >= 0.8 and not inventados and len(huecos) >= 2,
        "schema_ok": schema_ok, "violaciones": violaciones, "supuestos_no_sustentados": inventados,
        "detalle": {
            "secciones_presentes": presentes, "secciones_en_orden": en_orden,
            "requisitos": len(requisitos), "rf": n_rf, "rnf": len(requisitos) - n_rf,
            "verificabilidad": round(verificabilidad, 3), "trazabilidad": round(trazabilidad, 3),
            "huecos_preguntados": huecos,
        },
    }


# ---------------------------------------------------------------------------
# Fase 3 — Arquitectura
# ---------------------------------------------------------------------------

_SECCIONES_F3 = {
    "resumen": ["resumen"],
    "componentes": ["componentes"],
    "contratos": ["contratos"],
    "decisiones": ["decisiones"],
    "verificación de restricciones": ["verificación de restricciones", "verificacion de restricciones"],
    "diagrama": ["diagrama", "mermaid"],
    "supuestos y riesgos": ["supuestos"],
    "brechas de cobertura": ["brechas"],
    "lista de comprobación": ["comprobación", "comprobacion", "checklist"],
}
_BLOQUE = re.compile(r"```([\w+-]*)[^\n]*\n(.*?)```", re.DOTALL)
_LENGUAJES_IMPLEMENTACION = {"python", "py", "javascript", "js", "typescript", "ts", "java", "go", "csharp", "cs"}
_ARCH = re.compile(r"ARCH[-‑_]?(\d{2,})")


def _encabezados(texto: str) -> list[str]:
    """Líneas que funcionan como título: Markdown (#), negrita al inicio o 'N. '."""
    return [
        linea.strip().lower() for linea in texto.splitlines()
        if re.match(r"^\s*(#{1,6}\s|\*\*|\d+\.\s+\**[A-ZÁÉÍÓÚ])", linea)
    ]


def calificar_fase3(salida: str, ids_spec: list[str], juez: dict[str, Any] | None) -> dict[str, Any]:
    encabezados = " \n".join(_encabezados(salida))
    secciones = [s for s, claves in _SECCIONES_F3.items() if any(c in encabezados for c in claves)]

    bloques = _BLOQUE.findall(salida)
    mermaid = "\n".join(c for lang, c in bloques if lang.lower() == "mermaid")
    implementacion = [lang for lang, _ in bloques if lang.lower() in _LENGUAJES_IMPLEMENTACION]

    normal = salida.replace("‑", "-")
    cubiertos = [s for s in ids_spec if s in normal]

    ids_arch = sorted({int(n) for n in _ARCH.findall(salida)})
    secuenciales = bool(ids_arch) and ids_arch == list(range(1, len(ids_arch) + 1))
    en_diagrama = bool(ids_arch) and all(
        re.search(rf"ARCH[-‑_]?{n:02d}\b", mermaid) for n in ids_arch
    )

    # "Afirma verificaciones no realizadas": marca como hecho [x] un ítem que
    # dice haber usado un linter o un script (el modelo no puede ejecutarlos).
    afirmaciones = [
        linea.strip() for linea in salida.splitlines()
        if re.search(r"\[[xX✓✔]\]", linea) and re.search(r"linter|script|mermaid[-‑ ]cli|mermaid\.live", linea, re.I)
    ]

    violaciones, supuestos = [], list(afirmaciones)
    restricciones_violadas = []
    if juez:
        restricciones_violadas = [r["id"] for r in juez["restricciones"] if not r["cumple"]]
        violaciones += [f"{r['id']}: {r['evidencia']}" for r in juez["restricciones"] if not r["cumple"]]
        supuestos += [f"funcionalidad inventada: {x}" for x in juez["funcionalidades_inventadas"]]
        supuestos += [f"dato inventado: {x}" for x in juez["datos_inventados"]]
    if implementacion:
        violaciones.append(f"incluye código de implementación ({', '.join(implementacion)})")

    schema_ok = len(secciones) == len(_SECCIONES_F3) and bool(mermaid.strip()) and not implementacion
    componentes = {
        "cobertura_spec": round(25 * len(cubiertos) / len(ids_spec), 2),
        "estructura": round(15 * len(secciones) / len(_SECCIONES_F3), 2),
        "identificadores": (5 if secuenciales else 0) + (5 if en_diagrama else 0),
        "restricciones": max(0, 20 - 7 * len(restricciones_violadas)) if juez else None,
        "revision": 3 * juez["puntaje_revision"] if juez else None,
    }
    puntaje = None if juez is None else round(sum(componentes.values()), 2)
    return {
        "puntaje": puntaje, "componentes": componentes,
        "cumple_tarea": (len(cubiertos) == len(ids_spec) and schema_ok and not restricciones_violadas
                         if juez else None),
        "schema_ok": schema_ok, "violaciones": violaciones, "supuestos_no_sustentados": supuestos,
        "detalle": {
            "secciones_presentes": secciones, "specs_cubiertos": cubiertos, "ids_arch": ids_arch,
            "arch_secuenciales": secuenciales, "arch_en_diagrama": en_diagrama,
            "tiene_mermaid": bool(mermaid.strip()), "bloques_implementacion": implementacion,
            "afirma_verificacion_no_realizada": afirmaciones,
            "restricciones_violadas_segun_juez": restricciones_violadas,
            # Informativo: la cobertura puntuada es la presencia del SPEC en el
            # documento; el juez además opina si cada SPEC está cubierto de
            # forma concreta (en el ensayo detectó un SPEC-03 incompleto).
            "specs_no_cubiertos_segun_juez": [s["id"] for s in juez["specs"] if not s["cubierto"]] if juez else None,
        },
    }


# ---------------------------------------------------------------------------
# Fase 4 — Implementación
# ---------------------------------------------------------------------------

_ARCHIVO = re.compile(r"^\s*(?:#|//)\s*File\s*:\s*(\S+)", re.IGNORECASE)
_NOMBRES_CONTRATO = {
    "WishlistError", "DuplicateItemError", "WishlistFullError", "ItemNotFoundError", "InvalidPriceError",
    "WishlistItem", "PriceDrop", "WishlistService", "detect_price_drops",
}
# Módulos que dan acceso a red, disco, procesos o carga dinámica de código:
# si el código generado los importa no se ejecuta (y cuenta como violación).
# No incluye módulos inofensivos de la biblioteca estándar (threading para un
# Lock, typing, sys, asyncio...): bloquearlos daría 0 a un código correcto.
_MODULOS_PELIGROSOS = {
    "os", "subprocess", "socket", "shutil", "pathlib", "ctypes", "multiprocessing", "urllib", "http",
    "requests", "httpx", "ftplib", "smtplib", "sqlite3", "pickle", "importlib", "builtins", "tempfile",
    "glob", "signal", "webbrowser",
}
_LLAMADAS_PELIGROSAS = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}


_RUTA_SUELTA = re.compile(r"^[\s>#*`_-]*(?:(?:File|Archivo)\s*:\s*)?[`*_]*([\w./\\-]+\.[A-Za-z]{1,5})[`*_:]*\s*$",
                         re.IGNORECASE)


def _lenguaje_por_ruta(ruta: str | None) -> str:
    return "python" if ruta and ruta.lower().endswith(".py") else ""


def extraer_archivos(salida: str) -> list[tuple[str | None, str, str]]:
    """Archivos de código de la salida: (ruta declarada o None, lenguaje, código).

    El prompt aprobado pide "únicamente código" con una línea `# File: ruta`
    por archivo, y los modelos lo entregan de tres formas válidas (vistas en
    el ensayo del punto 6):
    1. bloques ``` con `# File:` en su primera línea;
    2. bloques ``` con la ruta en la línea anterior al bloque;
    3. código sin ``` dividido por líneas `# File:` (así respondió nemotron).
    """
    archivos = []
    for m in _BLOQUE.finditer(salida):
        lang, codigo = m.group(1).lower(), m.group(2)
        primera = next((x for x in codigo.splitlines() if x.strip()), "")
        cabecera = _ARCHIVO.match(primera)
        ruta = cabecera.group(1) if cabecera else None
        if ruta is None:
            anterior = next((x for x in reversed(salida[: m.start()].splitlines()) if x.strip()), "")
            suelta = _RUTA_SUELTA.match(anterior)
            ruta = suelta.group(1) if suelta else None
        archivos.append((ruta, lang or _lenguaje_por_ruta(ruta), codigo))
    if archivos:
        return archivos

    # Sin bloques ```: se divide por las líneas "# File:".
    lineas = salida.splitlines()
    inicios = [i for i, linea in enumerate(lineas) if _ARCHIVO.match(linea)]
    for k, i in enumerate(inicios):
        fin = inicios[k + 1] if k + 1 < len(inicios) else len(lineas)
        ruta = _ARCHIVO.match(lineas[i]).group(1)
        archivos.append((ruta, _lenguaje_por_ruta(ruta), "\n".join(lineas[i:fin])))
    if not archivos and salida.strip():
        try:
            ast.parse(salida)
            archivos.append((None, "", salida))  # todo el texto es un único módulo Python válido
        except SyntaxError:
            pass
    return archivos


def analisis_estatico(codigo: str) -> dict[str, Any]:
    try:
        arbol = ast.parse(codigo)
    except SyntaxError as e:
        return {"sintaxis_ok": False, "error": f"{e.msg} (línea {e.lineno})"}
    importados = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            importados |= {a.name.split(".")[0] for a in nodo.names}
        elif isinstance(nodo, ast.ImportFrom) and nodo.module:
            importados.add(nodo.module.split(".")[0])
    llamadas = {
        n.func.id for n in ast.walk(arbol) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
    } & _LLAMADAS_PELIGROSAS
    no_estandar = sorted(m for m in importados if m not in sys.stdlib_module_names and m != "__future__")
    publicos = sorted(
        n.name for n in arbol.body
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not n.name.startswith("_")
    )
    return {
        "sintaxis_ok": True,
        "importados": sorted(importados),
        "no_estandar": no_estandar,
        "peligrosos": sorted((importados & _MODULOS_PELIGROSOS) | llamadas),
        "nombres_publicos_extra": [n for n in publicos if n not in _NOMBRES_CONTRATO],
        "faltan_del_contrato": sorted(_NOMBRES_CONTRATO - set(publicos)),
        "asunciones": len(re.findall(r"ASSUMPTION", codigo)),
    }


def _ejecutar(argumentos: list[str], carpeta: str, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(argumentos, cwd=carpeta, capture_output=True, text=True, timeout=timeout,
                          env={"PYTHONPATH": carpeta, "SYSTEMROOT": "C:\\Windows", "PYTHONIOENCODING": "utf-8"})


def calificar_fase4(salida: str) -> dict[str, Any]:
    archivos = extraer_archivos(salida)
    python = [a for a in archivos if a[1] in ("python", "py", "")]

    def es_prueba(a) -> bool:
        return bool((a[0] and Path(a[0]).name.startswith("test_")) or re.search(r"^\s*def test_", a[2], re.M))

    implementaciones = [a for a in python if not es_prueba(a)]
    incluye_pruebas = any(es_prueba(a) for a in python)
    modulo = next((a for a in implementaciones if a[0] and a[0].replace("\\", "/").endswith("wishlist_service.py")),
                  None)
    encabezado_file = modulo is not None
    if modulo is None and len(implementaciones) == 1:
        modulo = implementaciones[0]  # sin encabezado # File:, pero es el único bloque de implementación

    violaciones, supuestos = [], []
    if incluye_pruebas:
        violaciones.append("incluye pruebas aunque el diseño dice que no se requieren")
    base = {"puntaje": 0.0, "componentes": {"tests": 0, "lint": 0, "formato": 0}, "cumple_tarea": False,
            "schema_ok": False, "violaciones": violaciones, "supuestos_no_sustentados": supuestos}
    if modulo is None:
        return {**base, "detalle": {"error": "no se encontró wishlist_service.py en la salida",
                                    "bloques": [(a[0], a[1]) for a in archivos]}}
    codigo = modulo[2]
    estatico = analisis_estatico(codigo)
    if not estatico["sintaxis_ok"]:
        return {**base, "schema_ok": encabezado_file,
                "detalle": {"compila": False, "error": estatico["error"], "estatico": estatico}}
    if estatico["no_estandar"]:
        violaciones.append(f"dependencias fuera de la biblioteca estándar: {estatico['no_estandar']}")
    if estatico["peligrosos"]:
        violaciones.append(f"acceso a red/disco/procesos o ejecución dinámica: {estatico['peligrosos']}")
    supuestos += [f"nombre público fuera del contrato: {n}" for n in estatico["nombres_publicos_extra"]]

    detalle: dict[str, Any] = {"estatico": estatico, "encabezado_file": encabezado_file,
                               "archivos": [(a[0], a[1]) for a in archivos]}
    if estatico["peligrosos"]:
        detalle["ejecutado"] = False
        return {**base, "schema_ok": encabezado_file, "detalle": detalle}

    with tempfile.TemporaryDirectory() as carpeta:
        (Path(carpeta) / "wishlist_service.py").write_text(codigo, encoding="utf-8")
        # Configuración vacía: la suite no hereda el pytest.ini del proyecto.
        (Path(carpeta) / "pytest.ini").write_text("[pytest]\n", encoding="utf-8")
        try:
            compila = _ejecutar([sys.executable, "-m", "py_compile", "wishlist_service.py"], carpeta).returncode == 0
        except subprocess.TimeoutExpired:
            compila = False
        try:
            lint = _ejecutar([sys.executable, "-m", "ruff", "check", "--isolated", "--no-cache", "--output-format", "json",
                              "wishlist_service.py"], carpeta)
            avisos = json.loads(lint.stdout or "[]")
        except (subprocess.TimeoutExpired, ValueError):
            avisos = [{"code": "LINT", "message": "ruff no pudo ejecutarse"}]
        xml = Path(carpeta) / "resultado.xml"
        total, fallidas, fallos = 0, 0, []
        if compila:
            try:
                _ejecutar([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-c",
                           str(Path(carpeta) / "pytest.ini"), "--rootdir", carpeta, f"--junitxml={xml}",
                           str(SUITE_OCULTA)], carpeta)
                raiz = ET.parse(xml).getroot()
                suite = raiz if raiz.tag == "testsuite" else raiz.find("testsuite")
                total = int(suite.get("tests", 0))
                fallidas = int(suite.get("failures", 0)) + int(suite.get("errors", 0))
                fallos = [c.get("name") for c in suite.iter("testcase")
                          if c.find("failure") is not None or c.find("error") is not None]
            except (subprocess.TimeoutExpired, ET.ParseError, FileNotFoundError, AttributeError) as e:
                total, fallidas, fallos = 34, 34, [f"la suite no pudo ejecutarse: {type(e).__name__}"]

    pasadas = max(0, total - fallidas)
    tasa = pasadas / total if total else 0.0
    implements = re.search(r"Implements\s*:.*ARCH[-‑]\d+.*SPEC[-‑]\d+", codigo) is not None
    componentes = {
        "tests": round(70 * tasa, 2) if compila else 0,
        "lint": max(0.0, 15 - 1.5 * len(avisos)) if compila else 0,
        "formato": (5 if encabezado_file else 0) + (5 if implements else 0) + (5 if len(implementaciones) == 1 else 0),
    }
    detalle.update({"compila": compila, "tests_total": total, "tests_pasadas": pasadas, "tests_fallidas": fallos,
                    "avisos_lint": [f"{a.get('code')}: {a.get('message')}" for a in avisos],
                    "implements": implements, "archivos_implementacion": len(implementaciones),
                    "incluye_pruebas": bool(incluye_pruebas)})
    return {
        "puntaje": round(sum(componentes.values()), 2) if compila else 0.0,
        "componentes": componentes,
        "cumple_tarea": compila and total > 0 and pasadas == total,
        "schema_ok": encabezado_file and compila,
        "violaciones": violaciones, "supuestos_no_sustentados": supuestos, "detalle": detalle,
    }
