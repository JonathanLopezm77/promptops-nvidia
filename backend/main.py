"""Punto de entrada de la aplicación: FastAPI, manejo de errores y el
frontend servido como estáticos (sin build step, sin npm)."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError

from backend.routes.runs import router as runs_router
from backend.services.nvidia_client import NvidiaClientError
from backend.services.workflow import InvalidTransitionError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("promptops")

app = FastAPI(title="Laboratorio de PromptOps")

app.include_router(runs_router, prefix="/api")


@app.exception_handler(InvalidTransitionError)
async def _invalid_transition_handler(request: Request, exc: InvalidTransitionError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": f"No se puede pasar de {exc.current_status} a {exc.target_status}."},
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
