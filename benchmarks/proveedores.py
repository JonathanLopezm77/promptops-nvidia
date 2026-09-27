"""Proveedores de modelos para el benchmark (Parcial 1, Componente 4).

Una sola interfaz, `generar()`, para un modelo local servido por Ollama y
modelos cloud de NVIDIA, que mide lo que exige la sección 7:

- TTFT: tiempo al primer token (de razonamiento o de respuesta) y tiempo al
  primer token de la RESPUESTA, medidos en el cliente con streaming.
- Latencia total, tokens de entrada / salida / razonamiento y finish_reason.
- Recursos locales (RAM/CPU del proceso de Ollama, VRAM y uso de GPU) con
  `MonitorRecursos`, solo para el modelo local.

Decisiones verificadas contra los servicios reales (ver
evidence/punto5_proveedores/):

- Ollama se usa por su API nativa (/api/chat) y no por la compatible con
  OpenAI: es la única que acepta `num_ctx` (Ollama usa 4096 de contexto por
  defecto y recortaría los prompts del benchmark sin avisar) y la que
  devuelve load_duration (la carga del modelo en la GPU, que en frío fue de
  20 s y no debe contarse como TTFT).
- `generar()` nunca lanza excepciones por fallos del modelo o del servicio:
  los devuelve en `ResultadoLLM.error`. En el benchmark un fallo es un dato
  (Task Success Rate), no algo que se reintenta en silencio.
- No se envía `seed`: con kimi-k3 en streaming empeoró las respuestas vacías
  (0 de 3 correctas).
"""

import asyncio
import json
import subprocess
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

import httpx

OLLAMA_URL_POR_DEFECTO = "http://localhost:11434"


@dataclass
class ModeloBench:
    """Un modelo del benchmark y cómo invocarlo."""

    clave: str  # p. ej. "local", "cloud_generalista", "cloud_razonamiento"
    tipo: str  # descripción del tipo exigido por el enunciado
    proveedor: str  # "ollama" | "nvidia"
    modelo: str
    # Parámetros propios del modelo que se envían tal cual y quedan
    # registrados (p. ej. chat_template_kwargs de NVIDIA, num_ctx de Ollama).
    extra: dict[str, Any] = field(default_factory=dict)
    justificacion: str = ""


@dataclass
class Parametros:
    """Parámetros de inferencia comunes: idénticos para los 3 modelos."""

    temperature: float = 0.2
    top_p: float = 0.95
    max_tokens: int = 4096


@dataclass
class ResultadoLLM:
    modelo: str
    proveedor: str
    contenido: str = ""
    razonamiento: str = ""
    ttft_s: float | None = None  # primer token de cualquier tipo
    ttft_contenido_s: float | None = None  # primer token de la respuesta
    latencia_total_s: float | None = None
    tokens_entrada: int | None = None
    tokens_salida: int | None = None  # incluye razonamiento si el proveedor lo cuenta así
    tokens_razonamiento: int | None = None
    finish_reason: str | None = None
    carga_modelo_s: float | None = None  # solo Ollama (load_duration)
    modelo_reportado: str | None = None  # lo que el servicio dice que respondió
    inicio_utc: str = ""
    fin_utc: str = ""
    error: str | None = None
    detalle_final: dict[str, Any] = field(default_factory=dict)  # último chunk / métricas crudas
    recursos: dict[str, Any] | None = None
    # Reintentos por fallos del servicio (ver generar_con_reintentos): número
    # de intentos usados y el error de cada intento fallido anterior.
    intentos: int = 1
    errores_previos: list[str] = field(default_factory=list)
    duracion_con_reintentos_s: float | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and bool(self.contenido.strip())

    def a_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["ok"] = self.ok
        return d


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# NVIDIA (compatible con OpenAI, streaming SSE)
# ---------------------------------------------------------------------------


async def _generar_nvidia(
    client: httpx.AsyncClient, cfg: ModeloBench, messages: list[dict], p: Parametros,
    base_url: str, api_key: str,
) -> ResultadoLLM:
    res = ResultadoLLM(modelo=cfg.modelo, proveedor="nvidia", inicio_utc=_ahora())
    body = {
        "model": cfg.modelo, "messages": messages, "stream": True,
        "stream_options": {"include_usage": True},
        "temperature": p.temperature, "top_p": p.top_p, "max_tokens": p.max_tokens,
        **cfg.extra,
    }
    t0 = time.perf_counter()
    try:
        async with client.stream(
            "POST", f"{base_url}/chat/completions", json=body,
            headers={"Authorization": f"Bearer {api_key}"},
        ) as r:
            if r.status_code != 200:
                texto = (await r.aread()).decode("utf-8", "replace")
                res.error = f"HTTP {r.status_code}: {texto.strip()[:300]}"
                return _cerrar(res, t0)
            async for linea in r.aiter_lines():
                if not linea.startswith("data:"):
                    continue
                dato = linea[5:].strip()
                if dato == "[DONE]":
                    break
                d = json.loads(dato)
                res.modelo_reportado = d.get("model") or res.modelo_reportado
                if d.get("usage"):
                    u = d["usage"]
                    res.tokens_entrada = u.get("prompt_tokens")
                    res.tokens_salida = u.get("completion_tokens")
                    res.tokens_razonamiento = (u.get("completion_tokens_details") or {}).get("reasoning_tokens")
                    res.detalle_final["usage"] = u
                for ch in d.get("choices") or []:
                    delta = ch.get("delta") or {}
                    razon = delta.get("reasoning_content") or delta.get("reasoning") or ""
                    texto = delta.get("content") or ""
                    if (razon or texto) and res.ttft_s is None:
                        res.ttft_s = time.perf_counter() - t0
                    if texto and res.ttft_contenido_s is None:
                        res.ttft_contenido_s = time.perf_counter() - t0
                    res.razonamiento += razon
                    res.contenido += texto
                    if ch.get("finish_reason"):
                        res.finish_reason = ch["finish_reason"]
    except httpx.TimeoutException as e:
        res.error = f"Timeout: {type(e).__name__}"
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        res.error = f"{type(e).__name__}: {str(e)[:200]}"
    _cerrar(res, t0)
    if res.error is None and not res.contenido.strip():
        res.error = f"Respuesta vacía (finish_reason={res.finish_reason!r}, razonamiento={len(res.razonamiento)} chars)"
    return res


# ---------------------------------------------------------------------------
# Ollama (API nativa, streaming NDJSON)
# ---------------------------------------------------------------------------


async def _generar_ollama(
    client: httpx.AsyncClient, cfg: ModeloBench, messages: list[dict], p: Parametros, base_url: str,
) -> ResultadoLLM:
    res = ResultadoLLM(modelo=cfg.modelo, proveedor="ollama", inicio_utc=_ahora())
    opciones = {"temperature": p.temperature, "top_p": p.top_p, "num_predict": p.max_tokens,
                **cfg.extra.get("options", {})}
    body = {"model": cfg.modelo, "messages": messages, "stream": True, "options": opciones,
            **{k: v for k, v in cfg.extra.items() if k != "options"}}
    t0 = time.perf_counter()
    try:
        async with client.stream("POST", f"{base_url}/api/chat", json=body) as r:
            if r.status_code != 200:
                texto = (await r.aread()).decode("utf-8", "replace")
                res.error = f"HTTP {r.status_code}: {texto.strip()[:300]}"
                return _cerrar(res, t0)
            async for linea in r.aiter_lines():
                if not linea.strip():
                    continue
                d = json.loads(linea)
                if d.get("error"):
                    res.error = f"Ollama: {d['error']}"
                    break
                msg = d.get("message") or {}
                razon = msg.get("thinking") or ""
                texto = msg.get("content") or ""
                if (razon or texto) and res.ttft_s is None:
                    res.ttft_s = time.perf_counter() - t0
                if texto and res.ttft_contenido_s is None:
                    res.ttft_contenido_s = time.perf_counter() - t0
                res.razonamiento += razon
                res.contenido += texto
                if d.get("done"):
                    res.modelo_reportado = d.get("model")
                    res.finish_reason = d.get("done_reason")
                    res.tokens_entrada = d.get("prompt_eval_count")
                    res.tokens_salida = d.get("eval_count")
                    if d.get("load_duration") is not None:
                        res.carga_modelo_s = d["load_duration"] / 1e9
                    res.detalle_final = {k: v for k, v in d.items() if k != "message"}
    except httpx.TimeoutException as e:
        res.error = f"Timeout: {type(e).__name__}"
    except (httpx.HTTPError, json.JSONDecodeError) as e:
        res.error = f"{type(e).__name__}: {str(e)[:200]}"
    _cerrar(res, t0)
    if res.error is None and not res.contenido.strip():
        res.error = f"Respuesta vacía (done_reason={res.finish_reason!r})"
    return res


def _cerrar(res: ResultadoLLM, t0: float) -> ResultadoLLM:
    res.latencia_total_s = time.perf_counter() - t0
    res.fin_utc = _ahora()
    if res.error is None and res.contenido.strip() and es_degenerada(res.contenido):
        res.error = f"Respuesta degenerada: {res.contenido.strip()[:40]!r}"
    return res


def es_degenerada(texto: str) -> bool:
    """Salida sin contenido real: sin letras ni dígitos, o un único carácter
    repetido. Caso real del punto 5: kimi-k3 devolvió como RESPUESTA
    '!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!' con finish_reason 'stop'; al comprobar
    solo que no estuviera vacía, se contó como correcta."""
    visibles = [c for c in texto if not c.isspace()]
    if not visibles:
        return False  # vacía: se reporta como "Respuesta vacía", no aquí
    if len(set(visibles)) == 1 and len(visibles) >= 5:
        return True
    return not any(c.isalnum() for c in visibles)


# ---------------------------------------------------------------------------
# API pública
# ---------------------------------------------------------------------------


async def generar(
    cfg: ModeloBench,
    messages: list[dict],
    params: Parametros,
    *,
    client: httpx.AsyncClient,
    nvidia_base_url: str = "",
    nvidia_api_key: str = "",
    ollama_url: str = OLLAMA_URL_POR_DEFECTO,
    medir_recursos: bool | None = None,
) -> ResultadoLLM:
    """Genera una respuesta y devuelve todas las métricas. Por defecto mide
    recursos solo para el modelo local."""
    medir = cfg.proveedor == "ollama" if medir_recursos is None else medir_recursos
    monitor = MonitorRecursos(ollama_url=ollama_url) if medir else None
    if monitor:
        await monitor.iniciar()
    try:
        if cfg.proveedor == "nvidia":
            res = await _generar_nvidia(client, cfg, messages, params, nvidia_base_url, nvidia_api_key)
        elif cfg.proveedor == "ollama":
            res = await _generar_ollama(client, cfg, messages, params, ollama_url)
        else:
            raise ValueError(f"proveedor desconocido: {cfg.proveedor}")
    finally:
        if monitor:
            recursos = await monitor.detener()
    if monitor:
        res.recursos = recursos
    return res


def es_fallo_de_servicio(error: str | None) -> bool:
    """Fallos del servicio (no de la calidad de la respuesta) que justifican
    reintentar: respuesta vacía, 429, 5xx, timeouts y cortes de red. Un 400,
    401 o 404 no se arreglan repitiendo."""
    if not error:
        return False
    if error.startswith(("Respuesta vacía", "Respuesta degenerada", "Timeout", "RemoteProtocolError",
                         "ReadError", "ConnectError")):
        return True
    return error.startswith("HTTP ") and (error[5:8] == "429" or error[5:6] == "5")


async def generar_con_reintentos(
    cfg: ModeloBench, messages: list[dict], params: Parametros, *, max_intentos: int = 3, **kwargs,
) -> ResultadoLLM:
    """Como `generar`, pero repite ante fallos del servicio (hasta
    `max_intentos`). Medido en el punto 5: kimi-k3 en streaming devolvió
    content vacío en 1 de 3 llamadas con un caso real. Las métricas son las
    del último intento; `intentos` y `errores_previos` dejan constancia de
    los fallos, que se reportan aparte como confiabilidad del servicio. La
    misma política aplica a los 3 modelos."""
    t0 = time.perf_counter()
    errores: list[str] = []
    for intento in range(1, max_intentos + 1):
        res = await generar(cfg, messages, params, **kwargs)
        if res.ok or not es_fallo_de_servicio(res.error) or intento == max_intentos:
            res.intentos = intento
            res.errores_previos = errores
            res.duracion_con_reintentos_s = time.perf_counter() - t0
            return res
        errores.append(res.error)
        await asyncio.sleep(2 * intento)
    raise AssertionError("inalcanzable")


async def modelo_cargado(client: httpx.AsyncClient, cfg: ModeloBench, ollama_url: str = OLLAMA_URL_POR_DEFECTO) -> bool:
    """True si Ollama ya tiene el modelo en memoria (entonces el
    calentamiento no mide una carga en frío)."""
    modelos = (await client.get(f"{ollama_url}/api/ps")).json().get("models", [])
    return any(m.get("name") == cfg.modelo for m in modelos)


async def calentar_ollama(client: httpx.AsyncClient, cfg: ModeloBench, ollama_url: str = OLLAMA_URL_POR_DEFECTO) -> float:
    """Carga el modelo local en memoria antes de medir (con el mismo num_ctx
    del benchmark) y devuelve el tiempo de carga. Sin esto la primera
    ejecución sumaría ~20 s de carga al TTFT."""
    body = {"model": cfg.modelo, "messages": [{"role": "user", "content": "ok"}], "stream": False,
            "options": {"num_predict": 1, **cfg.extra.get("options", {})},
            **{k: v for k, v in cfg.extra.items() if k != "options"}}
    r = await client.post(f"{ollama_url}/api/chat", json=body)
    r.raise_for_status()
    return (r.json().get("load_duration") or 0) / 1e9


async def version_modelo(
    client: httpx.AsyncClient, cfg: ModeloBench, *, nvidia_base_url: str = "",
    ollama_url: str = OLLAMA_URL_POR_DEFECTO,
) -> dict[str, Any]:
    """Identificación exacta del modelo para registrar su versión."""
    if cfg.proveedor == "ollama":
        info = (await client.post(f"{ollama_url}/api/show", json={"model": cfg.modelo})).json()
        tags = (await client.get(f"{ollama_url}/api/tags")).json().get("models", [])
        tag = next((t for t in tags if t["name"] == cfg.modelo), {})
        version_ollama = (await client.get(f"{ollama_url}/api/version")).json().get("version")
        contexto_max = next((v for k, v in (info.get("model_info") or {}).items() if k.endswith(".context_length")), None)
        return {"modelo": cfg.modelo, "digest": tag.get("digest"), "tamano_bytes": tag.get("size"),
                **(info.get("details") or {}), "contexto_maximo": contexto_max, "ollama_version": version_ollama}
    modelos = (await client.get(f"{nvidia_base_url}/models")).json().get("data", [])
    m = next((x for x in modelos if x.get("id") == cfg.modelo), {})
    # El catálogo de NVIDIA devuelve la misma fecha genérica (1993-04-26)
    # como "created" para todos los modelos, así que no sirve como versión:
    # se identifica el modelo por su id y la fecha de la ejecución.
    return {"modelo": cfg.modelo, "owned_by": m.get("owned_by"), "en_catalogo": bool(m),
            "version": "no publicada por NVIDIA: se registra el id del modelo y la fecha de ejecución"}


# ---------------------------------------------------------------------------
# Recursos locales
# ---------------------------------------------------------------------------


class MonitorRecursos:
    """Muestrea RAM/CPU de los procesos de Ollama y VRAM/uso de la GPU
    mientras dura una generación local.

    En Windows (modo WDDM) nvidia-smi no informa la VRAM por proceso, así que
    se registran: la VRAM total ocupada de la GPU (incluye otros programas)
    y la VRAM que Ollama dice usar para el modelo (/api/ps, exacta)."""

    PROCESOS = ("llama-server", "ollama")

    def __init__(self, ollama_url: str = OLLAMA_URL_POR_DEFECTO, intervalo_s: float = 0.5):
        self.ollama_url = ollama_url
        self.intervalo_s = intervalo_s
        self.muestras: list[dict[str, float]] = []
        self._tarea: asyncio.Task | None = None
        self._procesos: list = []

    async def iniciar(self) -> None:
        import psutil

        self._procesos = [p for p in psutil.process_iter(["name"])
                          if any(n in (p.info["name"] or "").lower() for n in self.PROCESOS)]
        for p in self._procesos:
            try:
                p.cpu_percent(None)  # primera lectura: fija la referencia
            except Exception:  # noqa: BLE001
                pass
        self._tarea = asyncio.create_task(self._bucle())

    async def _bucle(self) -> None:
        while True:
            self.muestras.append(await asyncio.to_thread(self._muestra))
            await asyncio.sleep(self.intervalo_s)

    def _muestra(self) -> dict[str, float]:
        ram = cpu = 0.0
        for p in self._procesos:
            try:
                ram += p.memory_info().rss
                cpu += p.cpu_percent(None)
            except Exception:  # noqa: BLE001  (el proceso pudo terminar)
                pass
        gpu = _nvidia_smi()
        return {"ram_mb": ram / 2**20, "cpu_pct": cpu, **gpu}

    async def detener(self) -> dict[str, Any]:
        if self._tarea:
            self._tarea.cancel()
            try:
                await self._tarea
            except asyncio.CancelledError:
                pass
        vram_modelo = None
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                ps = (await c.get(f"{self.ollama_url}/api/ps")).json().get("models", [])
            vram_modelo = [{"modelo": m["name"], "tamano_mb": m["size"] / 2**20,
                            "vram_mb": m["size_vram"] / 2**20,
                            "fraccion_gpu": round(m["size_vram"] / m["size"], 3) if m["size"] else None,
                            "contexto": m.get("context_length")} for m in ps]
        except Exception:  # noqa: BLE001
            pass

        def resumen(clave):
            valores = [m[clave] for m in self.muestras if m.get(clave) is not None]
            if not valores:
                return None
            return {"max": round(max(valores), 1), "media": round(sum(valores) / len(valores), 1)}

        import psutil

        return {
            "muestras": len(self.muestras), "intervalo_s": self.intervalo_s,
            # cpu_proceso_pct: suma de los procesos de Ollama; 100 = un núcleo
            # lógico completo (puede superar 100). Para el % de toda la CPU,
            # dividir entre nucleos_logicos.
            "ram_proceso_mb": resumen("ram_mb"), "cpu_proceso_pct": resumen("cpu_pct"),
            "nucleos_logicos": psutil.cpu_count(),
            "vram_gpu_total_usada_mb": resumen("vram_usada_mb"), "gpu_uso_pct": resumen("gpu_pct"),
            "modelos_cargados_ollama": vram_modelo,
        }


def _nvidia_smi() -> dict[str, float]:
    try:
        salida = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used,utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip().splitlines()[0]
        usada, uso = (float(x) for x in salida.split(","))
        return {"vram_usada_mb": usada, "gpu_pct": uso}
    except Exception:  # noqa: BLE001  (sin GPU NVIDIA o sin nvidia-smi)
        return {}
