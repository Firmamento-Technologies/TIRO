"""Whisper transcription server — OpenAI-compatible API."""
import os
import tempfile
from fastapi import FastAPI, UploadFile, File, Form
from faster_whisper import WhisperModel

app = FastAPI(title="TIRO Whisper", version="0.1.0")

model_size = os.environ.get("WHISPER_MODEL", "base")
_model: WhisperModel | None = None


@app.on_event("startup")
async def load_model() -> None:
    global _model
    _model = WhisperModel(model_size, device="cpu", compute_type="int8")


@app.post("/v1/audio/transcriptions")
async def transcribe(
    file: UploadFile = File(...),
    model: str = Form(default="whisper-1"),
    language: str = Form(default="it"),
) -> dict:
    assert _model is not None, "Modello Whisper non ancora caricato"
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp.flush()
        segments, _info = _model.transcribe(tmp.name, language=language)
        text = " ".join(seg.text for seg in segments)
    return {"text": text.strip()}


@app.get("/salute")
async def salute() -> dict:
    return {"stato": "operativo"}
