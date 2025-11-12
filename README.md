# Transcription Studio

A modern toolkit for chunked audio transcription powered by OpenAI. Use the command-line interface for fast batch conversions or the glassmorphism GUI for a polished drag-and-drop experience.

## Features

- ⚡ 90-second intelligent chunking with 1-second overlaps to protect sentence boundaries
- 🧠 Deduplicated chunk stitching using the latest `gpt-4o-transcribe` model (customisable)
- 🪟 Glass UI web front-end with drag & drop upload, live status feed, and transcript download
- 🎵 Multi-format audio support (WAV, M4A, MP3, AAC, FLAC, OGG) with automatic conversion to 16kHz mono WAV
- 🔐 Ephemeral OpenAI API key entry — nothing is persisted to disk
- 🧩 Modular service layer ready for CLI, GUI, or future deployment as a cloud web app

## Installation (conda workflow)

```cmd
conda create -n transcription python=3.11
conda activate transcription
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

**Note:** This app uses `pydub` for audio format conversion, which requires FFmpeg. Install it via:
- **Windows:** `conda install -c conda-forge ffmpeg`
- **macOS:** `brew install ffmpeg`  
- **Linux:** `sudo apt install ffmpeg` (Ubuntu/Debian)

## CLI usage

```cmd
conda activate transcription
set OPENAI_API_KEY=your_api_key_here
python transcribe_audio.py path\to\audio.wav
```

**Note:** CLI currently supports WAV files only. For other formats, use the web GUI or convert manually with FFmpeg first.

Options:

- `--output` to choose a custom transcript path
- `--no-save` to print the transcript without writing a file

Chunk files are written to a `chunks/` folder next to your audio file for inspection.

## Glass UI web app

1. Activate the `transcription` conda environment (see above) and ensure dependencies are installed.
2. Start the FastAPI app:

   ```cmd
   uvicorn app:app --reload
   ```

3. Open [http://localhost:8000](http://localhost:8000) in your browser.
4. Paste your OpenAI API key, drag in an audio file (WAV, M4A, MP3, AAC, FLAC, or OGG), and press **Start transcription**.
5. Non-WAV files are automatically converted to 16kHz mono WAV before processing.
6. Once complete, the **Save transcript** button becomes active for downloading a `.txt` copy.

> The API key only lives in memory for the lifetime of the request and is never logged or stored.

## Adapting for deployment

- The web client is pure HTML/CSS/JS served from `/static`, making it trivial to host on any static CDN.
- Wrap `TranscriptionService` inside your framework of choice (FastAPI example included).
- For non-WAV assets, pre-convert to 16 kHz mono WAV to reuse chunking logic as-is.

## Tests & quality gates

Run a basic syntax check across the project:

```cmd
conda activate transcription
python -m compileall .
```

The service is written to be framework-independent and ready for unit testing; you can mock the OpenAI client to validate chunk assembly, deduplication, and logging behaviour.
