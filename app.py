from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydub import AudioSegment

from transcription import TranscriptionService

ALLOWED_EXTENSIONS = {".wav", ".m4a", ".mp3", ".mp4", ".aac", ".flac", ".ogg"}

app = FastAPI(title="Transcription Studio", version="1.0")
app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")

service = TranscriptionService()


@app.get("/")
async def index() -> FileResponse:
    index_path = Path(__file__).parent / "static" / "index.html"
    return FileResponse(index_path)


def _convert_to_wav(input_path: Path, log_callback) -> Path:
    """Convert audio file to 16kHz mono WAV format using pydub."""
    log_callback(f"Converting {input_path.suffix} to WAV format...")
    
    # Load audio with pydub (supports many formats via ffmpeg)
    audio = AudioSegment.from_file(str(input_path))
    
    # Convert to mono and set sample rate to 16kHz
    audio = audio.set_channels(1)
    audio = audio.set_frame_rate(16000)
    
    # Create output path with .wav extension
    wav_path = input_path.with_suffix('.wav')
    
    # Export as WAV
    audio.export(str(wav_path), format="wav")
    log_callback(f"Converted to {wav_path.name} | {len(audio)}ms | 16kHz mono")
    
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
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp_file:
        temp_path = Path(tmp_file.name)
        contents = await audio.read()
        tmp_file.write(contents)

    wav_path = None
    try:
        # Convert to WAV if needed
        if ext.lower() == ".wav":
            wav_path = temp_path
        else:
            wav_path = _convert_to_wav(temp_path, log_callback)
            # Clean up original file after conversion
            temp_path.unlink()

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

    payload = {
        "transcript": result.transcript_text,
        "logs": logs,
        "filename": filename,
    }
    return JSONResponse(payload)
