"""Tests de benchmarks/proveedores.py con respuestas simuladas en el mismo
formato que devolvieron NVIDIA y Ollama en las pruebas reales del punto 5
(sin red)."""

import json

import httpx
import pytest

from benchmarks.proveedores import ModeloBench, Parametros, generar

NVIDIA = ModeloBench(clave="c", tipo="cloud", proveedor="nvidia", modelo="nvidia/modelo",
                     extra={"chat_template_kwargs": {"thinking": False}})
OLLAMA = ModeloBench(clave="l", tipo="local", proveedor="ollama", modelo="qwen2.5-coder:7b",
                     extra={"options": {"num_ctx": 16384}, "keep_alive": "30m"})


def _sse(*eventos) -> bytes:
    return "".join(f"data: {json.dumps(e)}\n\n" for e in eventos).encode() + b"data: [DONE]\n\n"


def _delta(**campos):
    return {"model": "nvidia/modelo", "choices": [{"index": 0, "delta": campos, "finish_reason": None}]}


def _cliente(respuesta_por_url, capturados):
    def manejar(request: httpx.Request) -> httpx.Response:
        capturados.append((str(request.url), json.loads(request.content)))
        return respuesta_por_url(str(request.url))

    return httpx.AsyncClient(transport=httpx.MockTransport(manejar))


async def test_nvidia_separa_razonamiento_y_respuesta_y_lee_el_uso():
    cuerpo = _sse(
        _delta(role="assistant", content=""),
        _delta(reasoning_content="Pienso"),
        _delta(content="Hola"),
        _delta(content=" mundo"),
        {"model": "nvidia/modelo", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]},
        {"model": "nvidia/modelo", "choices": [], "usage": {
            "prompt_tokens": 10, "completion_tokens": 7, "completion_tokens_details": {"reasoning_tokens": 3}}},
    )
    enviados = []
    async with _cliente(lambda url: httpx.Response(200, content=cuerpo), enviados) as c:
        res = await generar(NVIDIA, [{"role": "user", "content": "x"}], Parametros(),
                            client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert res.ok
    assert res.contenido == "Hola mundo" and res.razonamiento == "Pienso"
    assert (res.tokens_entrada, res.tokens_salida, res.tokens_razonamiento) == (10, 7, 3)
    assert res.finish_reason == "stop"
    assert res.ttft_s is not None and res.ttft_contenido_s is not None and res.ttft_s <= res.ttft_contenido_s
    assert res.recursos is None  # los recursos solo se miden para el modelo local
    url, body = enviados[0]
    assert url == "https://nv/v1/chat/completions"
    # Parámetros comunes explícitos + los propios del modelo; nunca seed.
    assert (body["temperature"], body["top_p"], body["max_tokens"]) == (0.2, 0.95, 4096)
    assert body["chat_template_kwargs"] == {"thinking": False}
    assert body["stream"] is True and body["stream_options"] == {"include_usage": True}
    assert "seed" not in body


async def test_nvidia_respuesta_vacia_queda_como_error_y_no_lanza():
    # Caso real de kimi-k3 en streaming: solo razonamiento, sin respuesta.
    cuerpo = _sse(_delta(reasoning_content="!!!!"),
                  {"model": "m", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    async with _cliente(lambda url: httpx.Response(200, content=cuerpo), []) as c:
        res = await generar(NVIDIA, [], Parametros(), client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert not res.ok
    assert "Respuesta vacía" in res.error and "razonamiento=4" in res.error
    assert res.ttft_s is not None and res.ttft_contenido_s is None


@pytest.mark.parametrize("codigo", [401, 404, 500])
async def test_nvidia_error_http_queda_registrado(codigo):
    async with _cliente(lambda url: httpx.Response(codigo, text="Not found for account"), []) as c:
        res = await generar(NVIDIA, [], Parametros(), client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert not res.ok and res.error.startswith(f"HTTP {codigo}")
    assert res.latencia_total_s is not None


async def test_ollama_usa_la_api_nativa_con_num_ctx_y_lee_las_metricas():
    lineas = [
        {"model": "qwen2.5-coder:7b", "message": {"role": "assistant", "content": "Ho"}, "done": False},
        {"model": "qwen2.5-coder:7b", "message": {"role": "assistant", "content": "la"}, "done": False},
        {"model": "qwen2.5-coder:7b", "message": {"role": "assistant", "content": ""}, "done": True,
         "done_reason": "stop", "load_duration": 150_000_000, "prompt_eval_count": 37, "eval_count": 9,
         "eval_duration": 403_440_000},
    ]
    cuerpo = "\n".join(json.dumps(x) for x in lineas).encode()
    enviados = []
    async with _cliente(lambda url: httpx.Response(200, content=cuerpo), enviados) as c:
        res = await generar(OLLAMA, [{"role": "user", "content": "x"}], Parametros(max_tokens=512),
                            client=c, ollama_url="http://ol", medir_recursos=False)

    assert res.ok and res.contenido == "Hola"
    assert (res.tokens_entrada, res.tokens_salida) == (37, 9)
    assert res.carga_modelo_s == pytest.approx(0.15)
    assert res.detalle_final["eval_duration"] == 403_440_000
    url, body = enviados[0]
    assert url == "http://ol/api/chat"
    assert body["options"] == {"temperature": 0.2, "top_p": 0.95, "num_predict": 512, "num_ctx": 16384}
    assert body["keep_alive"] == "30m"


async def test_ollama_error_en_el_stream_queda_registrado():
    cuerpo = json.dumps({"error": "model requires more system memory"}).encode()
    async with _cliente(lambda url: httpx.Response(200, content=cuerpo), []) as c:
        res = await generar(OLLAMA, [], Parametros(), client=c, ollama_url="http://ol", medir_recursos=False)

    assert not res.ok and "more system memory" in res.error


async def test_respuesta_degenerada_en_el_contenido_no_cuenta_como_correcta():
    # Caso real (prueba del punto 5): kimi-k3 devolvió "!!!!" como respuesta
    # con finish_reason "stop" y se había contado como correcta.
    cuerpo = _sse(_delta(content="!" * 32),
                  {"model": "m", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    async with _cliente(lambda url: httpx.Response(200, content=cuerpo), []) as c:
        res = await generar(NVIDIA, [], Parametros(), client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert not res.ok
    assert res.error.startswith("Respuesta degenerada")


@pytest.mark.parametrize(("texto", "degenerada"), [
    ("!!!!!!!!!!!!!!!!", True), ("....  ....", True), ("?¿!¡-- **", True), ("aaaaaaaa", True),
    ("REQ-01: El sistema deberá...", False), ("{}", True), ('{"a": 1}', False), ("ok", False), ("", False),
])
def test_deteccion_de_salidas_degeneradas(texto, degenerada):
    from benchmarks.proveedores import es_degenerada

    assert es_degenerada(texto) is degenerada


async def test_reintenta_la_respuesta_vacia_y_registra_los_intentos(monkeypatch):
    from benchmarks import proveedores

    monkeypatch.setattr(proveedores.asyncio, "sleep", _sin_espera)
    vacia = _sse(_delta(reasoning_content="!!!!"),
                 {"model": "m", "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]})
    buena = _sse(_delta(content="Hola"))
    respuestas = [vacia, buena]
    async with _cliente(lambda url: httpx.Response(200, content=respuestas.pop(0)), []) as c:
        res = await proveedores.generar_con_reintentos(
            NVIDIA, [], Parametros(), client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert res.ok and res.contenido == "Hola"
    assert res.intentos == 2
    assert len(res.errores_previos) == 1 and res.errores_previos[0].startswith("Respuesta vacía")
    assert res.duracion_con_reintentos_s >= res.latencia_total_s


async def test_no_reintenta_errores_que_no_son_del_servicio(monkeypatch):
    from benchmarks import proveedores

    llamadas = []
    async with _cliente(lambda url: httpx.Response(404, text="Not found for account"), llamadas) as c:
        res = await proveedores.generar_con_reintentos(
            NVIDIA, [], Parametros(), client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert not res.ok and res.intentos == 1 and len(llamadas) == 1


async def test_se_rinde_tras_el_maximo_de_intentos(monkeypatch):
    from benchmarks import proveedores

    monkeypatch.setattr(proveedores.asyncio, "sleep", _sin_espera)
    llamadas = []
    async with _cliente(lambda url: httpx.Response(503, text="ocupado"), llamadas) as c:
        res = await proveedores.generar_con_reintentos(
            NVIDIA, [], Parametros(), max_intentos=3, client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert not res.ok and res.intentos == 3 and len(llamadas) == 3 and len(res.errores_previos) == 2


@pytest.mark.parametrize(("error", "reintentar"), [
    ("Respuesta vacía (finish_reason='stop')", True), ("HTTP 429: rate", True), ("HTTP 503: x", True),
    ("Timeout: ReadTimeout", True), ("HTTP 404: no", False), ("HTTP 401: no", False), (None, False),
])
def test_clasificacion_de_fallos_de_servicio(error, reintentar):
    from benchmarks.proveedores import es_fallo_de_servicio

    assert es_fallo_de_servicio(error) is reintentar


async def _sin_espera(_s):
    return None


async def test_timeout_queda_registrado_sin_lanzar():
    def manejar(request):
        raise httpx.ReadTimeout("lento", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(manejar)) as c:
        res = await generar(NVIDIA, [], Parametros(), client=c, nvidia_base_url="https://nv/v1", nvidia_api_key="k")

    assert not res.ok and res.error.startswith("Timeout")
