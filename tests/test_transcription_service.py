"""Checks for the file transcription request and temporary-audio lifecycle."""

from __future__ import annotations

import tempfile
import unittest
import wave
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from transcription.service import TranscriptionService


class TranscriptionServiceTests(unittest.TestCase):
    def test_multiple_chunks_are_sent_without_a_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "dictation.wav"
            with wave.open(str(audio_path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(16000)
                audio.writeframes(b"\0\0" * 32000)

            create = Mock(side_effect=[
                SimpleNamespace(text="Write an email to my colleague about the meeting."),
                SimpleNamespace(text="about the meeting. Please include the agenda."),
            ])
            service = TranscriptionService(max_chunk_secs=1.5, chunk_overlap_secs=0)
            service._create_client = Mock(return_value=SimpleNamespace(
                audio=SimpleNamespace(transcriptions=SimpleNamespace(create=create))
            ))

            result = service.transcribe(
                audio_path=audio_path,
                api_key="test-key",
                save_transcript=False,
                cleanup_chunks=True,
            )

            self.assertEqual(create.call_count, 2)
            for call in create.call_args_list:
                self.assertEqual(call.kwargs["model"], "gpt-transcribe")
                self.assertEqual(call.kwargs["response_format"], "json")
                self.assertNotIn("prompt", call.kwargs)
            self.assertEqual(result.transcript_text, (
                "Write an email to my colleague about the meeting.\n\n"
                "about the meeting. Please include the agenda."
            ))
            self.assertIsNone(result.transcript_path)
            self.assertTrue(all(not path.exists() for path in result.chunk_paths))
            self.assertTrue(audio_path.exists())


if __name__ == "__main__":
    unittest.main()
