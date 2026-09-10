"""Extracción robusta de JSON desde el texto de respuesta de un LLM.

Los modelos a veces envuelven el JSON en bloques ```json ... ``` o le
añaden texto alrededor pese a que el system prompt pide JSON puro.
SPEC.md §17: "extraer el bloque JSON del texto" es el primer paso antes
de reintentar cuando el parseo directo falla.
"""

import re

_BLOQUE_MARKDOWN = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


def extract_json_block(text: str) -> str:
    """Acota el substring más probable de ser el JSON de la respuesta.

    No valida que sea JSON válido: solo recorta. La validación real la
    hace Pydantic al construir el schema correspondiente.
    """
    texto = text.strip()

    match = _BLOQUE_MARKDOWN.search(texto)
    if match:
        return match.group(1).strip()

    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio != -1 and fin != -1 and fin > inicio:
        return texto[inicio : fin + 1]

    return texto
