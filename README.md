# Transcription Studio

**Record or upload audio and get a text transcript — powered by your own OpenAI API key.**

Transcription Studio is a lightweight, self-hosted alternative to OpenAI's Whisper desktop app. Paste your API key, drop in an audio file (or record directly in the browser), and receive an accurate transcript in seconds. The app **does not store your audio or your API key** — audio is sent directly to the OpenAI API for processing and all temporary files are deleted immediately afterwards.

![Transcription Studio UI](https://github.com/user-attachments/assets/2164301a-2d34-4355-893c-046125333039)

## Why use this?

| | Transcription Studio | OpenAI Whisper (local) |
|---|---|---|
| **Setup** | `pip install` + your API key | Download & run large model weights |
| **Hardware** | Any machine — processing happens via the API | Needs a capable GPU for real-time speeds |
| **Accuracy** | Uses the latest `gpt-4o-transcribe` model | Depends on chosen model size |
| **Privacy** | Audio sent to OpenAI API only; nothing stored locally | Fully local |

## How it works

1. Audio is split into overlapping chunks (~4.5 min each) to stay within API limits.
2. Each chunk is sent to the OpenAI transcription API (`gpt-4o-transcribe` by default).
3. Overlapping text between chunks is automatically deduplicated.
4. The final stitched transcript is displayed and can be copied or downloaded.

## Features

- 🎙️ **Record directly** in the browser or drag & drop / upload audio files
- 🎵 **Multi-format support** — WAV, M4A, MP3, MP4, AAC, FLAC, OGG, WEBM (auto-converted to WAV)
- 🔐 **Your API key stays private** — entered per-session, never stored or logged
- 🗑️ **No audio storage** — temporary files are cleaned up immediately after transcription
- ⚡ **Intelligent chunking** with overlap and deduplication for seamless long-form transcripts
- 💾 **Copy or save** the transcript as a `.txt` file
- 🖥️ **CLI included** for scripting and batch workflows

## Quick start

### 1. Install dependencies

```bash
# Create a virtual environment (conda or venv)
conda create -n transcription python=3.11 && conda activate transcription
# Or: python -m venv .venv && source .venv/bin/activate

pip install -r requirements.txt
```

**FFmpeg** is required for non-WAV audio conversion:
- **Windows:** `conda install -c conda-forge ffmpeg`
- **macOS:** `brew install ffmpeg`
- **Linux:** `sudo apt install ffmpeg`

### 2. Launch the web app

```bash
uvicorn app:app --reload
```

Open [http://localhost:8000](http://localhost:8000), paste your OpenAI API key, and start transcribing.

### 3. Or use the CLI

```bash
export OPENAI_API_KEY="your_key_here"       # Linux / macOS
# set OPENAI_API_KEY=your_key_here          # Windows

python transcribe_audio.py path/to/audio.wav
```

CLI options:

| Flag | Description |
|---|---|
| `--output PATH` | Custom output file path |
| `--no-save` | Print transcript to stdout without saving |
| `--keep-chunks` | Keep intermediate chunk files for inspection |

> **Note:** The CLI currently accepts WAV files only. For other formats, use the web UI or pre-convert with FFmpeg.

## Privacy & security

- **API key** — entered in the browser, sent over HTTPS to the OpenAI API, and discarded after the request. It is never written to disk or logged.
- **Audio data** — uploaded audio is held in a temporary file only for the duration of processing. It is sent to the OpenAI API for transcription and then immediately deleted. The app does not retain, log, or transmit your audio anywhere else.
- **Transcripts** — displayed in your browser. Nothing is saved server-side unless you explicitly use the CLI `--output` flag.

## Project structure

```
├── app.py                  # FastAPI web server
├── transcribe_audio.py     # CLI entry point
├── transcription/
│   ├── __init__.py
│   └── service.py          # Core chunking & transcription logic
├── static/
│   ├── index.html          # Web UI
│   ├── styles.css
│   └── app.js
└── requirements.txt
```

## License

© Juraj Mavračić 2025
