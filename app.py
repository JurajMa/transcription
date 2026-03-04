from __future__ import annotations

import atexit
import logging
import shutil
import signal
import subprocess
import sys
import tempfile
import types
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment

from transcription import TranscriptionService

ALLOWED_EXTENSIONS = {".wav", ".m4a", ".mp3", ".mp4", ".aac", ".flac", ".ogg", ".webm"}
_TEMP_PREFIX = "transcription_audio_"

logger = logging.getLogger(__name__)

# Process-level registry of temp paths created by this process.
_temp_registry: set[Path] = set()


def _cleanup_registered() -> None:
    """Delete all temp paths registered by this process."""
    for path in list(_temp_registry):
        try:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            elif path.exists():
                path.unlink()
        except OSError:
            pass
        _temp_registry.discard(path)


def _sigterm_handler(signum: int, frame: types.FrameType | None) -> None:
    """Ensure cleanup runs when the process is asked to terminate."""
    sys.exit(0)


atexit.register(_cleanup_registered)
signal.signal(signal.SIGTERM, _sigterm_handler)
signal.signal(signal.SIGINT, _sigterm_handler)

app = FastAPI(title="Transcription Studio", version="1.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

service = TranscriptionService()


@app.on_event("startup")
async def startup_cleanup() -> None:
    """Remove leftover temp files/dirs from a previous crashed run."""
    tmp_dir = Path(tempfile.gettempdir())
    for item in tmp_dir.glob(f"{_TEMP_PREFIX}*"):
        try:
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink()
            logger.info("Startup cleanup: removed %s", item)
        except OSError as exc:
            logger.warning("Startup cleanup: could not remove %s: %s", item, exc)


@app.get("/")
async def index() -> FileResponse:
    index_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(index_path)


def _convert_to_wav(input_path: Path, log_callback) -> Path:
    """Convert audio file to 16kHz mono WAV format using ffmpeg directly."""
    log_callback(f"Converting {input_path.suffix} to WAV format...")

    wav_path = input_path.with_suffix('.wav')

    result = subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-ac", "1",
            "-ar", "16000",
            "-sample_fmt", "s16",
            str(wav_path),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")

    # Log the resulting duration for verification
    try:
        audio = AudioSegment.from_wav(str(wav_path))
        log_callback(f"Converted to {wav_path.name} | {len(audio)}ms | 16kHz mono")
    except Exception:  # noqa: BLE001
        log_callback(f"Converted to {wav_path.name} | 16kHz mono")

    return wav_path


@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    api_key: str = Form(...),
) -> JSONResponse:
    filename = audio.filename or "upload"
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        supported = ", ".join(sorted(ALLOWED_EXTENSIONS))
        raise HTTPException(status_code=400, detail=f"Supported formats: {supported}")
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing OpenAI API key.")

    logs: list[str] = []

    def log_callback(message: str) -> None:
        logs.append(message)

    # Persist upload to a temp file for processing
    with tempfile.NamedTemporaryFile(delete=False, prefix=_TEMP_PREFIX, suffix=ext) as tmp_file:
        temp_path = Path(tmp_file.name)
        contents = await audio.read()
        tmp_file.write(contents)
    _temp_registry.add(temp_path)

    wav_path = None
    try:
        # Convert to WAV if needed
        if ext.lower() == ".wav":
            wav_path = temp_path
        else:
            wav_path = _convert_to_wav(temp_path, log_callback)
            _temp_registry.add(wav_path)
            temp_path.unlink()
            _temp_registry.discard(temp_path)

        result = service.transcribe(
            audio_path=wav_path,
            api_key=api_key,
            save_transcript=False,
            cleanup_chunks=True,
            log_callback=log_callback,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        # Clean up temp files
        for path in [temp_path, wav_path]:
            if path and path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
            if path:
                _temp_registry.discard(path)

    payload = {
        "transcript": result.transcript_text,
        "logs": logs,
        "filename": filename,
    }
    return JSONResponse(payload)
