from __future__ import annotations

import contextlib
import time
import wave
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, List, Optional, Sequence

from openai import OpenAI

LogFn = Callable[[str], None]

# Number of characters from the previous chunk's transcript used as prompt context
_PROMPT_CONTEXT_CHARS = 200


def human_time(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def _dedup_overlap(prev: str, curr: str, tail_chars: int = 200, head_chars: int = 500) -> str:
    """Trim duplicated overlap text between two consecutive chunks."""
    if not prev:
        return curr
    prev_tail = prev[-tail_chars:]
    curr_head = curr[:head_chars]
    upto = min(len(prev_tail), len(curr_head))
    for size in range(upto, 0, -1):
        if prev_tail[-size:] == curr_head[:size]:
            return curr[size:]
    return curr


@dataclass
class TranscriptionResult:
    transcript_text: str
    transcript_path: Optional[Path]
    chunk_paths: Sequence[Path]
    log: Sequence[str]


class TranscriptionService:
    """High-level orchestration for chunked OpenAI audio transcription."""

    def __init__(
        self,
        *,
        model: str = "gpt-4o-transcribe",
        response_format: str = "json",
        max_chunk_secs: float = 90.0,
        chunk_overlap_secs: float = 1.0,
        max_chunk_bytes: int = 24 * 1024 * 1024,
        retry_max: int = 3,
        retry_backoff: float = 2.0,
    ) -> None:
        self.model = model
        self.response_format = response_format
        self.max_chunk_secs = max_chunk_secs
        self.chunk_overlap_secs = chunk_overlap_secs
        self.max_chunk_bytes = max_chunk_bytes
        self.retry_max = retry_max
        self.retry_backoff = retry_backoff

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def transcribe(
        self,
        audio_path: Path,
        api_key: str,
        *,
        save_transcript: bool = True,
        transcript_path: Optional[Path] = None,
        chunk_dir: Optional[Path] = None,
        cleanup_chunks: bool = False,
        log_callback: Optional[LogFn] = None,
    ) -> TranscriptionResult:
        """Run chunked transcription on *audio_path* using the provided API key."""
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")
        if not api_key:
            raise ValueError("Missing OpenAI API key")

        log_lines: List[str] = []

        def log(message: str) -> None:
            log_lines.append(message)
            if log_callback:
                log_callback(message)

        client = self._create_client(api_key)

        temp_dir: Optional[TemporaryDirectory[str]] = None
        try:
            if chunk_dir is None and cleanup_chunks:
                temp_dir = TemporaryDirectory(prefix="transcription_chunks_")
                chunk_dir_path = Path(temp_dir.name)
            else:
                chunk_dir_path = Path(chunk_dir) if chunk_dir else audio_path.parent / "chunks"
                chunk_dir_path.mkdir(parents=True, exist_ok=True)

            log(f"Splitting audio into ~{self.max_chunk_secs:.0f}s segments …")
            chunk_paths = self._split_wav(audio_path, chunk_dir_path, log)

            if not chunk_paths:
                raise RuntimeError("No audio chunks were produced.")

            transcript_parts: List[str] = []
            previous_text = ""
            total_chunks = len(chunk_paths)

            for index, chunk_path in enumerate(chunk_paths, start=1):
                log(f"Transcribing chunk {index}/{total_chunks}: {chunk_path.name}")
                prompt = previous_text[-_PROMPT_CONTEXT_CHARS:] if previous_text else ""
                chunk_text = self._transcribe_file(client, chunk_path, log, prompt=prompt).strip()
                if previous_text:
                    chunk_text = _dedup_overlap(previous_text, chunk_text)
                previous_text = chunk_text
                header = f"\n--- [Chunk {index}/{total_chunks}] {chunk_path.name} ---\n"
                transcript_parts.append(header + chunk_text + "\n")

            transcript_text = "".join(transcript_parts) if transcript_parts else ""

            result_path: Optional[Path] = None
            if save_transcript:
                result_path = (
                    transcript_path
                    if transcript_path is not None
                    else audio_path.parent / "transcript.txt"
                )
                result_path.write_text(transcript_text, encoding="utf-8")
                log(f"Transcript saved to {result_path}")

            return TranscriptionResult(
                transcript_text=transcript_text,
                transcript_path=result_path,
                chunk_paths=list(chunk_paths),
                log=list(log_lines),
            )
        finally:
            if cleanup_chunks:
                # Ensure we clean up generated chunks when requested
                if chunk_dir is not None:
                    for path in Path(chunk_dir).glob("*"):
                        try:
                            path.unlink()
                        except OSError:
                            pass
                    try:
                        Path(chunk_dir).rmdir()
                    except OSError:
                        pass
                if temp_dir is not None:
                    temp_dir.cleanup()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _create_client(self, api_key: str) -> OpenAI:
        return OpenAI(api_key=api_key)

    def _split_wav(self, input_wav: Path, out_dir: Path, log: LogFn) -> List[Path]:
        chunks: List[Path] = []
        with contextlib.closing(wave.open(str(input_wav), "rb")) as wf:
            nch = wf.getnchannels()
            sw = wf.getsampwidth()
            sr = wf.getframerate()
            nframes = wf.getnframes()
            bytes_per_frame = nch * sw
            total_bytes = nframes * bytes_per_frame

            frames_by_secs = int(self.max_chunk_secs * sr)
            if frames_by_secs <= 0:
                raise RuntimeError("Configured max chunk seconds is too small.")

            max_frames_by_bytes = self.max_chunk_bytes // bytes_per_frame
            if max_frames_by_bytes <= 0:
                raise RuntimeError("Configured max chunk bytes is too small for this WAV format.")

            chunk_frames = min(frames_by_secs, max_frames_by_bytes)
            overlap_frames = int(self.chunk_overlap_secs * sr)
            if overlap_frames >= chunk_frames:
                overlap_frames = max(0, chunk_frames // 2)

            start_frame = 0
            index = 0
            duration_total = nframes / sr if sr else 0
            log(f"Source: {human_time(duration_total)} | {nch}ch @ {sr}Hz | {total_bytes / (1024*1024):.2f} MB")

            while start_frame < nframes:
                end_frame = min(start_frame + chunk_frames, nframes)
                wf.setpos(start_frame)
                frames = wf.readframes(end_frame - start_frame)

                out_file = out_dir / f"chunk_{index:03d}.wav"
                with contextlib.closing(wave.open(str(out_file), "wb")) as outw:
                    outw.setnchannels(nch)
                    outw.setsampwidth(sw)
                    outw.setframerate(sr)
                    outw.writeframes(frames)

                chunk_duration = (end_frame - start_frame) / sr if sr else 0
                log(
                    f"  wrote {out_file.name} | {human_time(chunk_duration)} | "
                    f"size {(out_file.stat().st_size / (1024 * 1024)):.2f} MB"
                )

                chunks.append(out_file)
                index += 1
                start_frame = end_frame
                if start_frame < nframes:
                    start_frame = max(0, start_frame - overlap_frames)
        log(f"Split into {len(chunks)} chunk(s).")
        return chunks

    def _transcribe_file(self, client: OpenAI, path: Path, log: LogFn, *, prompt: str = "") -> str:
        last_error: Optional[Exception] = None
        for attempt in range(1, self.retry_max + 1):
            try:
                with open(path, "rb") as fh:
                    response = client.audio.transcriptions.create(
                        model=self.model,
                        file=fh,
                        response_format=self.response_format,
                        prompt=prompt,
                    )
                text = response.text if hasattr(response, "text") else str(response)
                return text
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                if attempt >= self.retry_max:
                    raise
                sleep_seconds = self.retry_backoff ** attempt
                log(
                    f"[warn] {type(exc).__name__}: {exc}. Retrying in {sleep_seconds:.1f}s"
                )
                time.sleep(sleep_seconds)
        assert last_error is not None  # pragma: no cover
        raise last_error
