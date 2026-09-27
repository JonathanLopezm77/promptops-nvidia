"""Tests del cliente NVIDIA con httpx mockeado (sin red)."""

import httpx
import pytest

from backend.config import Settings, get_settings
from backend.services.nvidia_client import (
    NvidiaEmptyResponseError,
    NvidiaModelNotFoundError,
    chat_completion,
)

_VACIA = {
    "id": "x", "model": "moonshotai/kimi-k3",
    "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "", "refusal": None}}],
}
_BUENA = {
    "id": "y", "model": "moonshotai/kimi-k3",
    "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "hola"}}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}


def _post_en_secuencia(monkeypatch, cuerpos):
    llamadas = []

    async def post_falso(self, url, **kwargs):
        llamadas.append(url)
        return httpx.Response(200, json=cuerpos[min(len(llamadas), len(cuerpos)) - 1])

    monkeypatch.setattr(httpx.AsyncClient, "post", post_falso)
    monkeypatch.setattr("backend.services.nvidia_client.asyncio.sleep", _sin_espera)
    return llamadas


async def _sin_espera(_segundos):
    return None


async def test_respuesta_vacia_se_reintenta(monkeypatch):
    # Visto en el punto 3: kimi-k3 devolvió 200 con content vacío de forma
    # intermitente; al repetir la llamada respondió bien.
    llamadas = _post_en_secuencia(monkeypatch, [_VACIA, _BUENA])

    resultado = await chat_completion("moonshotai/kimi-k3", [{"role": "user", "content": "hola"}])

    assert resultado.content == "hola"
    assert len(llamadas) == 2


async def test_respuesta_vacia_persistente_conserva_el_cuerpo(monkeypatch):
    llamadas = _post_en_secuencia(monkeypatch, [_VACIA])

    with pytest.raises(NvidiaEmptyResponseError) as info:
        await chat_completion("moonshotai/kimi-k3", [{"role": "user", "content": "hola"}])

    assert len(llamadas) == get_settings().llm_max_retries + 1
    assert info.value.raw_response == _VACIA
    assert "finish_reason='stop'" in str(info.value)


def test_modo_json_se_configura_por_modelo():
    base = get_settings().model_dump(exclude={"json_mode_models"})
    solo_nemotron = Settings(**base, json_mode_models=frozenset({"nvidia/nemotron-3-super-120b-a12b"}))
    todos = Settings(**base, json_mode_models=frozenset({"*"}))

    assert solo_nemotron.json_mode_for("nvidia/nemotron-3-super-120b-a12b")
    assert not solo_nemotron.json_mode_for("moonshotai/kimi-k3")
    assert todos.json_mode_for("moonshotai/kimi-k3")
    assert not Settings(**base).json_mode_for("moonshotai/kimi-k3")


async def test_404_incluye_la_respuesta_de_nvidia_para_distinguir_la_causa(monkeypatch):
    # NVIDIA responde 404 tanto si el modelo no existe como si la cuenta de
    # la API key no tiene acceso: solo el cuerpo permite distinguirlo.
    llamadas = []

    async def post_falso(self, url, **kwargs):
        llamadas.append(url)
        return httpx.Response(404, text="Function 'abc': Not found for account 'xyz'\n")

    monkeypatch.setattr(httpx.AsyncClient, "post", post_falso)

    with pytest.raises(NvidiaModelNotFoundError) as info:
        await chat_completion("nvidia/modelo-x", [{"role": "user", "content": "hola"}])

    mensaje = str(info.value)
    assert "nvidia/modelo-x" in mensaje
    assert "no tiene acceso" in mensaje
    assert "Not found for account 'xyz'" in mensaje
    assert len(llamadas) == 1  # un 404 es permanente: no se reintenta
