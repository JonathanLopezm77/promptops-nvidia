"""Cliente HTTP asíncrono para la API de NVIDIA (compatible con OpenAI).

Endpoint y forma de la respuesta verificados contra la API real
(https://integrate.api.nvidia.com/v1/chat/completions) antes de escribir
este cliente, no asumidos de la documentación:

- `choices[0].message.content` trae la respuesta.
- `choices[0].message.reasoning_content` es un campo HERMANO separado en
  modelos de razonamiento (confirmado con moonshotai/kimi-k3) — nunca se
  mezcla con `content`.
- 401 devuelve JSON `{"status":401,...}`; 404 (modelo inexistente) devuelve
  texto plano "404 page not found", no JSON, así que el parseo de error
  nunca asume `response.json()`.

Aplica `LLM_TIMEOUT_SECONDS` y `LLM_MAX_RETRIES` de `.env`. Solo reintenta
fallos transitorios (timeout, conexión, 429, 5xx); 401/404/400 son errores
permanentes y se lanzan de inmediato.
"""

import asyncio
from dataclasses import dataclass
from typing import Any

import httpx

from backend.config import get_settings


class NvidiaClientError(Exception):
    """Error base del cliente NVIDIA."""


class NvidiaAuthError(NvidiaClientError):
    """401: API key inválida o ausente."""


class NvidiaModelNotFoundError(NvidiaClientError):
    """404: el modelo solicitado no existe en NVIDIA."""


class NvidiaRateLimitError(NvidiaClientError):
    """429 persistente tras agotar los reintentos."""


class NvidiaTimeoutError(NvidiaClientError):
    """La API no respondió dentro de LLM_TIMEOUT_SECONDS, ni tras reintentar."""


class NvidiaEmptyResponseError(NvidiaClientError):
    """La API respondió 200 pero sin contenido utilizable en el mensaje."""


class NvidiaServerError(NvidiaClientError):
    """Error 5xx / de red persistente tras agotar los reintentos."""


@dataclass
class NvidiaChatResult:
    content: str
    reasoning_content: str | None
    model: str
    raw_response: dict[str, Any]
    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None


_ESTADOS_REINTENTABLES = {429, 500, 502, 503, 504}


async def chat_completion(
    model: str,
    messages: list[dict[str, str]],
    *,
    max_tokens: int | None = None,
    extra_payload: dict[str, Any] | None = None,
) -> NvidiaChatResult:
    """`extra_payload` se mezcla tal cual en el JSON del request (p. ej.
    `{"chat_template_kwargs": {"thinking": False}}` para desactivar el
    razonamiento de modelos como deepseek-v4-pro en NVIDIA)."""
    settings = get_settings()
    payload: dict[str, Any] = {"model": model, "messages": messages}
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens
    if extra_payload:
        payload.update(extra_payload)

    intentos_totales = settings.llm_max_retries + 1

    async with httpx.AsyncClient(timeout=settings.llm_timeout_seconds) as client:
        for intento in range(1, intentos_totales + 1):
            try:
                response = await client.post(
                    f"{settings.nvidia_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.nvidia_api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                )
            except httpx.TimeoutException as exc:
                if intento < intentos_totales:
                    await asyncio.sleep(intento)
                    continue
                raise NvidiaTimeoutError(
                    f"NVIDIA no respondió en {settings.llm_timeout_seconds}s "
                    f"tras {intentos_totales} intento(s)."
                ) from exc
            except httpx.ConnectError as exc:
                if intento < intentos_totales:
                    await asyncio.sleep(intento)
                    continue
                raise NvidiaServerError(
                    f"No se pudo conectar con NVIDIA tras {intentos_totales} intento(s): {exc}"
                ) from exc

            if response.status_code == 401:
                raise NvidiaAuthError("NVIDIA_API_KEY inválida o ausente (401 Unauthorized).")

            if response.status_code == 404:
                raise NvidiaModelNotFoundError(
                    f"El modelo '{model}' no existe en NVIDIA (404). Revisa el nombre en .env."
                )

            if response.status_code in _ESTADOS_REINTENTABLES:
                if intento < intentos_totales:
                    await asyncio.sleep(intento)
                    continue
                if response.status_code == 429:
                    raise NvidiaRateLimitError(
                        f"Rate limit de NVIDIA (429) persistente tras {intentos_totales} intento(s)."
                    )
                raise NvidiaServerError(
                    f"NVIDIA respondió {response.status_code} de forma persistente tras "
                    f"{intentos_totales} intento(s): {response.text[:300]}"
                )

            if response.status_code != 200:
                raise NvidiaClientError(
                    f"NVIDIA respondió {response.status_code} inesperado: {response.text[:300]}"
                )

            return _parsear_respuesta(response, model)

    raise NvidiaClientError("Fallo desconocido llamando a NVIDIA: se agotaron los intentos.")


def _parsear_respuesta(response: httpx.Response, model: str) -> NvidiaChatResult:
    try:
        body = response.json()
    except ValueError as exc:
        raise NvidiaEmptyResponseError(
            f"NVIDIA respondió 200 pero el cuerpo no es JSON válido: {response.text[:300]}"
        ) from exc

    choices = body.get("choices") or []
    if not choices:
        raise NvidiaEmptyResponseError("NVIDIA respondió 200 sin 'choices' en el cuerpo.")

    message = choices[0].get("message") or {}
    content = message.get("content")
    if not content:
        raise NvidiaEmptyResponseError("NVIDIA respondió 200 pero 'message.content' está vacío.")

    usage = body.get("usage") or {}

    return NvidiaChatResult(
        content=content,
        reasoning_content=message.get("reasoning_content"),
        model=body.get("model", model),
        raw_response=body,
        prompt_tokens=usage.get("prompt_tokens"),
        completion_tokens=usage.get("completion_tokens"),
        total_tokens=usage.get("total_tokens"),
    )
