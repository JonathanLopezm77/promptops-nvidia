"""Punto de entrada de la aplicación: FastAPI, manejo de errores y el
frontend servido como estáticos (sin build step, sin npm)."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from backend.database import SessionLocal, engine
from backend.services import requirements_workflow, workflow
from backend.routes.requirements import router as requirements_router
from backend.routes.runs import router as runs_router
from backend.services.nvidia_client import NvidiaClientError
from backend.services.workflow import InvalidTransitionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("promptops")

_SCHEMA_REQUISITOS = Path(__file__).parent / "schema_requirements.sql"
_SCHEMA_ACTUALIZACIONES = Path(__file__).parent / "schema_updates.sql"


@asynccontextmanager
async def _lifespan(app: FastAPI):
    # schema_requirements.sql es idempotente (IF NOT EXISTS). Aplicarlo al
    # arrancar permite que las BD ya desplegadas (Render) reciban las
    # tablas de requisitos sin ejecutar SQL a mano. schema.sql (las cinco
    # tablas originales) se sigue aplicando manualmente, como antes.
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(_SCHEMA_REQUISITOS.read_text(encoding="utf-8"))
    except SQLAlchemyError:
        logger.exception("No se pudo aplicar schema_requirements.sql al arrancar")
    try:
        with engine.begin() as conn:
            conn.exec_driver_sql(_SCHEMA_ACTUALIZACIONES.read_text(encoding="utf-8"))
    except SQLAlchemyError:
        logger.exception("No se pudo aplicar schema_updates.sql al arrancar")
    try:
        db = SessionLocal()
        try:
            recuperados = requirements_workflow.recover_interrupted(db)
            runs_recuperados = workflow.recover_interrupted_runs(db)
        finally:
            db.close()
        if recuperados:
            logger.warning("%d análisis de requisitos interrumpidos por el reinicio quedaron en ERROR", recuperados)
        if runs_recuperados:
            logger.warning("%d runs interrumpidos por el reinicio quedaron en ERROR", runs_recuperados)
    except SQLAlchemyError:
        logger.exception("No se pudieron cerrar los análisis interrumpidos al arrancar")
    yield


app = FastAPI(title="Laboratorio de PromptOps", lifespan=_lifespan)

app.include_router(runs_router, prefix="/api")
app.include_router(requirements_router, prefix="/api")


def _mensaje_transicion(exc: InvalidTransitionError) -> str:
    if exc.target_status == "CLARIFY":
        return (
            f"Solo se pueden responder las preguntas de un análisis COMPLETED "
            f"(este está en {exc.current_status})."
        )
    if exc.target_status == "TTS":
        return f"El análisis todavía no terminó (está en {exc.current_status}): no hay resultado que leer."
    return f"No se puede pasar de {exc.current_status} a {exc.target_status}."


@app.exception_handler(InvalidTransitionError)
async def _invalid_transition_handler(request: Request, exc: InvalidTransitionError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": _mensaje_transicion(exc)},
    )


@app.exception_handler(NvidiaClientError)
async def _nvidia_error_handler(request: Request, exc: NvidiaClientError) -> JSONResponse:
    logger.exception("Error al comunicarse con NVIDIA")
    return JSONResponse(
        status_code=502,
        content={"detail": f"Error al comunicarse con NVIDIA: {exc}"},
    )


@app.exception_handler(SQLAlchemyError)
async def _db_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("Error de base de datos")
    return JSONResponse(
        status_code=503,
        content={"detail": "No se pudo completar la operación: la base de datos no está disponible."},
    )


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Error inesperado")
    return JSONResponse(
        status_code=500,
        content={"detail": "Ocurrió un error inesperado en el servidor."},
    )


# Debe registrarse DESPUÉS del router: un Mount en "/" actúa como catch-all,
# así que /api/* tiene que resolverse primero.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
