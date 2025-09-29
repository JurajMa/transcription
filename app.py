from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from transcription import TranscriptionService

ALLOWED_EXTENSIONS = {".wav"}

app = FastAPI(title="Transcription Studio", version="1.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

service = TranscriptionService()


@app.get("/", response_class=HTMLResponse)
async def index() -> FileResponse:
    index_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(index_path)


@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    api_key: str = Form(...),
) -> JSONResponse:
    filename = audio.filename or "upload.wav"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only WAV files are supported.")
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing OpenAI API key.")

    logs: list[str] = []

    def log_callback(message: str) -> None:
        logs.append(message)

    # Persist upload to a temp file for processing
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        temp_path = Path(tmp_file.name)
        contents = await audio.read()
        tmp_file.write(contents)

    try:
        result = service.transcribe(
            audio_path=temp_path,
            api_key=api_key,
            save_transcript=False,
            cleanup_chunks=True,
            log_callback=log_callback,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        try:
            temp_path.unlink()
        except OSError:
            pass

    payload = {
        "transcript": result.transcript_text,
        "logs": logs,
        "filename": filename,
    }
    return JSONResponse(payload)
