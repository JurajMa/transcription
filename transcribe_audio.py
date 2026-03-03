"""Command-line entry for the transcription toolkit."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from transcription import TranscriptionService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Split a WAV into 90 second chunks, send them to OpenAI for transcription, "
            "and combine the results into a transcript.txt file."
        )
    )
    parser.add_argument("audio", type=Path, help="Path to the input WAV file")
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path for the transcript text file (default: transcript.txt next to audio)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Skip writing transcript.txt and only print status/logs",
    )
    parser.add_argument(
        "--keep-chunks",
        action="store_true",
        help="Keep intermediate audio chunk files after transcription (default: delete them)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    audio_path = args.audio.expanduser().resolve()

    if not audio_path.exists():
        raise SystemExit(f"File not found: {audio_path}")

    if audio_path.suffix.lower() != ".wav":
        print("Tip: For best accuracy, provide a WAV file (16kHz mono recommended).")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Missing OPENAI_API_KEY environment variable.")

    service = TranscriptionService()

    def log_printer(message: str) -> None:
        print(message)

    result = service.transcribe(
        audio_path=audio_path,
        api_key=api_key,
        save_transcript=not args.no_save,
        transcript_path=args.output,
        cleanup_chunks=not args.keep_chunks,
        log_callback=log_printer,
    )

    if args.no_save:
        print("\n--- Transcript (not saved) ---\n")
        print(result.transcript_text)
    else:
        print("\n✅ Transcription complete.")


if __name__ == "__main__":
    main()
