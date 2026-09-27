"""Tests del cliente NVIDIA con httpx mockeado (sin red)."""

import httpx
import pytest

from backend.services.nvidia_client import NvidiaModelNotFoundError, chat_completion


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
