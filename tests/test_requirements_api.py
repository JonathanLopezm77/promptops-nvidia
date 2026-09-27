"""Tests de los endpoints /api/requirements contra PostgreSQL real.

El procesamiento en segundo plano (las llamadas a las IAs) se reemplaza por
un no-op: aquí solo se verifica lo que la API recibe y persiste.
"""

import uuid

import pytest
from fastapi.testclient import TestClient

from backend.database import SessionLocal
from backend.main import app
from backend.models import RequirementAnalysis
from backend.services import requirements_workflow

STT = {
    "engine": "Web Speech API (SpeechRecognition)",
    "provider": "Google (servicio en la nube de Chrome)",
    "processing": "remote",
    "language": "es-CO",
    "transcription_ms": 850,
    "edited": False,
}


@pytest.fixture
def client(monkeypatch):
    async def sin_procesar(analysis_id):
        return None

    monkeypatch.setattr(requirements_workflow, "run_analysis_background", sin_procesar)
    creados: list[str] = []
    with TestClient(app) as c:
        c.creados = creados
        yield c
    db = SessionLocal()
    try:
        for analysis_id in creados:
            fila = db.get(RequirementAnalysis, uuid.UUID(analysis_id))
            if fila is not None:
                db.delete(fila)
        db.commit()
    finally:
        db.close()


def _crear(client, **body):
    respuesta = client.post("/api/requirements", json=body)
    if respuesta.status_code == 202:
        client.creados.append(respuesta.json()["id"])
    return respuesta


def test_entrada_por_voz_guarda_la_metadata_del_stt(client):
    r = _crear(client, requirement="El sistema debe ser rápido.", input_mode="voice", stt_metadata=STT)

    assert r.status_code == 202
    cuerpo = client.get(f"/api/requirements/{r.json()['id']}").json()
    assert cuerpo["input_mode"] == "voice"
    assert cuerpo["stt_metadata"] == STT
    assert cuerpo["status"] == "CREATED"


def test_entrada_por_voz_sin_metadata_es_rechazada(client):
    r = _crear(client, requirement="El sistema debe ser rápido.", input_mode="voice")
    assert r.status_code == 422


def test_metadata_de_stt_en_entrada_de_texto_es_rechazada(client):
    r = _crear(client, requirement="El sistema debe ser rápido.", stt_metadata=STT)
    assert r.status_code == 422


TTS = {
    "engine": "speechSynthesis (navegador)",
    "voice": "Microsoft Sabina - Spanish (Mexico)",
    "language": "es-MX",
    "processing": "local",
    "script": "Análisis completado. El requisito original obtuvo 40 de 100 puntos.",
}


def _marcar(analysis_id: str, status: str) -> None:
    db = SessionLocal()
    try:
        db.get(RequirementAnalysis, uuid.UUID(analysis_id)).status = status
        db.commit()
    finally:
        db.close()


def test_registra_cada_lectura_en_voz_alta(client):
    r = _crear(client, requirement="El sistema debe ser rápido.", input_mode="voice", stt_metadata=STT)
    _marcar(r.json()["id"], "COMPLETED")

    primera = client.post(f"/api/requirements/{r.json()['id']}/tts", json=TTS)
    segunda = client.post(f"/api/requirements/{r.json()['id']}/tts", json={**TTS, "processing": "remote"})

    assert primera.status_code == 201 and segunda.status_code == 201
    log = client.get(f"/api/requirements/{r.json()['id']}").json()["tts_log"]
    assert [e["processing"] for e in log] == ["local", "remote"]
    assert log[0]["voice"] == TTS["voice"] and log[0]["script"] == TTS["script"]
    assert all(e["played_at"] for e in log)


def test_no_se_registra_lectura_de_un_analisis_sin_terminar(client):
    r = _crear(client, requirement="El sistema debe ser rápido.")
    respuesta = client.post(f"/api/requirements/{r.json()['id']}/tts", json=TTS)
    assert respuesta.status_code == 409
    assert "no hay resultado que leer" in respuesta.json()["detail"]


def test_lectura_con_procesamiento_invalido_es_rechazada(client):
    r = _crear(client, requirement="El sistema debe ser rápido.")
    _marcar(r.json()["id"], "COMPLETED")
    respuesta = client.post(f"/api/requirements/{r.json()['id']}/tts", json={**TTS, "processing": "nube"})
    assert respuesta.status_code == 422


def test_la_aclaracion_de_un_analisis_por_voz_conserva_su_origen(client):
    r = _crear(client, requirement="El sistema debe ser rápido.", input_mode="voice", stt_metadata=STT)
    db = SessionLocal()
    try:
        padre = db.get(RequirementAnalysis, uuid.UUID(r.json()["id"]))
        padre.status = "COMPLETED"
        db.commit()
    finally:
        db.close()

    hijo = client.post(f"/api/requirements/{r.json()['id']}/clarify", json={"answers": "2 segundos"})
    client.creados.insert(0, hijo.json()["id"])

    assert hijo.status_code == 202
    assert hijo.json()["parent_id"] == r.json()["id"]
    assert hijo.json()["input_mode"] == "voice"
    assert hijo.json()["stt_metadata"] == STT
